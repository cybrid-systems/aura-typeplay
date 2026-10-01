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
    MicroFeedback("☁️", "Oops — try THIS key", "按错啦，看黄色大字", "oops"),
    MicroFeedback("🌱", "Almost! Look ↑", "快了！看上面闪的字", "soft"),
    MicroFeedback("🤗", "Hugs — press the yellow one", "抱抱，按下黄色那个", "oops"),
    MicroFeedback("🫧", "Soft — wait for the blink", "慢慢来，看闪烁的字母", "soft"),
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

BACKSPACE_FB = MicroFeedback("↩️", "Back one", "退一格", "soft")


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


def for_waiting(expected: str) -> MicroFeedback:
    show = "空格" if expected == " " else expected
    return MicroFeedback(
        "👆",
        f"Press [{show}]",
        f"请按 【{show}】",
        "oops",
    )


def big_glyphs(
    text: str,
    typed_len: int,
    last_ok: bool | None,
    scale: float = 1.0,
    *,
    waiting_correct: bool = False,
) -> str:
    """Render target with spaced big-friendly glyphs (Textual markup).

    When waiting_correct (after a wrong key), flash the expected glyph huge.
    """
    parts: list[str] = []
    gap = "  " if scale >= 1.2 or waiting_correct else " "
    for i, ch in enumerate(text):
        show = "␣" if ch == " " else ch
        if i < typed_len:
            parts.append(f"[bold green on #113311]{show}[/]")
        elif i == typed_len:
            if waiting_correct:
                # Huge cue — never freeze without telling kids what to press
                parts.append(
                    f"[bold white on #aa2200 blink]>>> {show} <<<[/]"
                )
            else:
                parts.append(f"[bold yellow on #333300 blink]{show}[/]")
        else:
            parts.append(f"[bold #888]{show}[/]")
    hint = ""
    if waiting_correct and typed_len < len(text):
        exp = text[typed_len]
        label = "空格 Space" if exp == " " else exp
        hint = f"\n  [bold #ff8866]👉 下一个字母 Next:[/] [bold white on #aa2200] {label} [/]"
    return gap.join(parts) + hint
