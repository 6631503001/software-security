"""Deadlines: stored in UTC, typed and shown in Thai time (ICT, UTC+7).

The incident this guards (Oct 2026): W10-15 deadlines were typed as "23:59" Thai time
into a field the app reads as UTC, so the portal kept accepting uploads until 06:59 the
next morning and showed students a bare "2026-10-24T23:59:00" with no zone. A W12
upload at 01:20 ICT was accepted without any "late" signal.
"""

import os
import re
import sys

import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
import submission as S  # noqa: E402
from test_submission import conn, make, open_sub, uploads  # noqa: E402,F401  (fixtures)

INVITE = "LETMEIN"


# --- converting what a person types ------------------------------------------

@pytest.mark.parametrize("typed, stored", [
    ("2026-11-07T23:59", "2026-11-07T16:59:00"),
    ("2026-11-07T23:59:00", "2026-11-07T16:59:00"),
    ("2026-11-07 23:59", "2026-11-07T16:59:00"),
    ("  2026-11-06T16:59  ", "2026-11-06T09:59:00"),
    ("2026-11-07T03:00", "2026-11-06T20:00:00"),     # crosses midnight backwards
])
def test_thai_time_typed_into_the_form_is_stored_as_utc(typed, stored):
    assert S.due_from_local(typed) == stored


@pytest.mark.parametrize("typed", ["", "   ", None])
def test_a_blank_deadline_means_no_deadline(typed):
    assert S.due_from_local(typed) is None


@pytest.mark.parametrize("typed", ["next friday", "2026-13-01T10:00", "23:59",
                                   "2026-11-07T23:59+00:00", "2026-11-07T16:59Z",
                                   "2026-11-07",            # date only = midnight, a day early
                                   "20261107T2359", "2026-W45-6T23:59",
                                   "2026-11-07T23:59:00.5", "2026-11-07T24:00",
                                   "0001-01-01T00:00"])     # underflows on conversion
def test_a_deadline_that_is_not_a_plain_thai_time_is_refused(typed):
    # An explicit offset is refused rather than honoured: the field is Thai time,
    # and silently accepting "+00:00" is how the two conventions got mixed before.
    with pytest.raises(ValueError):
        S.due_from_local(typed)


# --- showing a stored deadline ------------------------------------------------

def test_a_stored_utc_deadline_is_shown_in_thai_time_with_its_zone():
    assert S.due_label("2026-11-07T16:59:00") == "2026-11-07 23:59 ICT"
    assert S.due_label("2026-11-06T20:00:00") == "2026-11-07 03:00 ICT"


def test_a_deadline_with_seconds_shows_them_and_an_offset_is_respected():
    assert S.due_label("2026-11-07T16:59:37") == "2026-11-07 23:59:37 ICT"
    assert S.due_label("2026-11-07T23:59:00+07:00") == "2026-11-07 23:59 ICT"


def test_a_value_that_cannot_be_shown_falls_back_to_the_raw_text():
    assert S.due_label("9999-12-31T23:59:00") == "9999-12-31T23:59:00"
    assert S.due_label("not a date") == "not a date"


def test_no_deadline_shows_nothing():
    assert S.due_label(None) == ""
    assert S.due_label("") == ""


# --- the incident, end to end on the domain rules ---------------------------

def test_an_upload_at_0120_thai_time_after_a_2359_deadline_is_refused(conn, uploads):
    aid = make(conn, due_at=S.due_from_local("2026-10-24T23:59"))
    sub, _ = open_sub(conn, aid)
    one_minute_before = "2026-10-24T16:58:00"     # 23:58 ICT
    incident = "2026-10-24T18:20:19"              # 01:20 ICT on the 25th
    assert S.can_upload(conn, sub, one_minute_before)
    assert not S.can_upload(conn, sub, incident)
    with pytest.raises(S.SubmitError):
        S.store_file(conn, sub, display_name="w12.pdf", data=b"%PDF-1.4 x",
                     now=incident, upload_dir=uploads)


def test_a_submission_handed_in_after_the_thai_deadline_is_marked_late(conn):
    aid = make(conn, due_at=S.due_from_local("2026-10-24T23:59"))
    sub, _ = open_sub(conn, aid)
    conn.execute("UPDATE submissions SET submitted_at = ? WHERE id = ?",
                 ("2026-10-24T18:20:19", sub["id"]))
    conn.commit()
    sub = conn.execute("SELECT * FROM submissions WHERE id = ?", (sub["id"],)).fetchone()
    assert S.is_late(conn, sub)


# --- through the teacher form and the pages ---------------------------------

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
def teacher(appmod):
    client = appmod.app.test_client()
    html = client.get("/register").get_data(as_text=True)
    client.post("/register", data={
        "csrf_token": _csrf(html), "username": "teach1",
        "password": "correct horse battery", "invite": INVITE})
    return client


def _new_assignment(client, due):
    html = client.get("/work/new").get_data(as_text=True)
    return client.post("/work/new", data={
        "csrf_token": _csrf(html), "title": "Week 13 Worksheet", "due_at": due,
        "criterion": ["Lecture"], "max": ["100"]})


def test_the_form_says_thai_time_and_stores_utc(teacher, appmod):
    form = teacher.get("/work/new").get_data(as_text=True)
    assert "ICT" in form and "Due (UTC" not in form
    r = _new_assignment(teacher, "2026-11-07T23:59")
    assert r.status_code in (302, 303)
    row = appmod.get_db().execute("SELECT due_at FROM assignments ORDER BY id DESC").fetchone()
    assert row["due_at"] == "2026-11-07T16:59:00"


def test_a_malformed_deadline_re_shows_the_form_instead_of_500(teacher, appmod):
    r = _new_assignment(teacher, "next friday")
    assert r.status_code == 200
    assert "a date and time in Thai time" in r.get_data(as_text=True)
    assert appmod.get_db().execute("SELECT COUNT(*) FROM assignments").fetchone()[0] == 0


def test_pages_show_the_deadline_in_thai_time(teacher, appmod):
    _new_assignment(teacher, "2026-11-07T23:59")
    aid = appmod.get_db().execute("SELECT id FROM assignments").fetchone()["id"]
    for page in ("/work", f"/work/{aid}"):
        html = teacher.get(page).get_data(as_text=True)
        assert "2026-11-07 23:59 ICT" in html, page
        assert "2026-11-07T16:59:00" not in html, page


def test_the_student_page_shows_the_deadline_in_thai_time(teacher, appmod):
    _new_assignment(teacher, "2099-11-07T23:59")        # far future: the code still opens
    conn = appmod.get_db()
    aid = conn.execute("SELECT id FROM assignments").fetchone()["id"]
    code = S.issue_codes(conn, aid, ["65310001"], "2026-08-15T08:00:00")["65310001"]
    student = appmod.app.test_client()
    html = student.get("/submit").get_data(as_text=True)
    page = student.post("/submit", data={"csrf_token": _csrf(html), "code": code},
                        follow_redirects=True).get_data(as_text=True)
    assert "2099-11-07 23:59 ICT" in page
    assert "2099-11-07T16:59:00" not in page


# --- late window through the routes ------------------------------------------

def test_the_form_stores_a_late_window(teacher, appmod):
    html = teacher.get("/work/new").get_data(as_text=True)
    assert 'name="late_days"' in html
    r = teacher.post("/work/new", data={
        "csrf_token": _csrf(html), "title": "Week 1 Worksheet", "due_at": "2026-11-07T23:59",
        "late_days": "10", "criterion": ["Lecture"], "max": ["100"]})
    assert r.status_code in (302, 303)
    row = appmod.get_db().execute("SELECT late_days FROM assignments ORDER BY id DESC").fetchone()
    assert row["late_days"] == 10
    detail = teacher.get(r.headers["Location"]).get_data(as_text=True)
    assert "late uploads until 2026-11-17 23:59 ICT (10 days)" in detail


@pytest.mark.parametrize("typed", ["ten", "-1", "31"])
def test_a_bad_late_window_re_shows_the_form(teacher, appmod, typed):
    html = teacher.get("/work/new").get_data(as_text=True)
    r = teacher.post("/work/new", data={
        "csrf_token": _csrf(html), "title": "W", "due_at": "2026-11-07T23:59",
        "late_days": typed, "criterion": ["Lecture"], "max": ["100"]})
    assert r.status_code == 200
    page = r.get_data(as_text=True)
    assert "whole number of days" in page or "late window" in page
    assert appmod.get_db().execute("SELECT COUNT(*) FROM assignments").fetchone()[0] == 0


def test_a_student_past_the_deadline_inside_the_window_can_still_upload(teacher, appmod):
    import datetime
    client = appmod.app.test_client()          # the student, in their own browser
    conn = appmod.get_db()
    tid = conn.execute("SELECT id FROM teachers WHERE username='teach1'").fetchone()["id"]
    now = datetime.datetime.now(datetime.timezone.utc).replace(tzinfo=None, microsecond=0)
    due = (now - datetime.timedelta(days=2)).isoformat()
    t0 = (now - datetime.timedelta(days=5)).isoformat()
    aid = S.create_assignment(conn, teacher_id=tid, title="W1", now=t0, due_at=due, late_days=10)
    code = S.issue_codes(conn, aid, ["65310001"], t0)["65310001"]
    html = client.get("/submit").get_data(as_text=True)
    r = client.post("/submit", data={"csrf_token": _csrf(html), "code": code})
    assert r.status_code in (302, 303), "a code must still open inside the late window"
    page = client.get("/submit/work").get_data(as_text=True)
    assert "Uploads are still accepted" in page
    assert 'type="file"' in page
    csv_text = teacher.get(f"/work/{aid}/results.csv").get_data(as_text=True)
    assert csv_text.splitlines()[0].endswith(",days_late")
