"""Live typing metrics: accuracy, WPM, streak, rhythm signals for Soft observe."""

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
    # Inter-key intervals (ms) for rhythm observe
    intervals_ms: list[float] = field(default_factory=list)
    _last_key_at: float | None = None

    def record_key(self, ok: bool) -> None:
        now = time.monotonic()
        if self._last_key_at is not None:
            self.intervals_ms.append((now - self._last_key_at) * 1000.0)
            # keep a rolling window
            if len(self.intervals_ms) > 64:
                self.intervals_ms = self.intervals_ms[-64:]
        self._last_key_at = now
        self.chars_done += 1
        if ok:
            self.correct += 1
            self.streak += 1
            self.best_streak = max(self.best_streak, self.streak)
        else:
            self.wrong += 1
            self.streak = 0

    @property
    def accuracy(self) -> float:
        total = self.correct + self.wrong
        if total == 0:
            return 1.0
        return self.correct / total

    @property
    def elapsed_min(self) -> float:
        # floor at 3s so brand-new sessions do not show absurd WPM
        secs = max(time.monotonic() - self.started_at, 3.0)
        return secs / 60.0

    @property
    def wpm(self) -> float:
        # standard: 5 chars ≈ 1 word
        return (self.correct / 5.0) / self.elapsed_min

    def rhythm_cv(self) -> float:
        """Coefficient of variation of inter-key intervals (lower = steadier)."""
        xs = self.intervals_ms
        if len(xs) < 3:
            return 0.0
        mean = sum(xs) / len(xs)
        if mean <= 0:
            return 0.0
        var = sum((x - mean) ** 2 for x in xs) / len(xs)
        return (var**0.5) / mean

    def observe_signals(self) -> dict:
        """Signals Soft will observe later via documented sockets."""
        return {
            "accuracy": round(self.accuracy, 4),
            "wpm": round(self.wpm, 2),
            "streak": self.streak,
            "best_streak": self.best_streak,
            "chars_done": self.chars_done,
            "wrong": self.wrong,
            "rhythm_cv": round(self.rhythm_cv(), 4),
        }
