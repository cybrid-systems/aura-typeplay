"""Thin MiniMax scene propose — env key; Soft/host select. No gold hardcoded fixes.

Env:
  MINIMAX_API_KEY   required for live propose
  MINIMAX_BASE_URL  optional (default MiniMax OpenAI-compatible endpoint)
  MINIMAX_MODEL     optional

Returns a proposal dict Soft/host may accept or ignore. Offline callers
should use host.scenes.rule_based_scene instead.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Any


DEFAULT_BASE = "https://api.minimax.chat/v1"
DEFAULT_MODEL = "MiniMax-Text-01"


def _prompt(signals: dict) -> str:
    return (
        "You propose ONE kid-friendly typing-game scene as JSON only.\n"
        "Keys: id (slug), title, art (5-7 lines ascii/emoji), hue "
        "(green|blue|magenta|yellow|cyan|white), energy (0..1).\n"
        "Match the learner's signals — calm if erratic, celebrate streaks, "
        "encourage if accuracy dips. No spoilers, no violence.\n"
        f"signals={json.dumps(signals)}\n"
        "Respond with a single JSON object, no markdown."
    )


def propose_scene(signals: dict, *, timeout: float = 12.0) -> dict[str, Any] | None:
    """Call MiniMax; return proposal dict or None on missing key / error."""
    key = os.environ.get("MINIMAX_API_KEY", "").strip()
    if not key:
        return None

    base = os.environ.get("MINIMAX_BASE_URL", DEFAULT_BASE).rstrip("/")
    model = os.environ.get("MINIMAX_MODEL", DEFAULT_MODEL)
    url = f"{base}/chat/completions"
    body = {
        "model": model,
        "messages": [
            {"role": "system", "content": "You are a kids game scene designer. JSON only."},
            {"role": "user", "content": _prompt(signals)},
        ],
        "temperature": 0.8,
    }
    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {key}",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = json.loads(resp.read().decode("utf-8"))
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, json.JSONDecodeError):
        return None

    try:
        content = raw["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError):
        return None

    text = content.strip()
    if text.startswith("```"):
        text = text.strip("`")
        if text.startswith("json"):
            text = text[4:].strip()
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return None
    if not isinstance(data, dict):
        return None
    return data


def propose_or_none(signals: dict) -> dict[str, Any] | None:
    """Host entry: only when TYPEPLAY_MODE=minimax and key present."""
    if os.environ.get("TYPEPLAY_MODE", "offline").lower() != "minimax":
        return None
    return propose_scene(signals)
