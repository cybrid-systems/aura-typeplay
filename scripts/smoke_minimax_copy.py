#!/usr/bin/env python3
"""Smoke MiniMax copy propose (filter + key resolve + optional live). Soft owns id/hue/energy."""

from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from host.app import minimax_status_chip  # noqa: E402
from host.minimax_scene import (  # noqa: E402
    _HTTP_401_HINT,
    _friendly_http_error,
    _sanitize_api_key,
    apply_copy,
    continuous_enrich,
    has_api_key,
    kid_safe_copy,
    kid_safe_hit,
    resolve_api_key,
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
    fb, why3 = select_copy(
        {"title": "Safe Title", "art": "a war scene"},
        scene=SCENES["meadow"],
    )
    assert fb is not None and len(fb["art"]) > 5
    print("filter_ok", why3 or "art_fallback")

    # Key sanitize + 401 chip (never print secrets)
    assert _sanitize_api_key("  Bearer sk-test-key\n") == "sk-test-key"
    assert _sanitize_api_key("bearer SK-X") == "SK-X"
    assert _friendly_http_error(401, '{"status":"unauthorized"}') == _HTTP_401_HINT
    chip = minimax_status_chip("fail", err='http:401:{"msg":"no"}')
    assert "密钥无效或未加载" in chip and "{" not in chip
    with tempfile.TemporaryDirectory() as td:
        key_path = Path(td) / "key"
        key_path.write_text("Bearer sk-from-file\n", encoding="utf-8")
        env_path = Path(td) / "minimax.env"
        env_path.write_text(
            f"MINIMAX_API_KEY_FILE={key_path}\nMINIMAX_MODEL=MiniMax-M3\n",
            encoding="utf-8",
        )
        got = resolve_api_key(
            environ={
                "TYPEPLAY_MINIMAX_ENV": str(env_path),
                "HOME": "/nonexistent",
            }
        )
        assert got == "sk-from-file", "env-file KEY_FILE path failed"
        got2 = resolve_api_key(
            environ={"MINIMAX_API_KEY": "  Bearer sk-env\n", "HOME": "/nonexistent"}
        )
        assert got2 == "sk-env"
    print("key_resolve_ok")

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
        print("LIVE_SKIP no MiniMax key resolved")
        print("SMOKE_OK minimax_copy filter+key")
        return 0

    # Live call — may use env KEY or aura-build minimax.env; never print key.
    os.environ["TYPEPLAY_MODE"] = "minimax"
    scene2, extras2, tag2 = continuous_enrich(base, signals, use_minimax=True)
    status = extras2.get("minimax_status")
    err = extras2.get("minimax_error") or ""
    print(
        "live:",
        json.dumps(
            {
                "tag": tag2,
                "status": status,
                "error": err,
                "ms": extras2.get("last_ms"),
                "hash": extras2.get("content_hash"),
                "id": scene2.id,
                "title": (scene2.title or "")[:40],
                "blurb": (scene2.blurb or "")[:60],
                "art_lines": len((scene2.art or "").splitlines()),
                "fb_zh": (extras2.get("feedback_zh") or "")[:40],
                "key_resolved": True,
            },
            ensure_ascii=False,
        ),
    )
    if status == "fail" and ("401" in err or "密钥" in err):
        assert "密钥无效或未加载" in err or "401" in err
        assert "{" not in err
        print("LIVE_AUTH_FAIL_CHIP_OK")
        print("SMOKE_OK minimax_copy key+401_hint")
        return 0
    assert status == "ok", extras2
    assert scene2.id == base.id and scene2.hue == base.hue
    assert scene2.title and scene2.art
    print("SMOKE_OK minimax_copy")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
