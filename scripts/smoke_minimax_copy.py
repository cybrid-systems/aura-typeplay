#!/usr/bin/env python3
"""Smoke MiniMax copy (filter + KEY_FILE env-file resolve). Never print secrets."""

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
    _HINT_KEY_INVALID,
    _HINT_KEY_MISSING_FILE,
    _HTTP_401_HINT,
    _friendly_http_error,
    _sanitize_api_key,
    apply_copy,
    continuous_enrich,
    has_api_key,
    kid_safe_copy,
    kid_safe_hit,
    resolve_minimax,
    select_copy,
)
from host.scenes import SCENES  # noqa: E402


def _assert_keyfile_only_env() -> None:
    """aura-build shape: env file has KEY_FILE + BASE + MODEL, no inline KEY."""
    with tempfile.TemporaryDirectory() as td:
        td_path = Path(td)
        key_path = td_path / "minimax"
        key_path.write_text("Bearer sk-unit-test-key-xyz\n", encoding="utf-8")
        env_path = td_path / "minimax.env"
        env_path.write_text(
            "\n".join(
                [
                    "MINIMAX_BASE_URL=https://api.minimax.cn/v1",
                    "MINIMAX_MODEL=MiniMax-M3",
                    f"MINIMAX_API_KEY_FILE={key_path}",
                    "",
                ]
            ),
            encoding="utf-8",
        )
        # No process KEY / KEY_FILE — only the env file (user's real layout).
        environ = {
            "HOME": str(td_path / "nohome"),
            "AURA_BUILD_MINIMAX_ENV": str(env_path),
        }
        cfg = resolve_minimax(environ=environ)
        assert cfg.api_key == "sk-unit-test-key-xyz", "KEY_FILE from env file not loaded"
        assert cfg.base_url == "https://api.minimax.cn/v1"
        assert cfg.model == "MiniMax-M3"
        assert cfg.key_file == str(key_path)
        assert not cfg.error

        # Missing KEY_FILE path → clear chip hint
        missing = td_path / "missing_key"
        env_path.write_text(
            f"MINIMAX_BASE_URL=https://api.minimax.cn/v1\n"
            f"MINIMAX_MODEL=MiniMax-M3\n"
            f"MINIMAX_API_KEY_FILE={missing}\n",
            encoding="utf-8",
        )
        cfg2 = resolve_minimax(environ=environ)
        assert not cfg2.api_key
        assert cfg2.error == _HINT_KEY_MISSING_FILE
        chip = minimax_status_chip("fail", err=cfg2.error)
        assert "密钥文件不存在" in chip

        # ~ expansion
        home = td_path / "home"
        home.mkdir()
        tilde_key = home / "k"
        tilde_key.write_text("sk-tilde-key", encoding="utf-8")
        env_path.write_text(
            "MINIMAX_BASE_URL=https://api.minimax.cn/v1\n"
            "MINIMAX_MODEL=MiniMax-M3\n"
            "MINIMAX_API_KEY_FILE=~/k\n",
            encoding="utf-8",
        )
        environ3 = {
            "HOME": str(home),
            "AURA_BUILD_MINIMAX_ENV": str(env_path),
        }
        cfg3 = resolve_minimax(environ=environ3)
        assert cfg3.api_key == "sk-tilde-key"
    print("keyfile_only_env_ok")


def main() -> int:
    assert kid_safe_copy("warm sunlight on flowers")
    assert kid_safe_hit("war zone") == "war"
    bad, why = select_copy({"title": "kill zone", "art": "boom"})
    assert bad is None and "filter" in why
    safe, why2 = select_copy(
        {"title": "Happy Meadow", "blurb": "flowers smile", "art": "  🌻\n bunny"},
        scene=SCENES["meadow"],
    )
    assert safe and why2 == ""
    base = SCENES["meadow"]
    assert apply_copy(base, safe).id == "meadow"
    print("filter_ok")

    assert _sanitize_api_key("  Bearer sk-ab\n") == "sk-ab"
    assert _friendly_http_error(401) == _HTTP_401_HINT
    assert _HINT_KEY_INVALID in minimax_status_chip("fail", err=_HTTP_401_HINT)
    assert "{" not in minimax_status_chip("fail", err='http:401:{"x":1}')
    _assert_keyfile_only_env()

    signals = {
        "accuracy": 0.9,
        "wpm": 18,
        "streak": 5,
        "level_id": "meadow",
        "theme_scene": "meadow",
    }
    scene, extras, tag = continuous_enrich(base, signals, use_minimax=False)
    assert "offline" in tag
    print("offline_copy_ok", tag)

    # Resolve against real box config without printing secrets.
    cfg = resolve_minimax()
    pub = cfg.public_dict()
    print("resolve_public:", json.dumps(pub, ensure_ascii=False))
    if not cfg.api_key:
        print("LIVE_SKIP", cfg.error or "no_key")
        print("SMOKE_OK minimax_copy filter+keyfile")
        return 0

    # Optional live call — status only, never key material.
    os.environ["TYPEPLAY_MODE"] = "minimax"
    scene2, extras2, tag2 = continuous_enrich(base, signals, use_minimax=True)
    status = extras2.get("minimax_status")
    err = str(extras2.get("minimax_error") or "")
    print(
        "live:",
        json.dumps(
            {
                "tag": tag2,
                "status": status,
                "error": err,
                "ms": extras2.get("last_ms"),
                "hash": extras2.get("content_hash"),
                "title_len": len(scene2.title or ""),
                "art_lines": len((scene2.art or "").splitlines()),
            },
            ensure_ascii=False,
        ),
    )
    if status == "fail":
        if "401" in err or _HINT_KEY_INVALID in err:
            assert _HINT_KEY_INVALID in err or "401" in err
            assert "{" not in err
            print("LIVE_AUTH_FAIL_CHIP_OK")
        elif _HINT_KEY_MISSING_FILE in err:
            print("LIVE_KEY_FILE_MISSING_OK")
        else:
            print("LIVE_FAIL", err)
        print("SMOKE_OK minimax_copy keyfile")
        return 0
    assert status == "ok", extras2
    assert scene2.title and scene2.art
    print("SMOKE_OK minimax_copy")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
