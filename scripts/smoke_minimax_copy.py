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
    enrich_scene_copy,
    has_api_key,
    kid_safe_copy,
    select_copy,
)
from host.scenes import SCENES  # noqa: E402


def main() -> int:
    assert kid_safe_copy("Sunny Meadow Friends")
    assert not kid_safe_copy("scary monster battle")
    assert select_copy({"title": "kill zone", "art": "boom"}) is None
    safe = select_copy(
        {"title": "Happy Meadow", "blurb": "flowers smile", "art": "  🌻\n bunny"}
    )
    assert safe and safe["title"] == "Happy Meadow"
    base = SCENES["meadow"]
    merged = apply_copy(base, safe)
    assert merged.id == "meadow" and merged.hue == base.hue and merged.energy == base.energy
    assert merged.title == "Happy Meadow"
    print("filter_ok")

    signals = {
        "accuracy": 0.9,
        "wpm": 18,
        "streak": 5,
        "level_id": "meadow",
        "theme_scene": "meadow",
    }
    # offline enrich
    os.environ["TYPEPLAY_MODE"] = "offline"
    scene, tag = enrich_scene_copy(base, signals, use_minimax=False)
    assert "offline" in tag and scene.id == "meadow"
    print("offline_copy_ok", tag)

    if not has_api_key():
        print("LIVE_SKIP no MINIMAX_API_KEY")
        print("SMOKE_OK minimax_copy filter")
        return 0

    os.environ["TYPEPLAY_MODE"] = "minimax"
    scene2, tag2 = enrich_scene_copy(base, signals, use_minimax=True)
    print(
        "live:",
        json.dumps(
            {
                "tag": tag2,
                "id": scene2.id,
                "hue": scene2.hue,
                "energy": scene2.energy,
                "title": scene2.title,
                "blurb": scene2.blurb[:80],
                "art_lines": len(scene2.art.splitlines()),
            },
            ensure_ascii=False,
        ),
    )
    assert scene2.id == base.id and scene2.hue == base.hue
    print("SMOKE_OK minimax_copy")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
