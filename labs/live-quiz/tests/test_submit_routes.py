"""Route tests for the worksheet submission entry point.

Narrow on purpose: submission.py's own tests (test_submission.py) already cover
the domain rules. This covers just the one thing that needs a real Flask
request/response cycle — the cross-kind rescue added alongside the unified
/code entry point, so a quiz code pasted into this box lands the student in
their quiz instead of a bare "not valid".
"""

import os
import re
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

INVITE = "LETMEIN"


def _csrf(html):
    m = re.search(r'name="csrf_token" value="([^"]+)"', html)
    assert m, "no CSRF token in the rendered form"
    return m.group(1)


@pytest.fixture
def appmod(tmp_path, monkeypatch):
    monkeypatch.setenv("DB_PATH", str(tmp_path / "t.db"))
    monkeypatch.setenv("INVITE_CODE", INVITE)
    monkeypatch.setenv("SECRET_KEY", "test-secret")
    import importlib
    import app as _a
    importlib.reload(_a)
    _a.app.config["TESTING"] = True
    return _a


@pytest.fixture
def client(appmod):
    return appmod.app.test_client()


@pytest.fixture
def teacher(client):
    html = client.get("/register").get_data(as_text=True)
    client.post("/register", data={
        "csrf_token": _csrf(html), "username": "teach1",
        "password": "correct horse battery", "invite": INVITE})
    return client


@pytest.fixture
def published(teacher, appmod):
    """A published assignment, with a submission code for one student."""
    import submission as S
    conn = appmod.get_db()
    tid = conn.execute("SELECT id FROM teachers WHERE username='teach1'").fetchone()["id"]
    wid = S.create_assignment(conn, teacher_id=tid, title="W4", now="2026-08-15T08:00:00")
    codes = S.issue_codes(conn, wid, ["65310001"], "2026-08-15T08:00:00")
    return wid, codes


def test_a_quiz_code_typed_into_submit_rescues_into_the_quiz(client, appmod, published):
    import assessment as A
    conn = appmod.get_db()
    tid = conn.execute("SELECT id FROM teachers WHERE username='teach1'").fetchone()["id"]
    aid = A.publish(conn, teacher_id=tid, title="Q",
                    questions=[{"stem": "q?", "options": ["a", "b"], "correct": 0}],
                    now="2026-08-15T08:00:00")
    quizcodes = A.issue_codes(conn, aid, ["65310099"], "2026-08-15T08:00:00")

    html = client.get("/submit").get_data(as_text=True)
    r = client.post("/submit", data={"csrf_token": _csrf(html), "code": quizcodes["65310099"]},
                    follow_redirects=False)
    assert r.status_code in (302, 303)
    assert "/quiz/take" in r.headers["Location"]


def test_a_terminal_quiz_code_typed_into_submit_shows_its_real_message(client, appmod, published):
    # find_kind() correctly says "quiz" for this code, so the rescue is
    # attempted — but the quiz is already submitted, so the rescue's own
    # redeem() fails too. That failure must reach the page, not a generic
    # "not valid" and not a 500.
    import assessment as A
    conn = appmod.get_db()
    tid = conn.execute("SELECT id FROM teachers WHERE username='teach1'").fetchone()["id"]
    aid = A.publish(conn, teacher_id=tid, title="Q",
                    questions=[{"stem": "q?", "options": ["a", "b"], "correct": 0}],
                    now="2026-08-15T08:00:00")
    quizcodes = A.issue_codes(conn, aid, ["65310098"], "2026-08-15T08:00:00")
    att = A.redeem(conn, quizcodes["65310098"], "2026-08-15T08:05:00")
    A.submit(conn, att, "2026-08-15T08:10:00")   # burns it — now terminal

    html = client.get("/submit").get_data(as_text=True)
    r = client.post("/submit", data={"csrf_token": _csrf(html), "code": quizcodes["65310098"]})
    assert r.status_code == 200
    assert "already submitted" in r.get_data(as_text=True).lower()


def test_an_unknown_code_on_submit_is_still_refused_plainly(client, published):
    html = client.get("/submit").get_data(as_text=True)
    page = client.post("/submit", data={"csrf_token": _csrf(html),
                                        "code": "ZZZZZZZZ"}).get_data(as_text=True)
    assert "valid" in page.lower()


def test_a_leaked_code_cannot_be_redeemed_a_second_time_by_someone_else(
        client, appmod, published):
    # The actual exploit Codex's security review flagged: submission codes
    # never burned, so a classmate who saw/photographed the printed code
    # could redeem it themselves at any later point and get the same
    # read/write access as the real student — including deleting their
    # files or reading grades after release. First redemption must still
    # work; a second redemption of the SAME code, from a fresh browser with
    # no cookies at all, must now be refused rather than silently handing
    # over the workspace.
    wid, codes = published
    code = codes["65310001"]

    html = client.get("/submit").get_data(as_text=True)
    r = client.post("/submit", data={"csrf_token": _csrf(html), "code": code},
                    follow_redirects=False)
    assert r.status_code in (302, 303)
    assert "/submit/work" in r.headers["Location"]

    attacker = appmod.app.test_client()  # fresh client: no cookies, no session
    html2 = attacker.get("/submit").get_data(as_text=True)
    r2 = attacker.post("/submit", data={"csrf_token": _csrf(html2), "code": code},
                       follow_redirects=False)
    assert r2.status_code not in (302, 303), (
        "a second redemption of the same code must not reach the workspace"
    )
    assert "valid" in r2.get_data(as_text=True).lower()


def test_a_fresh_colliding_code_does_not_silently_authenticate_into_the_workspace(
        client, appmod, published):
    # Mirror of the same case in test_assess_routes.py: a code that is a
    # genuinely fresh submit code for one student AND (fabricated) an
    # attempt_codes row for a DIFFERENT student. S.redeem() alone has no way
    # to know the attempt_codes row exists, so it succeeds outright on its
    # own terms. POSTing it to /submit must not redirect into the workspace —
    # the ambiguity must be refused, not resolved by whichever table the
    # entry route happens to check first.
    wid, codes = published
    submit_code = codes["65310001"]

    import assessment as A
    conn = appmod.get_db()
    tid = conn.execute("SELECT id FROM teachers WHERE username='teach1'").fetchone()["id"]
    aid = A.publish(conn, teacher_id=tid, title="Q",
                    questions=[{"stem": "q?", "options": ["a", "b"], "correct": 0}],
                    now="2026-08-15T08:00:00")
    conn.execute(
        "INSERT INTO attempt_codes (code, assessment_id, student_id, issued_at)"
        " VALUES (?, ?, '65310099', ?)", (submit_code, aid, "2026-08-15T08:00:00"))
    conn.commit()

    html = client.get("/submit").get_data(as_text=True)
    r = client.post("/submit", data={"csrf_token": _csrf(html), "code": submit_code},
                    follow_redirects=False)
    assert r.status_code not in (302, 303), (
        "a colliding code must not silently redirect into the submission workspace")
    still_untouched = conn.execute(
        "SELECT 1 FROM submissions WHERE assignment_id = ? AND student_id = '65310001'",
        (wid,)).fetchone()
    assert still_untouched is None, "no submission should have been created for the ambiguous code"
