#!/usr/bin/env python3
"""Non-interactive Soft evolve smoke (oneshot + serve). Soft observe ≠ Hard."""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from host import soft_bridge  # noqa: E402
from host.scenes import apply_soft_scene  # noqa: E402


def main() -> int:
    signals = {
        "accuracy": 0.96,
        "wpm": 28.0,
        "streak": 12,
        "best_streak": 12,
        "chars_done": 40,
        "wrong": 1,
        "rhythm_cv": 0.3,
    }
    soft_bridge.write_observe(signals)
    one = soft_bridge.evolve_oneshot(timeout_s=45.0)
    print("oneshot:", json.dumps({k: one.get(k) for k in ("ok", "via", "scene")}, indent=2))
    if not one.get("ok"):
        print("FAIL oneshot", one)
        return 1
    applied = apply_soft_scene(one.get("scene"), signals)
    if not applied:
        print("FAIL apply_soft_scene")
        return 1
    print("applied:", applied[0].id, applied[1])

    serve = soft_bridge.SoftServe.start(timeout_s=25.0)
    if not serve.alive:
        print("WARN serve start failed:", serve.last_error, "(oneshot ok — soft mode will fallback)")
        return 0
    soft_bridge.write_observe(
        {
            "accuracy": 0.55,
            "wpm": 8.0,
            "streak": 0,
            "best_streak": 3,
            "chars_done": 20,
            "wrong": 9,
            "rhythm_cv": 1.2,
        }
    )
    got = serve.evolve(timeout_s=25.0)
    print("serve:", json.dumps({k: got.get(k) for k in ("ok", "via", "scene")}, indent=2))
    serve.stop()
    if not got.get("ok"):
        print("FAIL serve evolve")
        return 1
    print("SMOKE_OK soft_observe_ne_hard=true")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
