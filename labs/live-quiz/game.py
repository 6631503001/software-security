# game.py
"""In-memory game state for one live-quiz session. No database: a game is short-lived
(one class period) and this project's expected scale (dozens-to-~200 concurrent players)
doesn't need persistence beyond the end-of-game CSV export (see export_results)."""
import hmac
import random
import secrets
import string
import time

from scoring import score_answer

TIME_LIMIT = 20  # seconds per question; matches make_kahoot_import.py's TIME_LIMIT constant


def generate_pin():
    return "".join(random.choices(string.digits, k=6))


class Player:
    def __init__(self, nickname):
        self.nickname = nickname
        self.score = 0
        self.correct_count = 0
        self.response_times_ms = []
        self.connected = True
        # Proves which caller may act as this nickname again. Nicknames are
        # plaintext and broadcast to the whole lobby (_broadcast_lobby in
        # app.py), so without this, anyone who simply saw "alice" there could
        # call join("alice") themselves and take over her scoring — see
        # GameSession.join's docstring.
        self.token = secrets.token_urlsafe(16)


class GameSession:
    def __init__(self, pin, questions, time_limit=TIME_LIMIT, course_slug=None):
        self.pin = pin
        self.questions = questions
        self.time_limit = time_limit
        self.course_slug = course_slug
        self.current_index = -1
        self.players = {}
        self.question_start_time = None
        self.answers_this_round = {}
        # nickname -> {"correct", "points"} for the current round. Kept so the server can hand
        # each player their own result when the round closes; see submit_answer.
        self.round_results = {}
        self.finished = False

    def join(self, nickname, token=None):
        """Create a new player, or reclaim an EXISTING one if `token` matches
        that player's own reconnect token (issued as `player.token` on their
        first join). A dropped wifi connection or a backgrounded phone tab
        must still let the real student rejoin — that is what `token` is
        for — but reclaiming an in-use nickname WITHOUT it is refused:
        raises PermissionError. Without this, a classmate who merely saw the
        nickname in the lobby could call join() themselves and take over
        scoring for it (the caller, app.py's on_player_join, turns this into
        a plain join_error rather than a 500).
        """
        existing = self.players.get(nickname)
        if existing is None:
            player = Player(nickname)
            self.players[nickname] = player
            return player
        if token and hmac.compare_digest(str(token).encode(), existing.token.encode()):
            existing.connected = True
            return existing
        raise PermissionError(f"nickname already in use: {nickname}")

    def disconnect(self, nickname):
        if nickname in self.players:
            self.players[nickname].connected = False

    def current_question(self):
        if 0 <= self.current_index < len(self.questions):
            return self.questions[self.current_index]
        return None

    def next_question(self):
        self.current_index += 1
        self.answers_this_round = {}
        self.round_results = {}
        self.question_start_time = time.time()
        self._revealed_this_round = False
        if self.current_index >= len(self.questions):
            self.finished = True
            return None
        return self.current_question()

    def submit_answer(self, nickname, choice_index):
        """Record and score one answer. The returned {"correct", "points"} is for the SERVER
        layer only: it must not reach the answering player until the round is revealed.
        Whether a choice is right is exactly what the other nicknames in the room are trying
        to learn, and the one-answer limit is per nickname, so a student with N throwaway
        nicknames can probe N options and read the key off the first "correct" (see
        on_answer_submit / _reveal_results in app.py, which hold it until the round closes)."""
        if nickname not in self.players:
            raise ValueError(f"unknown player: {nickname}")
        if nickname in self.answers_this_round:
            return None
        q = self.current_question()
        if q is None:
            raise ValueError("no active question")
        # isinstance(x, int) also accepts bool (True/False), but that's harmless here —
        # it just resolves to a valid-or-invalid index like any other int would.
        if not isinstance(choice_index, int) or not (0 <= choice_index < len(q["options"])):
            raise ValueError(f"invalid choice_index: {choice_index!r}")
        time_taken = time.time() - self.question_start_time
        correct = choice_index == q["correct"]
        points = score_answer(correct, time_taken, self.time_limit)
        self.answers_this_round[nickname] = (choice_index, time_taken)
        player = self.players[nickname]
        player.score += points
        if correct:
            player.correct_count += 1
        player.response_times_ms.append(time_taken * 1000)
        result = {"correct": correct, "points": points}
        self.round_results[nickname] = result
        return result

    def all_answered(self):
        connected = [n for n, p in self.players.items() if p.connected]
        return len(connected) > 0 and all(n in self.answers_this_round for n in connected)

    def answer_distribution(self):
        q = self.current_question()
        counts = [0] * len(q["options"])
        for choice_index, _ in self.answers_this_round.values():
            if isinstance(choice_index, int) and 0 <= choice_index < len(counts):
                counts[choice_index] += 1
        return counts

    def leaderboard(self, top_n=5):
        ranked = sorted(self.players.values(), key=lambda p: -p.score)
        return [{"nickname": p.nickname, "score": p.score} for p in ranked[:top_n]]

    def rank_of(self, nickname):
        ranked = sorted(self.players.values(), key=lambda p: -p.score)
        for i, p in enumerate(ranked):
            if p.nickname == nickname:
                return i + 1
        return None

    def export_results(self):
        rows = []
        for p in self.players.values():
            avg_ms = sum(p.response_times_ms) / len(p.response_times_ms) if p.response_times_ms else 0
            rows.append(
                {
                    "nickname": _csv_safe(p.nickname),
                    "total_score": p.score,
                    "correct_count": p.correct_count,
                    "avg_response_time_ms": round(avg_ms),
                }
            )
        return rows


def _csv_safe(value):
    """Neutralize spreadsheet formula injection (CWE-1236): a nickname starting with =, +, -, @
    (or a control prefix) would run as a formula when the exported CSV is opened directly in
    Excel/Sheets. Prefixing a single quote makes the cell render as literal text."""
    if value[:1] in ("=", "+", "-", "@", "\t", "\r"):
        return "'" + value
    return value
