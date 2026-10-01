"""Live typing metrics: accuracy, WPM, streak, rhythm, input patterns for Soft."""

from __future__ import annotations

import time
from dataclasses import dataclass, field


@dataclass
class SessionScore:
    correct: int = 0
    wrong: int = 0
    streak: int = 0
    best_streak: int = 0
    chars_done: int = 0
    started_at: float = field(default_factory=time.monotonic)
    intervals_ms: list[float] = field(default_factory=list)
    recent_ok: list[bool] = field(default_factory=list)  # last 24 keys
    _last_key_at: float | None = None

    def record_key(self, ok: bool) -> None:
        now = time.monotonic()
        if self._last_key_at is not None:
            self.intervals_ms.append((now - self._last_key_at) * 1000.0)
            if len(self.intervals_ms) > 64:
                self.intervals_ms = self.intervals_ms[-64:]
        self._last_key_at = now
        self.chars_done += 1
        self.recent_ok.append(ok)
        if len(self.recent_ok) > 24:
            self.recent_ok = self.recent_ok[-24:]
        if ok:
            self.correct += 1
            self.streak += 1
            self.best_streak = max(self.best_streak, self.streak)
        else:
            self.wrong += 1
            self.streak = 0

    def undo_correct(self) -> None:
        """Backspace: gently undo one prior correct key (streak trimmed)."""
        if self.correct > 0:
            self.correct -= 1
        if self.chars_done > 0:
            self.chars_done -= 1
        if self.streak > 0:
            self.streak -= 1
        if self.recent_ok and self.recent_ok[-1] is True:
            self.recent_ok.pop()

    @property
    def accuracy(self) -> float:
        total = self.correct + self.wrong
        if total == 0:
            return 1.0
        return self.correct / total

    @property
    def elapsed_min(self) -> float:
        secs = max(time.monotonic() - self.started_at, 3.0)
        return secs / 60.0

    @property
    def wpm(self) -> float:
        return (self.correct / 5.0) / self.elapsed_min

    def rhythm_cv(self) -> float:
        xs = self.intervals_ms
        if len(xs) < 3:
            return 0.0
        mean = sum(xs) / len(xs)
        if mean <= 0:
            return 0.0
        var = sum((x - mean) ** 2 for x in xs) / len(xs)
        return (var**0.5) / mean

    def recent_accuracy(self) -> float:
        if not self.recent_ok:
            return 1.0
        return sum(1 for x in self.recent_ok if x) / len(self.recent_ok)

    def burstiness(self) -> float:
        """High when mixed fast+slow intervals (input pattern irregularity)."""
        xs = self.intervals_ms[-16:]
        if len(xs) < 4:
            return 0.0
        lo, hi = min(xs), max(xs)
        if hi <= 0:
            return 0.0
        return min(1.0, (hi - lo) / hi)

    def observe_signals(self) -> dict:
        return {
            "accuracy": round(self.accuracy, 4),
            "wpm": round(self.wpm, 2),
            "streak": self.streak,
            "best_streak": self.best_streak,
            "chars_done": self.chars_done,
            "wrong": self.wrong,
            "rhythm_cv": round(self.rhythm_cv(), 4),
            "recent_accuracy": round(self.recent_accuracy(), 4),
            "burstiness": round(self.burstiness(), 4),
        }
