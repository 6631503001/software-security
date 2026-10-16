import os
import sys
import time

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from game import GameSession, generate_pin

QUESTIONS = [
    {"stem": "Q1?", "options": ["a", "b", "c", "d"], "correct": 1},
    {"stem": "Q2?", "options": ["a", "b", "c", "d"], "correct": 2},
]


def test_generate_pin_is_six_digits():
    pin = generate_pin()
    assert len(pin) == 6
    assert pin.isdigit()


def test_join_creates_a_new_player_with_zero_score():
    game = GameSession("123456", QUESTIONS)
    player = game.join("alice")
    assert player.nickname == "alice"
    assert player.score == 0


def test_course_slug_defaults_to_none():
    game = GameSession("123456", QUESTIONS)
    assert game.course_slug is None


def test_course_slug_is_stored_when_given():
    game = GameSession("123456", QUESTIONS, course_slug="software-security")
    assert game.course_slug == "software-security"


def test_rejoin_with_the_right_token_resumes_existing_score():
    game = GameSession("123456", QUESTIONS)
    alice = game.join("alice")  # first join: no token to prove, always allowed
    game.next_question()
    game.submit_answer("alice", 1)  # correct, Q1
    score_before = alice.score
    assert score_before > 0

    # simulate reconnect: same person, proves it with the token issued at first join
    rejoined = game.join("alice", token=alice.token)
    assert rejoined is alice
    assert rejoined.score == score_before  # NOT reset to zero


def test_rejoin_with_no_token_is_refused_not_silently_granted():
    # The actual exploit Codex's security review flagged: nicknames are shown
    # in the lobby to everyone (see _broadcast_lobby in app.py), and join()
    # used to hand back the SAME player to anyone who repeated an in-use
    # nickname -- no secret required. A classmate who saw "alice" in the
    # lobby could claim her identity and both tamper with her score and
    # block her from scoring herself (see the socketio-level reproduction in
    # test_app_socketio.py for the end-to-end version). Reclaiming an
    # existing nickname must prove it with that player's own token.
    game = GameSession("123456", QUESTIONS)
    game.join("alice")
    try:
        game.join("alice")  # no token at all
        assert False, "expected PermissionError"
    except PermissionError:
        pass
    try:
        game.join("alice", token="not-the-real-token")
        assert False, "expected PermissionError"
    except PermissionError:
        pass


def test_next_question_advances_index_and_returns_question():
    game = GameSession("123456", QUESTIONS)
    q = game.next_question()
    assert q == QUESTIONS[0]
    assert game.current_index == 0


def test_next_question_past_the_end_marks_finished():
    game = GameSession("123456", QUESTIONS)
    game.next_question()
    game.next_question()
    result = game.next_question()
    assert result is None
    assert game.finished is True


def test_submit_answer_scores_correct_answer():
    game = GameSession("123456", QUESTIONS)
    game.join("alice")
    game.next_question()
    result = game.submit_answer("alice", 1)  # correct (index 1)
    assert result["correct"] is True
    assert result["points"] > 0
    assert game.players["alice"].score == result["points"]


def test_submit_answer_scores_wrong_answer_as_zero():
    game = GameSession("123456", QUESTIONS)
    game.join("alice")
    game.next_question()
    result = game.submit_answer("alice", 0)  # wrong
    assert result["correct"] is False
    assert result["points"] == 0
    assert game.players["alice"].score == 0


def test_submit_answer_twice_in_same_round_ignores_second_submission():
    game = GameSession("123456", QUESTIONS)
    game.join("alice")
    game.next_question()
    first = game.submit_answer("alice", 1)
    second = game.submit_answer("alice", 0)  # try to change the answer
    assert second is None
    assert game.players["alice"].score == first["points"]  # unchanged


def test_round_results_keep_each_players_result_until_the_next_round():
    # app.py withholds a player's result until the round is revealed, so the model has to
    # remember it: submit_answer's return value is consumed at submit time and thrown away.
    game = GameSession("123456", QUESTIONS)
    game.join("alice")
    game.join("bob")
    game.next_question()
    first = game.submit_answer("alice", 1)                        # correct
    game.submit_answer("bob", 0)                                  # wrong
    game.submit_answer("alice", 0)                                # ignored duplicate: must not overwrite
    assert game.round_results["alice"] == first
    assert game.round_results["bob"] == {"correct": False, "points": 0}
    game.next_question()
    assert game.round_results == {}                               # a fresh round starts empty


def test_submit_answer_for_unknown_player_raises():
    game = GameSession("123456", QUESTIONS)
    game.next_question()
    try:
        game.submit_answer("ghost", 0)
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_submit_answer_rejects_non_integer_choice():
    # A malformed choice_index must never reach answers_this_round: it would
    # otherwise survive silently (choice_index == q["correct"] just compares
    # False, no crash yet) until answer_distribution() later does
    # `0 <= choice_index < len(counts)`, which raises TypeError for anything
    # that isn't an int — and that call happens AFTER the round is already
    # marked revealed (see app.py's _reveal_results), permanently breaking
    # that round for the whole class.
    game = GameSession("123456", QUESTIONS)
    game.join("alice")
    game.next_question()
    for bad in (None, "1", [1], {"choice": 1}, 3.5):
        try:
            game.submit_answer("alice", bad)
            assert False, f"expected ValueError for choice_index={bad!r}"
        except ValueError:
            pass
    assert "alice" not in game.answers_this_round


def test_submit_answer_rejects_out_of_range_choice():
    game = GameSession("123456", QUESTIONS)
    game.join("alice")
    game.next_question()
    try:
        game.submit_answer("alice", len(QUESTIONS[0]["options"]))  # one past the end
        assert False, "expected ValueError"
    except ValueError:
        pass
    try:
        game.submit_answer("alice", -1)
        assert False, "expected ValueError"
    except ValueError:
        pass


def test_answer_distribution_survives_a_rejected_submission():
    # Regression for the actual crash: even though submit_answer() now
    # rejects bad input, answer_distribution() itself must not assume every
    # stored entry is valid — belt-and-suspenders against any other path
    # that might populate answers_this_round.
    game = GameSession("123456", QUESTIONS)
    game.join("alice")
    game.next_question()
    game.answers_this_round["alice"] = (None, 1.0)  # simulate corrupted state directly
    counts = game.answer_distribution()
    assert counts == [0] * len(QUESTIONS[0]["options"])


def test_all_answered_true_only_when_every_connected_player_has_answered():
    game = GameSession("123456", QUESTIONS)
    game.join("alice")
    game.join("bob")
    game.next_question()
    assert game.all_answered() is False
    game.submit_answer("alice", 1)
    assert game.all_answered() is False
    game.submit_answer("bob", 0)
    assert game.all_answered() is True


def test_disconnected_player_excluded_from_all_answered():
    game = GameSession("123456", QUESTIONS)
    game.join("alice")
    game.join("bob")
    game.disconnect("bob")
    game.next_question()
    game.submit_answer("alice", 1)
    assert game.all_answered() is True  # bob is disconnected, doesn't block


def test_answer_distribution_counts_choices():
    game = GameSession("123456", QUESTIONS)
    game.join("alice")
    game.join("bob")
    game.join("carol")
    game.next_question()
    game.submit_answer("alice", 1)
    game.submit_answer("bob", 1)
    game.submit_answer("carol", 0)
    assert game.answer_distribution() == [1, 2, 0, 0]


def test_leaderboard_sorted_descending_by_score():
    game = GameSession("123456", QUESTIONS)
    game.join("alice")
    game.join("bob")
    game.next_question()
    game.submit_answer("alice", 1)  # correct, scores > 0
    game.submit_answer("bob", 0)  # wrong, scores 0
    board = game.leaderboard()
    assert board[0]["nickname"] == "alice"
    assert board[1]["nickname"] == "bob"


def test_rank_of_returns_one_based_position():
    game = GameSession("123456", QUESTIONS)
    game.join("alice")
    game.join("bob")
    game.next_question()
    game.submit_answer("alice", 1)
    game.submit_answer("bob", 0)
    assert game.rank_of("alice") == 1
    assert game.rank_of("bob") == 2


def test_export_results_shape():
    game = GameSession("123456", QUESTIONS)
    game.join("alice")
    game.next_question()
    game.submit_answer("alice", 1)
    rows = game.export_results()
    assert len(rows) == 1
    row = rows[0]
    assert row["nickname"] == "alice"
    assert row["correct_count"] == 1
    assert row["total_score"] > 0
    assert row["avg_response_time_ms"] >= 0
    assert row["roster_match"] == ""          # no roster handed in: nothing was checked


def test_export_marks_which_nicknames_are_on_the_roster():
    game = GameSession("123456", QUESTIONS)
    game.join("6631503001")
    game.join("someone else")
    rows = {r["nickname"]: r["roster_match"] for r in game.export_results(enrolled_ids={"6631503001"})}
    assert rows == {"6631503001": "yes", "someone else": "no"}


def test_export_neutralizes_csv_formula_injection():
    game = GameSession("123456", [])
    for nick in ("=HYPERLINK(1)", "+1", "@x", "safe"):
        game.join(nick)
    by_nick = {r["nickname"].lstrip("'"): r["nickname"] for r in game.export_results()}
    # formula-triggering prefixes are quoted; an ordinary nickname is left alone
    assert by_nick["=HYPERLINK(1)"].startswith("'=")
    assert by_nick["+1"] == "'+1"
    assert by_nick["@x"] == "'@x"
    assert by_nick["safe"] == "safe"
