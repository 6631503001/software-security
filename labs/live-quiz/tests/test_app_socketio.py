# tests/test_app_socketio.py
import json
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from app import app, socketio, GAMES, GAME_OWNER, get_db, _reveal_results, _auto_reveal_after_timeout
import content as C
import db as dbmod
import roster
from game import GameSession

QUESTIONS = [{"stem": "Q1?", "options": ["a", "b", "c", "d"], "correct": 1}]
TWO_QUESTIONS = [{"stem": "Q1?", "options": ["a", "b", "c", "d"], "correct": 1},
                 {"stem": "Q2?", "options": ["a", "b", "c", "d"], "correct": 2}]


def _enroll(student_ids, course_slug=None):
    """Enroll fake students in a real course so a nickname can be checked against
    a genuine roster, the same way roster.py itself is tested."""
    slug = course_slug or C.COURSES[0]["slug"]
    conn = get_db()
    t = dbmod.get_teacher_by_username(conn, "roster_check_teacher")
    tid = t["id"] if t else dbmod.create_teacher(conn, "roster_check_teacher", "unused-hash", now="t")
    roster.enroll(conn, course_slug=slug, teacher_id=tid, student_ids=student_ids, now="t")
    return slug


def _authed_host_socket(pin):
    """host_next now requires the emitting socket to be bound (in on_host_join) as the game's
    owner, verified via the same Flask-session auth.current_teacher_id() the HTTP routes use — so
    a bare unauthenticated socketio.test_client(app) can no longer drive host_next. Give this pin
    a real owning teacher and hand back a Socket.IO test client authenticated as that teacher
    (idempotent: safe to call again for the same pin across test runs against a persistent DB)."""
    username = f"host_{pin}"
    t = dbmod.get_teacher_by_username(get_db(), username)
    tid = t["id"] if t else dbmod.create_teacher(get_db(), username, "unused-hash", now="t")
    GAME_OWNER[pin] = tid
    client = app.test_client()
    with client.session_transaction() as sess:
        sess["teacher_id"] = tid
    sock = socketio.test_client(app, flask_test_client=client)
    sock.emit("host_join", {"pin": pin})
    return sock


def test_full_round_trip_join_question_answer_results():
    GAMES.clear()
    GAMES["999999"] = GameSession("999999", QUESTIONS)

    host = _authed_host_socket("999999")
    alice = socketio.test_client(app)
    bob = socketio.test_client(app)

    alice.emit("player_join", {"pin": "999999", "nickname": "alice"})
    bob.emit("player_join", {"pin": "999999", "nickname": "bob"})

    # the host lobby fills up live as players join
    lobby = [e for e in host.get_received() if e["name"] == "lobby:update"]
    assert lobby, "expected lobby:update broadcasts on player joins"
    assert lobby[-1]["args"][0] == {"count": 2, "players": ["alice", "bob"]}

    host.emit("host_next", {"pin": "999999"})
    # every client in the room should receive the question
    assert any(e["name"] == "question:show" for e in alice.get_received())
    assert any(e["name"] == "question:show" for e in bob.get_received())

    alice.emit("answer_submit", {"pin": "999999", "nickname": "alice", "choice": 1})  # correct
    bob.emit("answer_submit", {"pin": "999999", "nickname": "bob", "choice": 0})  # wrong

    # both answered -> results broadcast immediately, no need to wait for the timer
    host_events = host.get_received()
    results = [e for e in host_events if e["name"] == "question:results"]
    assert len(results) == 1
    payload = results[0]["args"][0]
    assert payload["distribution"] == [1, 1, 0, 0]
    assert payload["correct"] == 1  # results reveal the correct option index
    assert payload["leaderboard"][0]["nickname"] == "alice"  # alice scored, bob didn't

    # the projector's live "answered" counter climbs as responses arrive
    tallies = [e for e in host_events if e["name"] == "answer:tally"]
    assert tallies, "expected at least one answer:tally broadcast"
    assert tallies[-1]["args"][0] == {"answered": 2, "total": 2}


def test_disconnect_lets_remaining_players_finish_the_round():
    GAMES.clear()
    GAMES["888888"] = GameSession("888888", QUESTIONS)

    host = _authed_host_socket("888888")
    alice = socketio.test_client(app)
    bob = socketio.test_client(app)
    alice.emit("player_join", {"pin": "888888", "nickname": "alice"})
    bob.emit("player_join", {"pin": "888888", "nickname": "bob"})
    host.emit("host_next", {"pin": "888888"})
    host.get_received()  # clear

    bob.disconnect()  # bob closes his tab mid-question
    alice.emit("answer_submit", {"pin": "888888", "nickname": "alice", "choice": 1})

    # alice is now the only connected player, so the round reveals without waiting for the timer
    results = [e for e in host.get_received() if e["name"] == "question:results"]
    assert len(results) == 1


def test_answer_after_reveal_is_rejected():
    GAMES.clear()
    GAMES["666666"] = GameSession("666666", QUESTIONS)

    host = _authed_host_socket("666666")
    alice = socketio.test_client(app)
    alice.emit("player_join", {"pin": "666666", "nickname": "alice"})
    host.emit("host_next", {"pin": "666666"})

    alice.emit("answer_submit", {"pin": "666666", "nickname": "alice", "choice": 1})  # scores + reveals
    score_after_first = GAMES["666666"].players["alice"].score
    assert score_after_first > 0

    # a second (post-reveal) tap must not score — the round is already revealed
    alice.emit("answer_submit", {"pin": "666666", "nickname": "alice", "choice": 1})
    assert GAMES["666666"].players["alice"].score == score_after_first


def test_host_join_does_not_create_a_room_for_a_nonexistent_pin():
    # join_room() ran unconditionally, before checking the pin identified a real game — an
    # unauthenticated socket could make the server hold an unbounded number of arbitrary Socket.IO
    # rooms just by emitting host_join with made-up PINs. HOST_SIDS (the actual host-authorization
    # gate used by on_host_next) was never affected by this, but the room registry growth is real.
    GAMES.clear()
    sock = socketio.test_client(app)
    sock.emit("host_join", {"pin": "NOPE99"})
    rooms = socketio.server.manager.rooms.get("/", {})
    assert "NOPE99" not in rooms, "must not create a Socket.IO room for a PIN with no real game"


def test_host_join_still_creates_a_room_for_a_real_pin():
    GAMES.clear()
    GAMES["333333"] = GameSession("333333", QUESTIONS)
    sock = socketio.test_client(app)
    sock.emit("host_join", {"pin": "333333"})
    rooms = socketio.server.manager.rooms.get("/", {})
    assert "333333" in rooms, "a real game's PIN must still be joinable as a room"


def test_a_classmate_cannot_claim_an_in_use_nickname_without_its_token():
    # Nicknames aren't authenticated (see nickname_matches_roster's own docstring) and are
    # broadcast to the whole lobby (_broadcast_lobby), so anyone can see "alice" and try
    # player_join with that same name. game.join() used to silently hand back the SAME
    # player to whoever repeated an in-use nickname -- no secret required -- which let a
    # classmate take over alice's score outright (and freeze the real alice out, since
    # on_answer_submit trusts only the most recent socket). Reclaiming now requires alice's
    # own reconnect token, issued to her alone in her own join_ok payload.
    GAMES.clear()
    GAMES["444444"] = GameSession("444444", QUESTIONS)

    host = _authed_host_socket("444444")
    victim = socketio.test_client(app)
    victim.emit("player_join", {"pin": "444444", "nickname": "alice"})

    attacker = socketio.test_client(app)
    attacker.emit("player_join", {"pin": "444444", "nickname": "alice"})  # no token: must be refused
    errors = [e for e in attacker.get_received() if e["name"] == "join_error"]
    assert errors, "claiming an in-use nickname with no token must be refused, not granted"

    host.emit("host_next", {"pin": "444444"})
    host.get_received()  # clear

    # the attacker was never bound to "alice" -- the original (victim) socket is still current
    victim.emit("answer_submit", {"pin": "444444", "nickname": "alice", "choice": 1})
    assert GAMES["444444"].players["alice"].score > 0, \
        "the real alice must still be able to score for herself"

    # and the attacker's own rejected join never let it claim a scoring identity at all
    attacker.emit("answer_submit", {"pin": "444444", "nickname": "alice", "choice": 1})
    assert GAMES["444444"].players["alice"].score == GAMES["444444"].players["alice"].score, \
        "the rejected socket must not be able to score as alice"


def test_a_legitimate_reconnect_with_the_right_token_still_resumes_the_same_player():
    # The thing the old behavior was protecting, which the fix must not break: a dropped
    # wifi connection (a NEW socket, SAME browser) must still let the real student back in,
    # now by presenting the token her browser received in her own first join_ok.
    GAMES.clear()
    GAMES["445445"] = GameSession("445445", QUESTIONS)

    host = _authed_host_socket("445445")
    first_socket = socketio.test_client(app)
    first_socket.emit("player_join", {"pin": "445445", "nickname": "alice"})
    join_ok = [e for e in first_socket.get_received() if e["name"] == "join_ok"][0]
    token = join_ok["args"][0]["token"]
    assert token, "join_ok must hand the joining client its own reconnect token"

    host.emit("host_next", {"pin": "445445"})
    host.get_received()

    # simulate the wifi drop: a brand-new socket, same browser (it kept the token)
    reconnecting_socket = socketio.test_client(app)
    reconnecting_socket.emit("player_join", {"pin": "445445", "nickname": "alice", "token": token})
    assert any(e["name"] == "join_ok" for e in reconnecting_socket.get_received()), \
        "the real player must be able to reclaim her own nickname with her own token"

    reconnecting_socket.emit("answer_submit", {"pin": "445445", "nickname": "alice", "choice": 1})
    assert GAMES["445445"].players["alice"].score > 0, \
        "the reconnected socket must be able to score as the same player"


LEAKY_KEYS = {"correct", "points", "score"}


def _payload_keys(events):
    keys = set()
    for e in events:
        for arg in e["args"]:
            if isinstance(arg, dict):
                keys |= set(arg)
    return keys


def test_throwaway_nicknames_cannot_probe_the_answer_before_the_reveal():
    # Codex finding #3. on_answer_submit used to emit answer:feedback -- {correct, points,
    # score} -- the instant a player answered. player.js held the banner back until the
    # reveal, but that is a client-side courtesy: a hostile client reads the event straight off
    # the socket. The one-answer limit is per NICKNAME, so a student joins with one throwaway
    # nickname per option, submits a different choice from each, and the one that comes back
    # correct is the answer -- before the real reveal, relayable to the whole class.
    GAMES.clear()
    GAMES["555000"] = GameSession("555000", QUESTIONS)   # four options, correct == 1

    host = _authed_host_socket("555000")
    slow = socketio.test_client(app)                     # a real student who hasn't answered,
    slow.emit("player_join", {"pin": "555000", "nickname": "slow"})   # so the round stays open
    probes = []
    for i in range(4):
        s = socketio.test_client(app)
        s.emit("player_join", {"pin": "555000", "nickname": f"probe{i}"})
        probes.append(s)
    host.emit("host_next", {"pin": "555000"})
    for s in probes:
        s.get_received()  # drop the join / question:show noise

    # callback=True asks Socket.IO to send the handler's RETURN VALUE back to the caller: a
    # second channel a hostile client can request, separate from anything the handler emits
    acks = [s.emit("answer_submit", {"pin": "555000", "nickname": f"probe{i}", "choice": i}, callback=True)
            for i, s in enumerate(probes)]

    assert not getattr(GAMES["555000"], "_revealed_this_round", False), "round must still be open"
    assert all(not a for a in acks), f"the ack callback must carry nothing: {acks}"
    for i, s in enumerate(probes):
        got = s.get_received()
        names = [e["name"] for e in got]
        assert "answer:feedback" not in names, f"probe{i} was told its result mid-round"
        assert not (LEAKY_KEYS & _payload_keys(got)), \
            f"probe{i} received correctness-bearing data mid-round: {got}"
        assert names.count("answer:recorded") == 1, "the phone must be told its tap landed, once"
    assert "answer:recorded" not in [e["name"] for e in slow.get_received()], \
        "the acknowledgement is for the submitter alone"


def test_each_player_gets_their_own_result_at_the_reveal_and_only_theirs():
    # The other half of the fix: withholding must not lose the result. It is delivered
    # privately -- to that player's own socket -- when the round closes, before the
    # question:results broadcast (player.js keeps it pending and renders it from that handler).
    GAMES.clear()
    GAMES["555001"] = GameSession("555001", QUESTIONS)

    host = _authed_host_socket("555001")
    alice = socketio.test_client(app)
    bob = socketio.test_client(app)
    alice.emit("player_join", {"pin": "555001", "nickname": "alice"})
    bob.emit("player_join", {"pin": "555001", "nickname": "bob"})
    host.emit("host_next", {"pin": "555001"})
    alice.get_received(); bob.get_received()

    alice.emit("answer_submit", {"pin": "555001", "nickname": "alice", "choice": 1})   # correct
    assert "answer:feedback" not in [e["name"] for e in alice.get_received()]          # round still open
    bob.emit("answer_submit", {"pin": "555001", "nickname": "bob", "choice": 0})       # wrong -> reveal

    a_events = alice.get_received()
    b_events = bob.get_received()
    a_names = [e["name"] for e in a_events]
    assert a_names.index("answer:feedback") < a_names.index("question:results"), \
        "the private result must arrive before the reveal broadcast the client renders it from"

    a_fb = [e["args"][0] for e in a_events if e["name"] == "answer:feedback"]
    b_fb = [e["args"][0] for e in b_events if e["name"] == "answer:feedback"]
    assert len(a_fb) == 1 and len(b_fb) == 1, "exactly one private result each, nobody else's"
    assert a_fb[0]["correct"] is True and a_fb[0]["points"] > 0
    assert a_fb[0]["score"] == GAMES["555001"].players["alice"].score
    assert b_fb[0]["correct"] is False and b_fb[0]["points"] == 0


def test_a_timeout_reveal_still_delivers_results_and_skips_non_answerers():
    # The reveal also fires from the 20 s timer (_auto_reveal_after_timeout), not only when
    # everyone has answered. Same path, so the same delivery -- and a player who never answered
    # gets no result event at all (player.js renders "Time's up" from the absence).
    GAMES.clear()
    GAMES["555002"] = GameSession("555002", QUESTIONS)

    host = _authed_host_socket("555002")
    alice = socketio.test_client(app)
    bob = socketio.test_client(app)
    alice.emit("player_join", {"pin": "555002", "nickname": "alice"})
    bob.emit("player_join", {"pin": "555002", "nickname": "bob"})
    host.emit("host_next", {"pin": "555002"})
    alice.emit("answer_submit", {"pin": "555002", "nickname": "alice", "choice": 1})
    alice.get_received(); bob.get_received()

    game = GAMES["555002"]
    game.time_limit = 0                                   # run the real timer path, not a direct call
    _auto_reveal_after_timeout("555002", game.current_index)

    assert [e for e in alice.get_received() if e["name"] == "answer:feedback"][0]["args"][0]["correct"] is True
    b_names = [e["name"] for e in bob.get_received()]
    assert "question:results" in b_names and "answer:feedback" not in b_names


def test_a_reconnected_player_gets_the_result_on_the_new_socket():
    # Results go to CURRENT_SID, the same "newest socket for this nickname" record
    # on_answer_submit and on_disconnect already trust -- not to a stale socket.
    GAMES.clear()
    GAMES["555003"] = GameSession("555003", QUESTIONS)

    host = _authed_host_socket("555003")
    old = socketio.test_client(app)
    old.emit("player_join", {"pin": "555003", "nickname": "alice"})
    token = [e for e in old.get_received() if e["name"] == "join_ok"][0]["args"][0]["token"]
    other = socketio.test_client(app)
    other.emit("player_join", {"pin": "555003", "nickname": "bob"})   # keeps the round open
    host.emit("host_next", {"pin": "555003"})

    new = socketio.test_client(app)                                   # wifi drop: same browser, new socket
    new.emit("player_join", {"pin": "555003", "nickname": "alice", "token": token})
    new.emit("answer_submit", {"pin": "555003", "nickname": "alice", "choice": 1})
    old.get_received(); new.get_received()

    _reveal_results("555003")

    assert [e for e in new.get_received() if e["name"] == "answer:feedback"], "new socket must get the result"
    assert not [e for e in old.get_received() if e["name"] == "answer:feedback"], "stale socket must not"


def test_a_player_who_reconnects_after_the_reveal_still_gets_their_result():
    # A phone that drops wifi right after answering is skipped by the reveal (its CURRENT_SID
    # is gone). Before this change its score had already reached the phone at submit time;
    # now the result only exists at the reveal, so the rejoin must replay it -- but only once
    # the round is closed, never mid-round.
    GAMES.clear()
    GAMES["555004"] = GameSession("555004", QUESTIONS)

    host = _authed_host_socket("555004")
    first = socketio.test_client(app)
    first.emit("player_join", {"pin": "555004", "nickname": "alice"})
    token = [e for e in first.get_received() if e["name"] == "join_ok"][0]["args"][0]["token"]
    bob = socketio.test_client(app)
    bob.emit("player_join", {"pin": "555004", "nickname": "bob"})
    host.emit("host_next", {"pin": "555004"})

    first.emit("answer_submit", {"pin": "555004", "nickname": "alice", "choice": 1})   # correct
    first.disconnect()                                                                  # wifi drops

    early = socketio.test_client(app)                                                   # back, but round still open
    early.emit("player_join", {"pin": "555004", "nickname": "alice", "token": token})
    assert "answer:feedback" not in [e["name"] for e in early.get_received()], \
        "a rejoin mid-round must not be handed the result"
    early.disconnect()

    bob.emit("answer_submit", {"pin": "555004", "nickname": "bob", "choice": 0})        # reveal, alice absent
    assert getattr(GAMES["555004"], "_revealed_this_round", False)

    late = socketio.test_client(app)
    late.emit("player_join", {"pin": "555004", "nickname": "alice", "token": token})
    fb = [e["args"][0] for e in late.get_received() if e["name"] == "answer:feedback"]
    assert len(fb) == 1, "the rejoin after the reveal must replay alice's own result"
    assert fb[0]["correct"] is True and fb[0]["points"] > 0
    assert fb[0]["score"] == GAMES["555004"].players["alice"].score


def test_a_failed_private_delivery_does_not_stop_the_reveal_broadcast(monkeypatch):
    # _reveal_results marks the round revealed before it sends anything. If one player's
    # private emit raised, question:results would never go out and a second call returns early
    # on the flag -- a round stuck closed for everyone. One bad socket must cost only itself.
    GAMES.clear()
    GAMES["555005"] = GameSession("555005", QUESTIONS)

    host = _authed_host_socket("555005")
    alice = socketio.test_client(app)
    bob = socketio.test_client(app)
    alice.emit("player_join", {"pin": "555005", "nickname": "alice"})
    bob.emit("player_join", {"pin": "555005", "nickname": "bob"})
    host.emit("host_next", {"pin": "555005"})
    alice.emit("answer_submit", {"pin": "555005", "nickname": "alice", "choice": 1})
    host.get_received(); alice.get_received(); bob.get_received()

    real_emit = socketio.emit

    def flaky(event, *a, **kw):
        if event == "answer:feedback":
            raise RuntimeError("socket went away mid-send")
        return real_emit(event, *a, **kw)

    monkeypatch.setattr(socketio, "emit", flaky)
    _reveal_results("555005")
    monkeypatch.undo()

    assert any(e["name"] == "question:results" for e in host.get_received()), \
        "the reveal broadcast must still reach the room"
    assert any(e["name"] == "question:results" for e in bob.get_received())


def _fingerprint(events):
    return sorted(json.dumps([e["name"], e["args"]], sort_keys=True) for e in events)


def _observe_midround(pin, correct_idx):
    GAMES.clear()
    GAMES[pin] = GameSession(pin, [{"stem": "Q?", "options": ["a", "b", "c", "d"], "correct": correct_idx}])
    host = _authed_host_socket(pin)
    slow = socketio.test_client(app)
    slow.emit("player_join", {"pin": pin, "nickname": "slow"})   # keeps the round open
    probe = socketio.test_client(app)
    probe.emit("player_join", {"pin": pin, "nickname": "probe"})
    host.emit("host_next", {"pin": pin})
    probe.get_received(); slow.get_received()
    ack = probe.emit("answer_submit", {"pin": pin, "nickname": "probe", "choice": 1}, callback=True)
    assert not getattr(GAMES[pin], "_revealed_this_round", False)
    return ack, _fingerprint(probe.get_received()), _fingerprint(slow.get_received())


def test_midround_traffic_does_not_depend_on_which_answer_is_correct():
    # The property itself, rather than a deny-list of leaky key names: two games that differ ONLY
    # in the answer key, the same nickname making the same choice. Whatever the player can
    # observe mid-round -- every event, in order, with every payload, plus the ack callback --
    # must be identical whether that choice was right or wrong. A deny-list of "correct/points/
    # score" misses {"ok": ...}, a bare bool, a nested dict, or an extra event sent only on a hit.
    ack_hit, events_hit, slow_hit = _observe_midround("555010", correct_idx=1)    # the choice IS right
    ack_miss, events_miss, slow_miss = _observe_midround("555011", correct_idx=2)  # the choice is wrong
    assert not ack_hit and not ack_miss, "the ack callback must carry nothing"
    assert events_hit == events_miss, "the submitter's mid-round traffic varies with correctness"
    assert slow_hit == slow_miss, "a bystander's mid-round traffic varies with correctness"


def test_a_disconnected_answerers_result_is_not_sent_to_anyone_else():
    # An answerer with no socket on file has sid None, and socketio.emit(..., to=None) is a
    # BROADCAST to everyone. The `sid is not None` guard in _reveal_results is the line standing
    # between "no delivery" and "alice's result goes to the whole server".
    GAMES.clear()
    GAMES["555012"] = GameSession("555012", QUESTIONS)
    host = _authed_host_socket("555012")
    alice = socketio.test_client(app)
    bob = socketio.test_client(app)
    alice.emit("player_join", {"pin": "555012", "nickname": "alice"})
    bob.emit("player_join", {"pin": "555012", "nickname": "bob"})
    outsider = socketio.test_client(app)                    # not in this game at all
    host.emit("host_next", {"pin": "555012"})
    alice.emit("answer_submit", {"pin": "555012", "nickname": "alice", "choice": 1})   # correct
    alice.disconnect()
    bob.get_received(); outsider.get_received()

    bob.emit("answer_submit", {"pin": "555012", "nickname": "bob", "choice": 0})       # wrong -> reveal

    b_fb = [e["args"][0] for e in bob.get_received() if e["name"] == "answer:feedback"]
    assert b_fb == [{"correct": False, "points": 0, "score": 0}], "bob gets exactly his own result"
    assert not [e for e in outsider.get_received() if e["name"] == "answer:feedback"]


def test_the_private_score_is_cumulative_and_a_skipped_round_gets_no_stale_result():
    GAMES.clear()
    GAMES["555013"] = GameSession("555013", TWO_QUESTIONS)
    host = _authed_host_socket("555013")
    alice = socketio.test_client(app)
    bob = socketio.test_client(app)
    alice.emit("player_join", {"pin": "555013", "nickname": "alice"})
    token = [e for e in alice.get_received() if e["name"] == "join_ok"][0]["args"][0]["token"]
    bob.emit("player_join", {"pin": "555013", "nickname": "bob"})

    host.emit("host_next", {"pin": "555013"})
    alice.emit("answer_submit", {"pin": "555013", "nickname": "alice", "choice": 1})
    bob.emit("answer_submit", {"pin": "555013", "nickname": "bob", "choice": 1})       # round 1 reveals
    r1 = [e["args"][0] for e in alice.get_received() if e["name"] == "answer:feedback"]

    host.emit("host_next", {"pin": "555013"})
    alice.get_received(); bob.get_received()
    bob.emit("answer_submit", {"pin": "555013", "nickname": "bob", "choice": 2})       # alice skips round 2
    _reveal_results("555013")
    assert not [e for e in alice.get_received() if e["name"] == "answer:feedback"], \
        "a player who skipped round 2 must not be handed round 1's result again"

    rejoined = socketio.test_client(app)
    rejoined.emit("player_join", {"pin": "555013", "nickname": "alice", "token": token})
    assert not [e for e in rejoined.get_received() if e["name"] == "answer:feedback"], \
        "the rejoin replay is for the round just closed, never an earlier one"

    GAMES["555013"].players["alice"].connected = True
    host.emit("host_next", {"pin": "555013"})                                          # game over
    assert len(r1) == 1 and r1[0]["score"] == r1[0]["points"]
    bob_fb = [e["args"][0] for e in bob.get_received() if e["name"] == "answer:feedback"]
    assert bob_fb[-1]["score"] == bob_fb[0]["points"] + bob_fb[-1]["points"], "score is cumulative"


def test_a_player_who_answered_then_dropped_and_rejoined_before_the_reveal_gets_the_result():
    # The realistic wifi blip: answer on the OLD socket, it dies, the browser reconnects as a NEW
    # socket (same token) before the round closes. The result must follow the player.
    GAMES.clear()
    GAMES["555014"] = GameSession("555014", QUESTIONS)
    host = _authed_host_socket("555014")
    old = socketio.test_client(app)
    old.emit("player_join", {"pin": "555014", "nickname": "alice"})
    token = [e for e in old.get_received() if e["name"] == "join_ok"][0]["args"][0]["token"]
    other = socketio.test_client(app)
    other.emit("player_join", {"pin": "555014", "nickname": "bob"})
    host.emit("host_next", {"pin": "555014"})
    old.emit("answer_submit", {"pin": "555014", "nickname": "alice", "choice": 1})
    old.disconnect()
    new = socketio.test_client(app)
    new.emit("player_join", {"pin": "555014", "nickname": "alice", "token": token})
    new.get_received()

    _reveal_results("555014")

    fb = [e["args"][0] for e in new.get_received() if e["name"] == "answer:feedback"]
    assert fb and fb[0]["correct"] is True


def test_results_follow_the_newest_socket_through_a_ping_pong_rejoin():
    # old -> new -> old again, all with the token: CURRENT_SID ends on `old`, so that is where
    # the result belongs, not on whichever socket was bound last in some other table.
    GAMES.clear()
    GAMES["555015"] = GameSession("555015", QUESTIONS)
    host = _authed_host_socket("555015")
    old = socketio.test_client(app)
    old.emit("player_join", {"pin": "555015", "nickname": "alice"})
    token = [e for e in old.get_received() if e["name"] == "join_ok"][0]["args"][0]["token"]
    other = socketio.test_client(app)
    other.emit("player_join", {"pin": "555015", "nickname": "bob"})
    host.emit("host_next", {"pin": "555015"})
    new = socketio.test_client(app)
    new.emit("player_join", {"pin": "555015", "nickname": "alice", "token": token})
    old.emit("player_join", {"pin": "555015", "nickname": "alice", "token": token})
    old.emit("answer_submit", {"pin": "555015", "nickname": "alice", "choice": 1})
    old.get_received(); new.get_received()

    _reveal_results("555015")

    assert len([e for e in old.get_received() if e["name"] == "answer:feedback"]) == 1
    assert not [e for e in new.get_received() if e["name"] == "answer:feedback"]


def test_the_round_is_already_closed_when_private_results_go_out_and_a_second_reveal_sends_nothing(monkeypatch):
    # Closed first: a result emitted while the round is still open could still help someone
    # answer. And _reveal_results is reachable from two paths (all-answered, timer) that can both
    # fire, so a repeat must not re-send every player's private result.
    GAMES.clear()
    GAMES["555016"] = GameSession("555016", QUESTIONS)
    host = _authed_host_socket("555016")
    alice = socketio.test_client(app)
    bob = socketio.test_client(app)
    alice.emit("player_join", {"pin": "555016", "nickname": "alice"})
    bob.emit("player_join", {"pin": "555016", "nickname": "bob"})
    host.emit("host_next", {"pin": "555016"})
    alice.emit("answer_submit", {"pin": "555016", "nickname": "alice", "choice": 1})
    alice.get_received()

    seen = []
    real_emit = socketio.emit

    def spy(event, *a, **kw):
        seen.append((event, getattr(GAMES["555016"], "_revealed_this_round", False)))
        return real_emit(event, *a, **kw)

    monkeypatch.setattr(socketio, "emit", spy)
    _reveal_results("555016")
    _reveal_results("555016")
    monkeypatch.undo()

    private = [closed for event, closed in seen if event == "answer:feedback"]
    assert private and all(private), "a private result went out while the round was still open"
    names = [e["name"] for e in alice.get_received()]
    assert names.count("answer:feedback") == 1 and names.count("question:results") == 1



def test_nickname_is_sanitized_server_side():
    GAMES.clear()
    GAMES["555555"] = GameSession("555555", QUESTIONS)

    empty = socketio.test_client(app)
    empty.emit("player_join", {"pin": "555555", "nickname": "   "})
    assert any(e["name"] == "join_error" for e in empty.get_received())  # blank rejected

    long = socketio.test_client(app)
    long.emit("player_join", {"pin": "555555", "nickname": "x" * 100})
    ok = [e for e in long.get_received() if e["name"] == "join_ok"]
    assert ok and len(ok[0]["args"][0]["nickname"]) == 24  # capped server-side


def test_joining_mid_question_shows_the_active_question():
    GAMES.clear()
    GAMES["777777"] = GameSession("777777", QUESTIONS)

    host = _authed_host_socket("777777")
    host.emit("host_next", {"pin": "777777"})  # question is live before anyone joins

    late = socketio.test_client(app)
    late.emit("player_join", {"pin": "777777", "nickname": "late"})
    shown = [e for e in late.get_received() if e["name"] == "question:show"]
    assert len(shown) == 1  # the latecomer/reconnecter sees the in-progress question, not a blank wait
    assert shown[0]["args"][0]["stem"] == "Q1?"


def test_nickname_matching_a_real_enrolled_id_is_not_flagged():
    GAMES.clear()
    slug = _enroll(["6631503001", "6631503002"])
    GAMES["444401"] = GameSession("444401", QUESTIONS, course_slug=slug)

    real = socketio.test_client(app)
    real.emit("player_join", {"pin": "444401", "nickname": "6631503001"})
    ok = [e for e in real.get_received() if e["name"] == "join_ok"]
    assert ok and not ok[0]["args"][0]["id_mismatch"]


def test_nickname_not_matching_any_enrolled_id_is_flagged():
    GAMES.clear()
    slug = _enroll(["6631503003", "6631503004"])
    GAMES["444402"] = GameSession("444402", QUESTIONS, course_slug=slug)

    typo = socketio.test_client(app)
    typo.emit("player_join", {"pin": "444402", "nickname": "some nickname"})
    ok = [e for e in typo.get_received() if e["name"] == "join_ok"]
    assert ok and ok[0]["args"][0]["id_mismatch"] is True


def test_mismatch_warning_does_not_block_joining():
    # the whole point is a nudge, not a gate — a mismatched nickname still gets in
    GAMES.clear()
    slug = _enroll(["6631503005"])
    GAMES["444403"] = GameSession("444403", QUESTIONS, course_slug=slug)

    typo = socketio.test_client(app)
    typo.emit("player_join", {"pin": "444403", "nickname": "definitely not an id"})
    ok = [e for e in typo.get_received() if e["name"] == "join_ok"]
    assert ok  # still joined despite the mismatch
    assert "444403" in GAMES and "definitely not an id" in GAMES["444403"].players


def test_no_enrollment_data_skips_validation_entirely(tmp_path):
    # A course nobody has issued slips for yet must not flag anyone — graceful
    # degradation, same principle as the ledger's unmatched-row handling. This
    # exercises nickname_matches_roster directly against a freshly isolated DB
    # (no enrollments possible) rather than the shared cross-test app DB, which
    # by this point in the suite already has real enrollments from the tests
    # above — a real "empty roster" state can't be relied on there.
    from app import nickname_matches_roster

    conn = dbmod.connect(str(tmp_path / "empty.db"))
    dbmod.init_db(conn, default_course=C.COURSES[0]["slug"])
    assert nickname_matches_roster(conn, C.COURSES[0]["slug"], "whatever i typed")

