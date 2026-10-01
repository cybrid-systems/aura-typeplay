"""Cute bilingual micro-feedback (EN + 中文) — offline rule library.

Soft/MiniMax may propose richer copy asynchronously; this is the instant
kid-safe reaction layer (thin host, no Soft language hacks).
"""

from __future__ import annotations

import random
from dataclasses import dataclass


@dataclass(frozen=True)
class MicroFeedback:
    emoji: str
    en: str
    zh: str
    burst: str = "gentle"  # gentle | sparkle | party | soft | oops


OK = (
    MicroFeedback("✨", "Nice!", "真棒！", "sparkle"),
    MicroFeedback("🌟", "Yes!", "对啦！", "sparkle"),
    MicroFeedback("💖", "Lovely", "真好", "gentle"),
    MicroFeedback("🌈", "Rainbow!", "彩虹！", "sparkle"),
    MicroFeedback("🐰", "Hop!", "跳跳！", "gentle"),
)

STREAK = (
    MicroFeedback("🔥", "Streak!", "连击！", "sparkle"),
    MicroFeedback("🎉", "Wow streak!", "好厉害！", "party"),
    MicroFeedback("🦄", "Unicorn mode!", "独角兽模式！", "party"),
    MicroFeedback("🚀", "Zoom!", "飞起来！", "party"),
    MicroFeedback("🏆", "Champion fingers!", "手指冠军！", "party"),
)

OOPS = (
    MicroFeedback("☁️", "Soft try", "没关系，再试", "oops"),
    MicroFeedback("🌱", "Grow again", "再长大一点", "soft"),
    MicroFeedback("🤗", "Hugs — retry", "抱抱，再来", "oops"),
    MicroFeedback("🫧", "Bubble calm", "泡泡慢慢来", "soft"),
)

LINE_DONE = (
    MicroFeedback("🎵", "Line done!", "打完一行啦！", "sparkle"),
    MicroFeedback("🌸", "Pretty line!", "漂亮的一行！", "gentle"),
    MicroFeedback("⭐", "Star line!", "星星一行！", "sparkle"),
)

LEVEL_UP = (
    MicroFeedback("🏰", "New level!", "升级啦！", "party"),
    MicroFeedback("🎁", "Gift unlocked!", "礼物解锁！", "party"),
)


def for_key(ok: bool, streak: int) -> MicroFeedback:
    if not ok:
        return random.choice(OOPS)
    if streak >= 8 and streak % 4 == 0:
        return random.choice(STREAK)
    if streak >= 5 and streak % 5 == 0:
        return random.choice(STREAK)
    return random.choice(OK)


def for_line_done() -> MicroFeedback:
    return random.choice(LINE_DONE)


def for_level_up() -> MicroFeedback:
    return random.choice(LEVEL_UP)


def big_glyphs(text: str, typed_len: int, last_ok: bool | None, scale: float = 1.0) -> str:
    """Render target with spaced big-friendly glyphs (Textual markup)."""
    parts: list[str] = []
    gap = " " if scale >= 1.2 else ""
    for i, ch in enumerate(text):
        show = ch if ch != " " else "·"
        if i < typed_len:
            if last_ok is False and i == typed_len - 1:
                parts.append(f"[bold red on #331111]{show}[/]")
            else:
                parts.append(f"[bold green on #113311]{show}[/]")
        elif i == typed_len:
            parts.append(f"[bold yellow on #333300 blink]{show}[/]")
        else:
            parts.append(f"[bold white]{show}[/]")
    return gap.join(parts)
