"""One browser, several worksheets.

W10-12 share one due date, so a student naturally opens all three codes in one
browser. Codes are single-use (see submission.redeem), so the browser has to
REMEMBER every worksheet it opened: when it remembered only the latest, opening
W11 stranded W10 for good (re-entering its code = "That code isn't valid.") and
the student had to ask the teacher for a new one. Found when 6631503039 emailed
that her codes "don't work".
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


@pytest.fixture
def worksheets(teacher, appmod):  # noqa: F811
    """Two assignments with the same due date, each with a code for two students."""
    import submission as S
    conn = appmod.get_db()
    tid = conn.execute("SELECT id FROM teachers WHERE username='teach1'").fetchone()["id"]
    out = {}
    for title in ("W10", "W11"):
        wid = S.create_assignment(conn, teacher_id=tid, title=title, now="2026-10-10T08:00:00")
        out[title] = S.issue_codes(conn, wid, [STUDENT_A, STUDENT_B], "2026-10-10T08:00:00")
    return out


def _enter(c, code, path="/submit"):
    html = c.get(path).get_data(as_text=True)
    return c.post(path, data={"csrf_token": _csrf(html), "code": code}, follow_redirects=False)


def _workspace(c):
    return c.get("/submit/work").get_data(as_text=True)


def _upload(c, name, data=b"x"):
    html = _workspace(c)
    return c.post("/submit/work", content_type="multipart/form-data", data={
        "csrf_token": _csrf(html), "file": (io.BytesIO(data), name)})


def _switch(c, submission_id):
    html = _workspace(c)
    return c.post("/submit/work/switch", data={"csrf_token": _csrf(html),
                                              "submission_id": submission_id})


def _sub_id(appmod, title, student):  # noqa: F811
    return appmod.get_db().execute(
        "SELECT s.id FROM submissions s JOIN assignments a ON a.id = s.assignment_id"
        " WHERE a.title = ? AND s.student_id = ?", (title, student)).fetchone()["id"]


def _file_id(appmod, sub_id):  # noqa: F811
    return appmod.get_db().execute(
        "SELECT id FROM submission_files WHERE submission_id = ?", (sub_id,)).fetchone()["id"]


def _on_screen(page):
    """The title of the worksheet the workspace is showing (the <title> is '<assignment> — ...')."""
    return page.split("<title>")[1].split(" — ")[0]


@pytest.mark.parametrize("path", ["/submit", "/code"])
def test_opening_a_second_worksheet_does_not_strand_the_first(appmod, worksheets, path):  # noqa: F811
    student = appmod.app.test_client()
    assert _enter(student, worksheets["W10"][STUDENT_A], path).status_code in (302, 303)
    assert _enter(student, worksheets["W11"][STUDENT_A], path).status_code in (302, 303)

    # W11 is the one on screen, and W10 is still reachable from it, with no code.
    page = _workspace(student)
    assert _on_screen(page) == "W11"
    assert "Your worksheets" in page and "W10" in page
    assert _switch(student, _sub_id(appmod, "W10", STUDENT_A)).status_code in (302, 303)
    assert _on_screen(_workspace(student)) == "W10"


def test_each_worksheet_keeps_its_own_files_when_switching(appmod, worksheets):  # noqa: F811
    student = appmod.app.test_client()
    _enter(student, worksheets["W10"][STUDENT_A])
    _upload(student, "ten.pdf")
    _enter(student, worksheets["W11"][STUDENT_A])
    _upload(student, "eleven.pdf")

    assert "eleven.pdf" in _workspace(student) and "ten.pdf" not in _workspace(student)
    _switch(student, _sub_id(appmod, "W10", STUDENT_A))
    assert "ten.pdf" in _workspace(student) and "eleven.pdf" not in _workspace(student)
    # ...and the student can still download a file from the worksheet that is NOT on screen.
    other = _file_id(appmod, _sub_id(appmod, "W11", STUDENT_A))
    assert student.get(f"/work/file/{other}").status_code == 200


def test_a_worksheet_that_is_not_in_this_browser_cannot_be_switched_to(appmod, worksheets):  # noqa: F811
    alice = appmod.app.test_client()
    _enter(alice, worksheets["W10"][STUDENT_A])
    bob = appmod.app.test_client()
    _enter(bob, worksheets["W10"][STUDENT_B])
    bob_sub = _sub_id(appmod, "W10", STUDENT_B)

    # Bob's submission id (a small, guessable integer) must not be reachable from Alice's browser,
    # nor an id that does not exist.
    assert _switch(alice, bob_sub).status_code == 404
    assert _switch(alice, 99999).status_code == 404
    # and a refused switch must not have changed what Alice sees
    assert STUDENT_A in _workspace(alice) and STUDENT_B not in _workspace(alice)


def test_a_second_student_on_the_same_browser_does_not_inherit_the_first_ones_work(
        appmod, worksheets):  # noqa: F811
    # A shared lab PC: Alice hands in, then Bob opens his code in the same browser.
    pc = appmod.app.test_client()
    _enter(pc, worksheets["W10"][STUDENT_A])
    _upload(pc, "alice-ten.pdf")
    alice_w10 = _sub_id(appmod, "W10", STUDENT_A)
    alice_file = _file_id(appmod, alice_w10)

    _enter(pc, worksheets["W11"][STUDENT_B])
    page = _workspace(pc)
    assert STUDENT_B in page and STUDENT_A not in page
    assert "alice-ten.pdf" not in page
    assert _switch(pc, alice_w10).status_code == 404, "Bob must not be able to open Alice's worksheet"
    assert pc.get(f"/work/file/{alice_file}").status_code == 404, "...or download her files"


def test_a_session_from_before_this_fix_still_opens_its_worksheet(appmod, worksheets):  # noqa: F811
    # Students are signed in right now with the OLD session shape (one `submission_id`, no list).
    # Deploying must not sign them out of the worksheet they are in the middle of.
    student = appmod.app.test_client()
    _enter(student, worksheets["W10"][STUDENT_A])
    _upload(student, "ten.pdf")
    sid = _sub_id(appmod, "W10", STUDENT_A)
    with student.session_transaction() as s:
        s.pop("submission_ids", None)
        s["submission_id"] = sid
    assert "ten.pdf" in _workspace(student)
    assert student.get(f"/work/file/{_file_id(appmod, sid)}").status_code == 200
    # and opening the next worksheet from that old session keeps the one they were in
    _enter(student, worksheets["W11"][STUDENT_A])
    page = _workspace(student)
    assert _on_screen(page) == "W11" and "W10" in page.split("Your worksheets")[1]


def test_a_used_code_still_cannot_be_redeemed_again_from_another_browser(appmod, worksheets):  # noqa: F811
    # The point of single-use codes (the leaked-slip exploit) must survive this change.
    code = worksheets["W10"][STUDENT_A]
    assert _enter(appmod.app.test_client(), code).status_code in (302, 303)
    again = _enter(appmod.app.test_client(), code)
    assert again.status_code == 200
    assert str(escape(S.CODE_ALREADY_USED)) in again.get_data(as_text=True)


def test_typing_a_used_code_while_signed_in_points_back_to_the_open_worksheet(appmod, worksheets):  # noqa: F811
    # What the student in the screenshot did: she was signed in, typed the (now used) code
    # again, and saw only "That code isn't valid." with no way forward.
    student = appmod.app.test_client()
    code = worksheets["W10"][STUDENT_A]
    _enter(student, code)
    for path in ("/submit", "/code"):
        page = _enter(student, code, path).get_data(as_text=True)
        assert str(escape(S.CODE_ALREADY_USED)) in page
        assert 'href="/submit/work"' in page, f"{path}: no link back to the worksheet she has open"
    # ...whereas someone with nothing open is not shown a link to nowhere.
    fresh = _enter(appmod.app.test_client(), code).get_data(as_text=True)
    assert 'href="/submit/work"' not in fresh


def test_the_entry_pages_no_longer_promise_a_reusable_code(appmod, worksheets):  # noqa: F811
    for path in ("/submit", "/code"):
        page = appmod.app.test_client().get(path).get_data(as_text=True).lower()
        assert "same code until the deadline" not in page, path


def test_switching_needs_the_csrf_token(appmod, worksheets):  # noqa: F811
    student = appmod.app.test_client()
    _enter(student, worksheets["W10"][STUDENT_A])
    _enter(student, worksheets["W11"][STUDENT_A])
    w10 = _sub_id(appmod, "W10", STUDENT_A)
    r = student.post("/submit/work/switch", data={"submission_id": w10})   # no csrf_token
    assert r.status_code in (400, 403)
    assert _on_screen(_workspace(student)) == "W11", "a forged request must not move the student"
