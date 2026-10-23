"""What a student sees when a worksheet code does not open, and what the code is left as.

Codes are single-use (see submission.redeem), and every refusal used to say the same
"That code isn't valid." — for a typo, for a code the student had already used, and nothing at
all for a closed worksheet, which opened read-only and burned the code. Two students emailed
that the system was broken (21 and 23 Oct 2026): one had re-typed a code they had already used,
and the other burned their Week 6 code a month after Week 6 closed.

So a code that does not open says which of the three it is, and a code for a closed worksheet is
left unused, because the teacher has reopened deadlines before. The messages never name the
worksheet or the student.
"""

import io
import os
import sys

import pytest
from markupsafe import escape

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

# Reuse the real app/client/teacher fixtures and the CSRF helper.
from test_submit_routes import _csrf, appmod, client, teacher  # noqa: F401

import submission as S  # noqa: E402

STUDENT_A, STUDENT_B = "65310001", "65310002"
TITLE = "Week 10 Worksheet — API Security"
BEFORE = "2026-10-20T08:00:00"
DUE = "2026-10-24T23:59:00"
AFTER = "2026-10-25T08:00:00"
ENTRY_PAGES = ["/submit", "/code", "/quiz"]


@pytest.fixture
def clock(appmod):  # noqa: F811
    """The routes' clock, pinned. Set `clock.now` to move it."""
    class Clock:
        now = BEFORE
    c = Clock()
    appmod.app.config["NOW"] = lambda: c.now
    return c


@pytest.fixture
def worksheet(teacher, appmod, clock):  # noqa: F811
    """One assignment due at DUE, with a code for two students. Returns (assignment_id, codes)."""
    conn = appmod.get_db()
    tid = conn.execute("SELECT id FROM teachers WHERE username='teach1'").fetchone()["id"]
    aid = S.create_assignment(conn, teacher_id=tid, title=TITLE, due_at=DUE, now=BEFORE)
    return aid, S.issue_codes(conn, aid, [STUDENT_A, STUDENT_B], BEFORE)


def _enter(c, code, path="/submit"):
    html = c.get(path).get_data(as_text=True)
    return c.post(path, data={"csrf_token": _csrf(html), "code": code}, follow_redirects=False)


def _upload(c, name, data=b"x"):
    html = c.get("/submit/work").get_data(as_text=True)
    return c.post("/submit/work", content_type="multipart/form-data", data={
        "csrf_token": _csrf(html), "file": (io.BytesIO(data), name)})


def _redeemed_at(appmod, code):  # noqa: F811
    return appmod.get_db().execute(
        "SELECT redeemed_at FROM submit_codes WHERE code = ?", (code,)).fetchone()["redeemed_at"]


def _submissions(appmod, student):  # noqa: F811
    return appmod.get_db().execute(
        "SELECT COUNT(*) n FROM submissions WHERE student_id = ?", (student,)).fetchone()["n"]


def _shows(page, message):
    """The message as the page renders it (autoescaped: the apostrophe in "isn't" becomes &#39;)."""
    return str(escape(message)) in page


def _reveals_whose_code(page, student=STUDENT_A):
    return TITLE in page or str(escape(TITLE)) in page or student in page


# --- the three refusals -----------------------------------------------------

@pytest.mark.parametrize("path", ENTRY_PAGES)
def test_a_mistyped_code_says_to_check_the_characters(appmod, worksheet, path):  # noqa: F811
    r = _enter(appmod.app.test_client(), "ZZZZZZZZ", path)
    page = r.get_data(as_text=True)
    assert r.status_code == 200
    assert _shows(page, S.CODE_NOT_VALID)
    assert not _shows(page, S.CODE_ALREADY_USED) and not _shows(page, S.CODE_DEADLINE_PASSED)


@pytest.mark.parametrize("path", ENTRY_PAGES)
def test_a_used_code_says_it_was_used_and_not_whose_it_is(appmod, worksheet, clock, path):  # noqa: F811
    _, codes = worksheet
    code = codes[STUDENT_A]
    assert _enter(appmod.app.test_client(), code).status_code in (302, 303)
    first = _redeemed_at(appmod, code)

    clock.now = "2026-10-21T09:00:00"            # a day later, on another device
    r = _enter(appmod.app.test_client(), code, path)
    page = r.get_data(as_text=True)
    assert r.status_code == 200
    assert _shows(page, S.CODE_ALREADY_USED)
    assert not _shows(page, S.CODE_NOT_VALID)
    assert not _reveals_whose_code(page)
    assert _redeemed_at(appmod, code) == first, "a refused retry must not touch the code"


@pytest.mark.parametrize("path", ENTRY_PAGES)
def test_a_code_for_a_closed_worksheet_is_refused_and_left_unused(appmod, worksheet, clock, path):  # noqa: F811
    _, codes = worksheet
    code = codes[STUDENT_A]
    clock.now = AFTER
    student = appmod.app.test_client()
    r = _enter(student, code, path)
    page = r.get_data(as_text=True)
    assert r.status_code == 200
    assert _shows(page, S.CODE_DEADLINE_PASSED)
    assert not _reveals_whose_code(page)
    assert _redeemed_at(appmod, code) is None, "a closed worksheet must not burn the code"
    assert _submissions(appmod, STUDENT_A) == 0, "nor open a submission"
    # ...and the browser was not signed in to anything
    assert student.get("/submit/work").status_code in (302, 303)


def test_the_same_code_works_once_the_teacher_reopens_the_worksheet(appmod, worksheet, clock):  # noqa: F811
    aid, codes = worksheet
    code = codes[STUDENT_A]
    clock.now = AFTER
    assert _shows(_enter(appmod.app.test_client(), code).get_data(as_text=True),
                  S.CODE_DEADLINE_PASSED)

    conn = appmod.get_db()                          # how the W1-6 resubmission window was opened
    conn.execute("UPDATE assignments SET due_at = ? WHERE id = ?", ("2026-11-03T23:59:00", aid))
    conn.commit()
    student = appmod.app.test_client()
    r = _enter(student, code)
    assert r.status_code in (302, 303) and "/submit/work" in r.headers["Location"]
    assert _upload(student, "late.pdf").status_code == 200
    assert "late.pdf" in student.get("/submit/work").get_data(as_text=True)
    assert _redeemed_at(appmod, code) == AFTER


def test_a_used_code_for_a_closed_worksheet_still_says_used(appmod, worksheet, clock):  # noqa: F811
    # "Used" is the true reason here; the closed message would say the code is still unused.
    _, codes = worksheet
    code = codes[STUDENT_A]
    _enter(appmod.app.test_client(), code)
    clock.now = AFTER
    page = _enter(appmod.app.test_client(), code).get_data(as_text=True)
    assert _shows(page, S.CODE_ALREADY_USED)
    assert not _shows(page, S.CODE_DEADLINE_PASSED)


# --- the code still works the way it should ---------------------------------

@pytest.mark.parametrize("path", ENTRY_PAGES)
def test_a_fresh_code_opens_its_worksheet_and_is_burned_exactly_once(appmod, worksheet, clock, path):  # noqa: F811
    _, codes = worksheet
    code = codes[STUDENT_A]
    student = appmod.app.test_client()
    r = _enter(student, code, path)
    assert r.status_code in (302, 303) and "/submit/work" in r.headers["Location"]
    page = student.get("/submit/work").get_data(as_text=True)
    assert STUDENT_A in page and 'type="file"' in page
    assert _redeemed_at(appmod, code) == BEFORE
    assert _submissions(appmod, STUDENT_A) == 1

    clock.now = "2026-10-21T09:00:00"
    assert _enter(appmod.app.test_client(), code, path).status_code == 200
    assert _redeemed_at(appmod, code) == BEFORE, "burned once, at the first redemption"
    assert _submissions(appmod, STUDENT_A) == 1


def test_after_the_deadline_a_code_still_opens_released_feedback_read_only(appmod, worksheet, clock):  # noqa: F811
    # The one thing a code is still for after the deadline: a student who handed in, then lost
    # the session (new device), gets a re-issued code to read their marks.
    aid, codes = worksheet
    laptop = appmod.app.test_client()
    _enter(laptop, codes[STUDENT_A])
    _upload(laptop, "evidence.pdf")
    clock.now = AFTER
    conn = appmod.get_db()
    conn.execute("UPDATE assignments SET released = 1 WHERE id = ?", (aid,))
    conn.commit()
    new_code = S.issue_codes(conn, aid, [STUDENT_A], AFTER)[STUDENT_A]

    phone = appmod.app.test_client()
    assert _enter(phone, new_code).status_code in (302, 303)
    page = phone.get("/submit/work").get_data(as_text=True)
    assert "evidence.pdf" in page and "Your marks" in page
    assert "The deadline has passed." in page and 'type="file"' not in page, "read-only"
    assert _redeemed_at(appmod, new_code) == AFTER, "a code that grants access is burned"


# --- /quiz shares the path --------------------------------------------------

def test_a_submit_code_typed_into_quiz_on_a_shared_pc_does_not_open_the_last_students_work(
        appmod, teacher, clock):  # noqa: F811
    # /quiz used to set session["submission_id"] itself, skipping remember_submission(), so the
    # browser kept the previous student's worksheets and the next one could open them.
    conn = appmod.get_db()
    tid = conn.execute("SELECT id FROM teachers WHERE username='teach1'").fetchone()["id"]
    w10 = S.create_assignment(conn, teacher_id=tid, title="W10", due_at=DUE, now=BEFORE)
    w11 = S.create_assignment(conn, teacher_id=tid, title="W11", due_at=DUE, now=BEFORE)
    alice = S.issue_codes(conn, w10, [STUDENT_A], BEFORE)[STUDENT_A]
    bob = S.issue_codes(conn, w11, [STUDENT_B], BEFORE)[STUDENT_B]

    pc = appmod.app.test_client()
    _enter(pc, alice)
    _upload(pc, "alice-ten.pdf")
    alice_sub = conn.execute("SELECT id FROM submissions WHERE student_id = ?",
                             (STUDENT_A,)).fetchone()["id"]
    alice_file = conn.execute("SELECT id FROM submission_files WHERE submission_id = ?",
                              (alice_sub,)).fetchone()["id"]

    assert _enter(pc, bob, "/quiz").status_code in (302, 303)
    page = pc.get("/submit/work").get_data(as_text=True)
    assert STUDENT_B in page and STUDENT_A not in page and "alice-ten.pdf" not in page
    html = pc.get("/submit/work").get_data(as_text=True)
    switched = pc.post("/submit/work/switch", data={"csrf_token": _csrf(html),
                                                     "submission_id": alice_sub})
    assert switched.status_code == 404, "Bob must not be able to open Alice's worksheet"
    assert pc.get(f"/work/file/{alice_file}").status_code == 404, "...or download Alice's file"


@pytest.mark.parametrize("path", ENTRY_PAGES)
def test_a_worksheet_opened_from_any_entry_page_survives_closing_the_browser(
        appmod, worksheet, path):  # noqa: F811
    # The code is spent on the first redemption, so the session it starts is the only way back:
    # it must be a lasting cookie (remember_submission makes it permanent), not one the browser
    # drops on close. /quiz used to skip that.
    _, codes = worksheet
    r = _enter(appmod.app.test_client(), codes[STUDENT_A], path)
    assert r.status_code in (302, 303)
    assert "Expires=" in r.headers.get("Set-Cookie", ""), f"{path}: session cookie dies with the browser"


def test_a_session_the_old_quiz_path_mixed_up_no_longer_reaches_the_other_students_work(
        appmod, teacher, clock):  # noqa: F811
    # Browsers signed in through the old /quiz path still carry Alice's worksheet in Bob's list
    # (submission_ids=[Alice's, Bob's], submission_id=Bob's), for up to 180 days. Deploying the
    # /quiz fix alone would leave those open; only the on-screen student's worksheets count.
    conn = appmod.get_db()
    tid = conn.execute("SELECT id FROM teachers WHERE username='teach1'").fetchone()["id"]
    w10 = S.create_assignment(conn, teacher_id=tid, title="W10", due_at=DUE, now=BEFORE)
    w11 = S.create_assignment(conn, teacher_id=tid, title="W11", due_at=DUE, now=BEFORE)
    pc = appmod.app.test_client()
    _enter(pc, S.issue_codes(conn, w10, [STUDENT_A], BEFORE)[STUDENT_A])
    _upload(pc, "alice-ten.pdf")
    _enter(pc, S.issue_codes(conn, w11, [STUDENT_B], BEFORE)[STUDENT_B])
    alice_sub, bob_sub = (conn.execute(
        "SELECT id FROM submissions WHERE student_id = ?", (s,)).fetchone()["id"]
        for s in (STUDENT_A, STUDENT_B))
    alice_file = conn.execute("SELECT id FROM submission_files WHERE submission_id = ?",
                              (alice_sub,)).fetchone()["id"]
    with pc.session_transaction() as s:
        s["submission_ids"] = [alice_sub, bob_sub]
        s["submission_id"] = bob_sub

    page = pc.get("/submit/work").get_data(as_text=True)
    assert STUDENT_B in page and "Your worksheets" not in page, "W10 is not Bob's to switch to"
    html = pc.get("/submit/work").get_data(as_text=True)
    assert pc.post("/submit/work/switch", data={"csrf_token": _csrf(html),
                                                "submission_id": alice_sub}).status_code == 404
    assert pc.get(f"/work/file/{alice_file}").status_code == 404
