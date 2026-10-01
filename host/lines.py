"""Kid-friendly typing lines (English + simple phrases)."""

from __future__ import annotations

LINES: list[str] = [
    "the cat sat on the mat",
    "birds fly high in the sky",
    "i love to type and play",
    "soft colors make me smile",
    "red blue green and gold",
    "a happy dog runs fast",
    "we learn with every key",
    "stars shine in the night",
    "hello friend how are you",
    "practice makes fingers strong",
    "rain falls soft on leaves",
    "moon and sun take turns",
    "be kind and type with care",
    "music helps my fingers dance",
    "a brave fox jumps over",
]

def next_line(index: int) -> str:
    return LINES[index % len(LINES)]
