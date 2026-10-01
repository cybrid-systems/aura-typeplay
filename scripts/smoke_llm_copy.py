#!/usr/bin/env python3
"""Smoke LLM scene copy (DeepSeek default). Never print secrets."""

from __future__ import annotations

import json
import os
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from host.app import minimax_status_chip  # noqa: E402
from host.llm_copy import (  # noqa: E402
    select_targets,
    _HINT_KEY_INVALID,
    _HINT_KEY_MISSING_FILE,
    _HTTP_401_HINT,
    _friendly_http_error,
    _sanitize_api_key,
    active_provider,
    apply_copy,
    continuous_enrich,
    has_api_key,
    kid_safe_copy,
    kid_safe_hit,
    resolve_llm,
    select_copy,
)
from host.scenes import SCENES  # noqa: E402
from host.levels import LevelProgress  # noqa: E402


def _assert_deepseek_keyfile_only() -> None:
    with tempfile.TemporaryDirectory() as td:
        td_path = Path(td)
        key_path = td_path / "deepseek_key"
        key_path.write_text("Bearer sk-ds-unit-test\n", encoding="utf-8")
        env_path = td_path / "deepseek.env"
        env_path.write_text(
            "\n".join(
                [
                    "DEEPSEEK_BASE_URL=https://api.deepseek.com",
                    "DEEPSEEK_MODEL=deepseek-flash",
                    f"DEEPSEEK_API_KEY_FILE={key_path}",
                    "",
                ]
            ),
            encoding="utf-8",
        )
        environ = {
            "HOME": str(td_path / "nohome"),
            "TYPEPLAY_LLM": "deepseek",
            "AURA_BUILD_DEEPSEEK_ENV": str(env_path),
        }
        cfg = resolve_llm(provider="deepseek", environ=environ)
        assert cfg.api_key == "sk-ds-unit-test"
        assert cfg.model == "deepseek-flash"
        assert cfg.base_url == "https://api.deepseek.com"
        assert not cfg.error

        missing = td_path / "missing"
        env_path.write_text(
            f"DEEPSEEK_BASE_URL=https://api.deepseek.com\n"
            f"DEEPSEEK_MODEL=deepseek-flash\n"
            f"DEEPSEEK_API_KEY_FILE={missing}\n",
            encoding="utf-8",
        )
        cfg2 = resolve_llm(provider="deepseek", environ=environ)
        assert not cfg2.api_key
        assert cfg2.error == _HINT_KEY_MISSING_FILE
        chip = minimax_status_chip("fail", err=cfg2.error, provider="deepseek")
        assert "DeepSeek" in chip and "密钥文件不存在" in chip
    print("deepseek_keyfile_only_ok")


def main() -> int:
    assert active_provider(environ={"TYPEPLAY_LLM": ""}) == "deepseek"
    assert active_provider(environ={"TYPEPLAY_LLM": "minimax"}) == "minimax"
    assert kid_safe_copy("warm sunlight on flowers")
    assert kid_safe_hit("war zone") == "war"
    bad, why = select_copy({"title": "kill zone", "art": "boom"})
    assert bad is None and "filter" in why
    safe, why2 = select_copy(
        {"title": "Happy Meadow", "blurb": "flowers smile", "art": "  sunflower\n bunny"},
        scene=SCENES["meadow"],
    )
    assert safe and why2 == ""
    base = SCENES["meadow"]
    assert apply_copy(base, safe).id == "meadow"
    print("filter_ok")

    # DeepSeek targets → host queue (Soft does NOT mutate from these)
    tg, why = select_targets(
        [
            {"text": "soft cat", "hint_zh": "软猫"},
            {"text": "kill mode"},
            {"text": "yellow sun"},
        ]
    )
    assert len(tg) == 2 and why.startswith("ok:")
    lp = LevelProgress()
    assert lp.offer_llm_targets(tg, source="deepseek") == 2
    assert lp.target_text() == "soft cat"
    lp.complete_line(1.0)
    assert lp.target_text() == "yellow sun"
    lp.clear_llm_targets()
    assert not lp.using_llm_targets
    print("targets_queue_ok", why)


    assert _sanitize_api_key("  Bearer sk-ab\n") == "sk-ab"
    assert _friendly_http_error(401) == _HTTP_401_HINT
    chip401 = minimax_status_chip("fail", err=_HTTP_401_HINT)
    assert _HINT_KEY_INVALID in chip401 and "DeepSeek" in chip401
    _assert_deepseek_keyfile_only()

    signals = {
        "accuracy": 0.9,
        "wpm": 18,
        "streak": 5,
        "level_id": "meadow",
        "theme_scene": "meadow",
    }
    scene, extras, tag = continuous_enrich(base, signals, use_llm=False)
    assert "offline" in tag
    print("offline_copy_ok", tag)

    cfg = resolve_llm()
    print("resolve_public:", json.dumps(cfg.public_dict(), ensure_ascii=False))
    if not cfg.api_key:
        print("LIVE_SKIP", cfg.error or "no_key")
        print("SMOKE_OK llm_copy filter+keyfile")
        return 0

    os.environ.setdefault("TYPEPLAY_LLM", "deepseek")
    scene2, extras2, tag2 = continuous_enrich(base, signals, use_llm=True)
    status = extras2.get("llm_status") or extras2.get("minimax_status")
    err = str(extras2.get("llm_error") or extras2.get("minimax_error") or "")
    print(
        "live:",
        json.dumps(
            {
                "tag": tag2,
                "provider": extras2.get("llm_provider"),
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
        print("LIVE_FAIL_CHIP", err[:48])
        print("SMOKE_OK llm_copy keyfile")
        return 0
    assert status == "ok", extras2
    assert scene2.title and scene2.art
    print("SMOKE_OK llm_copy")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
