#!/usr/bin/env python3
"""Smoke MiniMax copy propose (filter + optional live). Soft owns id/hue/energy."""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from host.minimax_scene import (  # noqa: E402
    apply_copy,
    continuous_enrich,
    has_api_key,
    kid_safe_copy,
    kid_safe_hit,
    select_copy,
)
from host.scenes import SCENES  # noqa: E402


def main() -> int:
    assert kid_safe_copy("Sunny Meadow Friends")
    assert kid_safe_copy("warm sunlight on flowers")  # war⊂warm must NOT block
    assert kid_safe_hit("warm") is None
    assert kid_safe_hit("war zone") == "war"
    assert not kid_safe_copy("scary monster battle")
    bad, why = select_copy({"title": "kill zone", "art": "boom"})
    assert bad is None and "filter" in why
    safe, why2 = select_copy(
        {"title": "Happy Meadow", "blurb": "flowers smile", "art": "  🌻\n bunny"},
        scene=SCENES["meadow"],
    )
    assert safe and safe["title"] == "Happy Meadow" and why2 == ""
    base = SCENES["meadow"]
    merged = apply_copy(base, safe)
    assert merged.id == "meadow" and merged.hue == base.hue and merged.energy == base.energy
    # art filtered → library art fallback
    fb, why3 = select_copy(
        {"title": "Safe Title", "art": "a war scene"},
        scene=SCENES["meadow"],
    )
    assert fb is not None and len(fb["art"]) > 5
    print("filter_ok", why3 or "art_fallback")

    signals = {
        "accuracy": 0.9,
        "wpm": 18,
        "streak": 5,
        "level_id": "meadow",
        "theme_scene": "meadow",
    }
    scene, extras, tag = continuous_enrich(base, signals, use_minimax=False)
    assert "offline" in tag and scene.id == "meadow"
    print("offline_copy_ok", tag)

    if not has_api_key():
        print("LIVE_SKIP no MINIMAX_API_KEY")
        print("SMOKE_OK minimax_copy filter")
        return 0

    os.environ["TYPEPLAY_MODE"] = "minimax"
    scene2, extras2, tag2 = continuous_enrich(base, signals, use_minimax=True)
    print(
        "live:",
        json.dumps(
            {
                "tag": tag2,
                "status": extras2.get("minimax_status"),
                "error": extras2.get("minimax_error"),
                "ms": extras2.get("last_ms"),
                "hash": extras2.get("content_hash"),
                "id": scene2.id,
                "title": scene2.title,
                "blurb": (scene2.blurb or "")[:60],
                "art_lines": len(scene2.art.splitlines()),
                "fb_zh": (extras2.get("feedback_zh") or "")[:40],
            },
            ensure_ascii=False,
        ),
    )
    assert extras2.get("minimax_status") == "ok", extras2
    assert scene2.id == base.id and scene2.hue == base.hue
    assert scene2.title and scene2.art
    print("SMOKE_OK minimax_copy")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
