"""
submission.py — worksheet submission and rubric grading.

Replaces Google Classroom's collect-and-grade role, completing the move off
Google. Identity is the same one-time code used by the graded quiz: no student
password exists anywhere on this platform.

THE TWO THINGS THAT MAKE FILE UPLOAD SAFE HERE

1. **A student never influences a filesystem path.** `store_file` generates the
   on-disk name from `secrets.token_hex` and records the student's own filename
   in the database for display only. Traversal, collisions and
   extension-confusion (`report.pdf.php`, `..%2f`, NUL bytes, Windows reserved
   names) are all impossible by construction rather than filtered — there is no
   filter to bypass because the input never reaches the path.

2. **Uploads are never served inline.** `open_file` hands back bytes and a
   display name; the route sets `Content-Disposition: attachment` and a
   sandbox CSP. This matters more here than on most platforms: an uploaded HTML
   or SVG rendered inline from this origin is stored XSS straight into the
   teacher's authenticated grading session — the account that holds every
   student's marks. The deliverables are screenshots and PDFs, so nothing is
   lost by refusing to render them.

WHAT IS DELIBERATELY *NOT* DONE
   No content sniffing, no image re-encoding, no antivirus. Those are defences
   for platforms that display what they receive. This one doesn't. Adding them
   would suggest inline rendering is safe if only the checks were good enough,
   which is the argument that loses.

MARKS
   A criterion with `points = NULL` is UNMARKED, which is not zero. `score()`
   reports `complete=False` while any criterion is unmarked, so a half-graded
   worksheet cannot be exported as a finished mark.
"""

from __future__ import annotations

import datetime
import hashlib
import json
import math
import os
import re
import secrets
import string
import unicodedata

# Same alphabet as the quiz codes: printed on paper, read aloud, typed under
# time pressure — `I/O/0/1` cost support time.
CODE_ALPHABET = "".join(c for c in string.ascii_uppercase + string.digits
                        if c not in "IO01")
CODE_LEN = 8

# A worksheet PDF with a dozen embedded screenshots. Bounded, but not so tight
# that a legitimate submission bounces at 23:50 on a deadline.
MAX_FILE_BYTES = 20 * 1024 * 1024
MAX_FILES_PER_SUBMISSION = 10

# The rubric the worksheets actually carry (see any labs/weekNN/worksheet.md
# "Criterion | Points" table).
DEFAULT_RUBRIC = [
    {"criterion": "Lecture questions (conceptual accuracy)", "max": 20.0},
    {"criterion": "Exploitation + evidence (payloads + screenshots)", "max": 40.0},
    {"criterion": "Defense (fixes proven, lines cited)", "max": 25.0},
    {"criterion": "Reflection (CWE/OWASP mapping, mitigation)", "max": 15.0},
]


class SubmitError(Exception):
    """Refusal with a student-safe message."""


# Why a code did not open its worksheet. Three separate messages, because one "isn't valid" for
# all of them sent students who had simply re-typed a used code to email that the system was
# broken. Saying "used" or "closed" leaks nothing practical (8 characters from 32 symbols cannot
# be guessed), but none of them names the worksheet or the student the code belongs to. The
# unknown-code text also shows on /code and /quiz, so it has to suit a quiz code too.
CODE_NOT_VALID = ("That code isn't valid. Check that you typed all 8 characters of the code"
                  " on your slip (not your student ID) and try again.")
CODE_ALREADY_USED = ("That code has already been used. A code opens its worksheet once, and the"
                     " worksheet stays open in the browser where the code was first entered — go"
                     " back to that browser. If you can't, ask your teacher for a new code.")
CODE_DEADLINE_PASSED = ("The deadline for this worksheet has passed, so it is closed. Your code"
                        " has not been used, and it will still work if your teacher reopens the"
                        " worksheet.")


def safe_display_name(raw: str) -> str:
    """Sanitise a filename for DISPLAY. Never used to build a path.

    Even though the on-disk name is generated, the student's name is rendered
    back to them and to the teacher, so it still gets stripped of control
    characters, path separators and direction-override marks (which can make
    `exe.txt` display as `txt.exe`).
    """
    s = unicodedata.normalize("NFKC", str(raw or ""))
    s = "".join(c for c in s if c.isprintable() and unicodedata.category(c) != "Cf")
    s = s.replace("\\", "/").split("/")[-1]          # drop any path part
    s = re.sub(r"\s+", " ", s).strip(" .")           # no leading/trailing dots
    return s[:120] or "unnamed"


# --- assignments -----------------------------------------------------------

def create_assignment(conn, *, teacher_id, title, now, week_slug=None,
                      instructions="", due_at=None, rubric=None,
                      course_slug=None, late_days=0):
    rubric = rubric or DEFAULT_RUBRIC
    if not rubric:
        raise ValueError("an assignment needs a rubric")
    for r in rubric:
        if "criterion" not in r or float(r.get("max", 0)) <= 0:
            raise ValueError(f"bad rubric row: {r!r}")
    if not 0 <= int(late_days) <= MAX_LATE_DAYS:
        raise ValueError(f"The late window must be 0–{MAX_LATE_DAYS} days.")
    import course_scope
    course = course_scope.check(course_slug)
    cur = conn.execute(
        "INSERT INTO assignments (teacher_id, course_slug, title, week_slug,"
        " instructions, due_at, late_days, rubric_json, released, created_at)"
        " VALUES (?,?,?,?,?,?,?,?,0,?)",
        (teacher_id, course, title, week_slug, instructions, due_at, int(late_days),
         json.dumps(rubric, ensure_ascii=False), now))
    conn.commit()
    return cur.lastrowid


def get_assignment(conn, assignment_id):
    return conn.execute("SELECT * FROM assignments WHERE id = ?",
                        (assignment_id,)).fetchone()


def rubric_of(row) -> list[dict]:
    return json.loads(row["rubric_json"])


def total_points(row) -> float:
    return sum(float(r["max"]) for r in rubric_of(row))


def issue_codes(conn, assignment_id, student_ids, now):
    """Idempotent, like the quiz: adding a late enrolment must not invalidate
    slips already handed out.

    Also the recovery path for a student who already redeemed and then lost
    their session (new device, cleared cookies): their row's `redeemed_at` is
    set, so this mints them a fresh, unredeemed code rather than handing back
    the old (now-useless) one. The row itself is never replaced — `code` is
    the PRIMARY KEY and `(assignment_id, student_id)` the UNIQUE pair other
    tables may eventually reference, so a reissue UPDATEs it in place.
    """
    # Issuing slips IS the enrolment event — this is the one moment a real class
    # list passes through the platform. Registering it here means the roster
    # cannot drift from who actually holds a code, and it needs no second step a
    # teacher could forget. The course is read off the assignment rather than
    # taken as an argument, so a slip can never enrol someone into a course other
    # than the one they are being assessed in.
    import codes
    import roster
    _row = conn.execute(
        "SELECT teacher_id, course_slug FROM assignments WHERE id = ?", (assignment_id,)).fetchone()
    if _row is not None:
        roster.enroll(conn, course_slug=_row["course_slug"],
                      teacher_id=_row["teacher_id"], student_ids=student_ids, now=now)
    out = {}
    for sid in student_ids:
        row = conn.execute(
            "SELECT code, redeemed_at FROM submit_codes WHERE assignment_id = ? AND student_id = ?",
            (assignment_id, sid)).fetchone()
        if row and row["redeemed_at"] is None:
            out[sid] = row["code"]
            continue
        while True:
            code = "".join(secrets.choice(CODE_ALPHABET) for _ in range(CODE_LEN))
            # Checked against attempt_codes too — see codes.py and the matching
            # comment in assessment.issue_codes().
            if not codes.is_taken(conn, code):
                break
        if row:
            # Reissue: same (assignment_id, student_id) row, fresh code, clear
            # the burn marker. UPDATE not DELETE+INSERT — `code` is the primary
            # key, so this is the only way to change it without a window where
            # the row (and the student's place in gradebook_rows()) is absent.
            conn.execute("UPDATE submit_codes SET code = ?, issued_at = ?,"
                         " redeemed_at = NULL WHERE assignment_id = ? AND student_id = ?",
                         (code, now, assignment_id, sid))
        else:
            conn.execute("INSERT INTO submit_codes (code, assignment_id, student_id,"
                         " issued_at) VALUES (?,?,?,?)", (code, assignment_id, sid, now))
        out[sid] = code
    conn.commit()
    return out


# --- the student side ------------------------------------------------------

def redeem(conn, code, now):
    """Open (or create) this student's submission, then burn the code.

    Used to be reusable forever ("come back and replace a bad upload before
    the deadline, or read feedback after it") — but a code that NEVER expires
    is a permanent bearer credential: anyone who ever saw the printed slip
    (a classmate, a photo) could redeem it themselves at any later point —
    even after the real student submitted, even after the deadline — and get
    the same read/write access (delete files, edit the note, read released
    grades). The legitimate "come back later" need is real, so it still
    works — just through the Flask session this redemption establishes
    (made permanent in routes_submit.py/routes_code.py), not through the
    code staying valid forever. Losing that session (new device, cleared
    cookies) is recovered the same way a late enrollment already is: the
    teacher re-runs issue_codes() for that student — it mints a fresh code
    since the old row is gone, and redeem() finds the SAME submission by
    (assignment_id, student_id), never by the code string.

    After the deadline a code opens the worksheet only to read released marks
    on work that was handed in (read-only: can_upload() is False by then).
    Any other past-deadline code is refused BEFORE anything is written, so it
    stays unused: there is nothing to do on a closed worksheet, and the
    teacher has reopened deadlines before (the W1-6 resubmission window).
    Checked in this order — unknown, used, closed — so a used code is called
    used even once its worksheet has closed.
    """
    row = conn.execute("SELECT * FROM submit_codes WHERE code = ?",
                       ((code or "").strip().upper(),)).fetchone()
    if row is None:
        raise SubmitError(CODE_NOT_VALID)
    if row["redeemed_at"] is not None:
        raise SubmitError(CODE_ALREADY_USED)

    sub = conn.execute(
        "SELECT * FROM submissions WHERE assignment_id = ? AND student_id = ?",
        (row["assignment_id"], row["student_id"])).fetchone()
    a = get_assignment(conn, row["assignment_id"])
    has_feedback = bool(a["released"] and sub is not None and sub["submitted_at"])
    if not _is_open(a, now) and not has_feedback:
        raise SubmitError(CODE_DEADLINE_PASSED)

    # Burn first, and only if nobody else has: the SELECT above is not a lock,
    # so two redemptions of one code at once must not both get in.
    if conn.execute("UPDATE submit_codes SET redeemed_at = ?"
                    " WHERE code = ? AND redeemed_at IS NULL",
                    (now, row["code"])).rowcount != 1:
        conn.rollback()
        raise SubmitError(CODE_ALREADY_USED)
    if sub is None:
        cur = conn.execute(
            "INSERT INTO submissions (assignment_id, student_id, created_at)"
            " VALUES (?,?,?)", (row["assignment_id"], row["student_id"], now))
        sub = conn.execute("SELECT * FROM submissions WHERE id = ?",
                           (cur.lastrowid,)).fetchone()
    conn.commit()
    return sub


# Deadlines are STORED in UTC, like every other timestamp here (app._now() is naive
# UTC), but people type and read them in course-local time: the cohort is in Thailand
# (ICT = UTC+7, no DST). In Oct 2026 "23:59" Thai time was typed into this UTC field
# for W10-15, which kept the portal open until 06:59 the next morning, and every page
# showed the raw value with no zone. So the form takes ICT, every page shows ICT, and
# only storage and comparison use UTC.
COURSE_TZ = datetime.timezone(datetime.timedelta(hours=7), "ICT")


# A date AND a time, nothing else. fromisoformat alone also takes "2026-11-07" (midnight,
# a day early for anyone meaning "by the 7th"), compact and ISO-week forms, and offsets;
# and Python 3.13+ takes "24:00" where 3.12 does not, so the hour range is spelled out.
_DUE_INPUT = re.compile(r"\d{4}-\d{2}-\d{2}[T ]([01]\d|2[0-3]):[0-5]\d(:[0-5]\d)?")


def due_from_local(text):
    """'2026-11-07T23:59' Thai time -> '2026-11-07T16:59:00' UTC, as stored. Blank -> None.

    An explicit offset is refused, not honoured: this field is Thai time, and quietly
    accepting '+00:00' is how the two conventions got mixed in the first place."""
    s = (text or "").strip()
    if not s:
        return None
    if not _DUE_INPUT.fullmatch(s):
        raise ValueError(f"“{s}” isn't a date and time in Thai time like 2026-11-07T23:59"
                         " (with no offset).")
    try:
        local = datetime.datetime.fromisoformat(s.replace(" ", "T", 1))
        utc = local.replace(tzinfo=COURSE_TZ).astimezone(datetime.timezone.utc)
    except (ValueError, OverflowError):
        raise ValueError(f"“{s}” isn't a real date and time.") from None
    return utc.replace(tzinfo=None).isoformat(timespec="seconds")


def due_label(due_at) -> str:
    """A stored UTC deadline as people read it: '2026-11-07 23:59 ICT'."""
    if not due_at:
        return ""
    try:
        t = datetime.datetime.fromisoformat(due_at)
        if t.tzinfo is None:            # the stored convention: naive UTC
            t = t.replace(tzinfo=datetime.timezone.utc)
        local = t.astimezone(COURSE_TZ)
    except (ValueError, OverflowError):
        return str(due_at)
    return local.strftime("%Y-%m-%d %H:%M:%S ICT" if local.second else "%Y-%m-%d %H:%M ICT")


# A late window longer than this is a typo, not a policy.
MAX_LATE_DAYS = 30


def late_days_of(assignment) -> int:
    """Days uploads stay open after due_at; 0 when unset or on a row from before the column."""
    try:
        return int(assignment["late_days"] or 0)
    except (IndexError, KeyError):
        return 0


def closes_at(assignment):
    """When uploads actually stop (stored UTC): due_at plus the late window. None = never."""
    due = assignment["due_at"]
    days = late_days_of(assignment)
    if not due or not days:
        return due
    return (datetime.datetime.fromisoformat(due)
            + datetime.timedelta(days=days)).isoformat(timespec="seconds")


def _is_open(assignment, now) -> bool:
    """Before (or at) the close: the deadline, or the end of its late window. redeem() and
    can_upload() both ask this, so a code stops opening the worksheet at the same instant
    the upload form disappears."""
    close = closes_at(assignment)
    return not close or now <= close


def can_upload(conn, submission, now) -> bool:
    return _is_open(get_assignment(conn, submission["assignment_id"]), now)


def is_late(conn, submission) -> bool:
    a = get_assignment(conn, submission["assignment_id"])
    return bool(a["due_at"] and submission["submitted_at"]
                and submission["submitted_at"] > a["due_at"])


def days_late(conn, submission) -> int:
    """Days past due_at, a part day counting as a whole one (one second over = 1). 0 if on time.

    A count, not a deduction: each course's late rule (and any extension) is the teacher's to
    apply, so this travels alongside the score exactly as `late` does."""
    a = get_assignment(conn, submission["assignment_id"])
    if not (a["due_at"] and submission["submitted_at"]):
        return 0
    over = (datetime.datetime.fromisoformat(submission["submitted_at"])
            - datetime.datetime.fromisoformat(a["due_at"])).total_seconds()
    return max(0, math.ceil(over / 86400))


def store_file(conn, submission, *, display_name, data: bytes, now, upload_dir):
    """Persist one uploaded file. The student names nothing on disk.

    Returns the row. Refuses oversize, empty, and over-count uploads with
    messages a student can act on.
    """
    if not can_upload(conn, submission, now):
        raise SubmitError("The deadline has passed.")
    if not data:
        raise SubmitError("That file is empty.")
    if len(data) > MAX_FILE_BYTES:
        raise SubmitError(
            f"That file is {len(data) // (1024*1024)} MB — the limit is "
            f"{MAX_FILE_BYTES // (1024*1024)} MB.")
    n = conn.execute("SELECT COUNT(*) c FROM submission_files WHERE submission_id = ?",
                     (submission["id"],)).fetchone()["c"]
    if n >= MAX_FILES_PER_SUBMISSION:
        raise SubmitError(f"You can attach at most {MAX_FILES_PER_SUBMISSION} files. "
                          f"Remove one first.")

    # The on-disk name is ours alone: random, flat, no extension. Nothing a
    # student sends can reach the filesystem.
    stored = secrets.token_hex(24)
    os.makedirs(upload_dir, mode=0o700, exist_ok=True)
    path = os.path.join(upload_dir, stored)
    fd = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
    with os.fdopen(fd, "wb") as fh:
        fh.write(data)

    cur = conn.execute(
        "INSERT INTO submission_files (submission_id, display_name, stored_name,"
        " size_bytes, sha256, uploaded_at) VALUES (?,?,?,?,?,?)",
        (submission["id"], safe_display_name(display_name), stored, len(data),
         hashlib.sha256(data).hexdigest(), now))
    conn.execute("UPDATE submissions SET submitted_at = ? WHERE id = ?",
                 (now, submission["id"]))
    conn.commit()
    return conn.execute("SELECT * FROM submission_files WHERE id = ?",
                        (cur.lastrowid,)).fetchone()


def list_files(conn, submission_id):
    return conn.execute(
        "SELECT * FROM submission_files WHERE submission_id = ? ORDER BY id",
        (submission_id,)).fetchall()


def delete_file(conn, submission, file_id, now, upload_dir):
    """Let a student replace a wrong upload before the deadline."""
    if not can_upload(conn, submission, now):
        raise SubmitError("The deadline has passed.")
    row = conn.execute(
        "SELECT * FROM submission_files WHERE id = ? AND submission_id = ?",
        (file_id, submission["id"])).fetchone()
    if row is None:
        raise SubmitError("No such file.")
    try:
        os.remove(os.path.join(upload_dir, row["stored_name"]))
    except OSError:
        pass                      # already gone; the row still goes
    conn.execute("DELETE FROM submission_files WHERE id = ?", (file_id,))
    conn.commit()


def open_file(conn, file_id, upload_dir):
    """(display_name, bytes) for download. Callers MUST serve as an attachment.

    `stored_name` came from `secrets.token_hex`, so it is hex-only by
    construction — re-checked here anyway, because this function turns a
    database value into a filesystem path and that is exactly the place a future
    change could go wrong quietly.
    """
    row = conn.execute("SELECT * FROM submission_files WHERE id = ?",
                       (file_id,)).fetchone()
    if row is None:
        return None
    stored = row["stored_name"]
    if not re.fullmatch(r"[0-9a-f]{48}", stored):
        return None
    path = os.path.join(upload_dir, stored)
    if not os.path.isfile(path):
        return None
    with open(path, "rb") as fh:
        return row["display_name"], fh.read()


def set_note(conn, submission, note, now):
    if not can_upload(conn, submission, now):
        raise SubmitError("The deadline has passed.")
    conn.execute("UPDATE submissions SET note = ? WHERE id = ?",
                 (str(note or "")[:4000], submission["id"]))
    conn.commit()


# --- grading + export ------------------------------------------------------

def grade(conn, submission_id, criterion, points, comment, now):
    conn.execute(
        "INSERT INTO rubric_scores (submission_id, criterion, points, comment,"
        " graded_at) VALUES (?,?,?,?,?)"
        " ON CONFLICT(submission_id, criterion) DO UPDATE SET"
        " points = excluded.points, comment = excluded.comment,"
        " graded_at = excluded.graded_at",
        (submission_id, criterion, None if points is None else float(points),
         str(comment or "")[:2000], now))
    conn.commit()


def score(conn, submission_id):
    """(earned, possible, complete). `complete` is False while any criterion is
    unmarked — an unmarked criterion is not a zero."""
    sub = conn.execute("SELECT * FROM submissions WHERE id = ?",
                       (submission_id,)).fetchone()
    if sub is None:
        return 0.0, 0.0, False
    a = get_assignment(conn, sub["assignment_id"])
    marks = {r["criterion"]: r["points"] for r in conn.execute(
        "SELECT criterion, points FROM rubric_scores WHERE submission_id = ?",
        (submission_id,)).fetchall()}

    earned, possible, complete = 0.0, 0.0, True
    for row in rubric_of(a):
        possible += float(row["max"])
        got = marks.get(row["criterion"])
        if got is None:
            complete = False
        else:
            earned += got
    return earned, possible, complete


def gradebook_rows(conn, assignment_id):
    """Per-student results in the shape instructor/gradebook/ consumes.

    A student who never submitted appears with `submitted=False` and no percent
    — never a 0. "Didn't hand it in" and "handed in and scored nothing" are
    different facts, and the late penalty (SUBMISSION.md: -10%/day up to 3 days)
    is the teacher's to apply, so `late` travels alongside rather than being
    silently deducted here.
    """
    codes = conn.execute(
        "SELECT student_id FROM submit_codes WHERE assignment_id = ? ORDER BY student_id",
        (assignment_id,)).fetchall()
    out = []
    for c in codes:
        sub = conn.execute(
            "SELECT * FROM submissions WHERE assignment_id = ? AND student_id = ?",
            (assignment_id, c["student_id"])).fetchone()
        if sub is None or not sub["submitted_at"]:
            out.append({"student_id": c["student_id"], "submission_id": None,
                        "submitted": False, "late": False, "days_late": 0, "files": 0,
                        "earned": None, "possible": None, "percent": None,
                        "fully_graded": False})
            continue
        earned, possible, complete = score(conn, sub["id"])
        out.append({
            "student_id": c["student_id"],
            "submission_id": sub["id"],
            "submitted": True,
            "late": is_late(conn, sub),
            "days_late": days_late(conn, sub),
            "files": len(list_files(conn, sub["id"])),
            "earned": earned,
            "possible": possible,
            "percent": (earned / possible * 100) if possible else None,
            "fully_graded": complete,
        })
    return out
