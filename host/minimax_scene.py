"""Thin MiniMax scene **copy** propose — Soft/host own id/hue/energy.

MiniMax only proposes kid-safe title / blurb / ASCII art flavor for the
*current* Soft (or offline) scene. Soft or host select-best the scene id;
host never gold-hardcodes overrides of accepted LLM copy (unsafe → drop
proposal and keep rule-based library copy).

Env:
  MINIMAX_API_KEY   required for live propose
  MINIMAX_BASE_URL  optional (default https://api.minimaxi.com/v1)
  MINIMAX_MODEL     optional (default MiniMax-Text-01 / MiniMax-M2.5-ish)
"""

from __future__ import annotations

import json
import os
import re
import urllib.error
import urllib.request
from typing import Any

from host.scenes import SCENES, Scene

# CN OpenAI-compatible endpoint (matches aura-build dogfood)
DEFAULT_BASE = "https://api.minimaxi.com/v1"
DEFAULT_MODEL = "MiniMax-M3"

# Block scary / violent / adult content in proposed copy (reject → rule-based).
_BLOCK_RE = re.compile(
    r"("
    r"kill|murder|blood|gore|weapon|gun|knife|sword|bomb|explod|"
    r"war|battle|fight|attack|die|death|dead|ghost|haunt|horror|"
    r"scary|terror|monster|demon|zombie|skull|violent|abuse|"
    r"hate|racist|sex|nude|drug|alcohol|cigarette"
    r")",
    re.IGNORECASE,
)


def has_api_key() -> bool:
    return bool(os.environ.get("MINIMAX_API_KEY", "").strip())


def _lock_base_url(url: str | None) -> str:
    raw = (url or "").strip().rstrip("/")
    if not raw:
        return DEFAULT_BASE
    lower = raw.lower()
    if "minimax.io" in lower:
        return DEFAULT_BASE
    if "minimaxi.com" in lower:
        return raw if lower.endswith("/v1") else DEFAULT_BASE
    return DEFAULT_BASE


def kid_safe_copy(text: str) -> bool:
    """True if text passes the kid-safe content filter."""
    if not text or not str(text).strip():
        return False
    return _BLOCK_RE.search(str(text)) is None



def _extract_json_obj(text: str) -> dict[str, Any] | None:
    """Parse JSON object from model output (may include <think> prose)."""
    if not text:
        return None
    s = text.strip()
    # Drop common chain-of-thought wrappers
    if "</think>" in s:
        s = s.split("</think>", 1)[-1].strip()
    if s.startswith("```"):
        s = s.strip("`")
        if s.lower().startswith("json"):
            s = s[4:].strip()
    try:
        obj = json.loads(s)
        return obj if isinstance(obj, dict) else None
    except json.JSONDecodeError:
        pass
    decoder = json.JSONDecoder()
    # Prefer the last successful object (final answer after thinking)
    last: dict[str, Any] | None = None
    for i, ch in enumerate(s):
        if ch != "{":
            continue
        try:
            obj, _ = decoder.raw_decode(s, i)
        except json.JSONDecodeError:
            continue
        if isinstance(obj, dict) and ("title" in obj or "art" in obj):
            last = obj
    return last


def _prompt(scene: Scene, signals: dict) -> str:
    return (
        "You write kid-safe COPY only for a typing-game scene panel.\n"
        "Do NOT change scene id, hue, or energy — those are fixed by Soft.\n"
        "Return JSON only with keys:\n"
        "  title  (short cheerful English title, ≤6 words)\n"
        "  blurb  (one kind sentence, EN or EN+中文, ≤20 words)\n"
        "  art    (5-7 lines ascii/emoji art matching the scene theme)\n"
        f"Locked scene id={scene.id} hue={scene.hue} energy={scene.energy}\n"
        f"Level/theme hints: {json.dumps({k: signals.get(k) for k in ('level_id','theme_scene','accuracy','streak','wpm')})}\n"
        "Rules: friendly animals, nature, space wonder, calm focus, celebration.\n"
        "FORBIDDEN: scary, violent, weapons, death, horror, adult topics.\n"
        "Respond with a single JSON object, no markdown."
    )


def propose_copy(
    scene: Scene,
    signals: dict,
    *,
    timeout: float = 30.0,
) -> dict[str, Any] | None:
    """Ask MiniMax for title/blurb/art for *this* Soft scene. None if no key/error."""
    key = os.environ.get("MINIMAX_API_KEY", "").strip()
    if not key:
        return None

    base = _lock_base_url(os.environ.get("MINIMAX_BASE_URL"))
    model = os.environ.get("MINIMAX_MODEL", DEFAULT_MODEL)
    url = f"{base}/chat/completions"
    body = {
        "model": model,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are a kids game copywriter. JSON only. "
                    "Never invent violence or scary themes."
                ),
            },
            {"role": "user", "content": _prompt(scene, signals)},
        ],
        "temperature": 0.85,
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
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError, json.JSONDecodeError, OSError):
        return None

    try:
        content = raw["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError):
        return None

    text = (content or "").strip()
    data = _extract_json_obj(text)
    if not isinstance(data, dict):
        return None
    return data


def select_copy(proposal: dict[str, Any] | None) -> dict[str, str] | None:
    """Host select-best for copy: accept LLM fields if kid-safe; else None.

    No gold rewrite of LLM strings — only accept or reject.
    """
    if not proposal or not isinstance(proposal, dict):
        return None
    title = str(proposal.get("title") or "").strip()
    blurb = str(proposal.get("blurb") or proposal.get("subtitle") or "").strip()
    art = str(proposal.get("art") or "").strip()
    if not title or not art:
        return None
    if not kid_safe_copy(title) or not kid_safe_copy(art):
        return None
    if blurb and not kid_safe_copy(blurb):
        blurb = ""  # drop blurb only; keep title/art if safe
    return {"title": title, "blurb": blurb, "art": art}


def apply_copy(base: Scene, copy: dict[str, str]) -> Scene:
    """Merge accepted MiniMax copy onto Soft-owned id/hue/energy. No param overrides."""
    return Scene(
        id=base.id,
        title=copy["title"],
        art=copy["art"],
        hue=base.hue,
        energy=base.energy,
        blurb=copy.get("blurb") or "",
    )


def rule_based_copy(scene: Scene) -> Scene:
    """Offline / no-key: library art already on scene (identity)."""
    if scene.id in SCENES and not scene.blurb:
        lib = SCENES[scene.id]
        return Scene(
            id=scene.id,
            title=scene.title or lib.title,
            art=scene.art or lib.art,
            hue=scene.hue,
            energy=scene.energy,
            blurb=lib.blurb,
        )
    return scene


def enrich_scene_copy(
    scene: Scene,
    signals: dict,
    *,
    use_minimax: bool | None = None,
) -> tuple[Scene, str]:
    """Fill copy for Soft-owned scene. Returns (scene, source_tag).

    use_minimax defaults True when TYPEPLAY_MODE=minimax or TYPEPLAY_MINIMAX_COPY=1
    and API key is set.
    """
    if use_minimax is None:
        mode = os.environ.get("TYPEPLAY_MODE", "offline").lower()
        flag = os.environ.get("TYPEPLAY_MINIMAX_COPY", "").strip() in ("1", "true", "yes")
        use_minimax = (mode == "minimax" or flag) and has_api_key()

    if not use_minimax:
        return rule_based_copy(scene), "copy/offline"

    proposal = propose_copy(scene, signals)
    chosen = select_copy(proposal)
    if chosen:
        return apply_copy(scene, chosen), "copy/minimax"
    return rule_based_copy(scene), "copy/offline(fallback)"


# --- back-compat thin aliases (older callers) ---

def propose_scene(signals: dict, *, timeout: float = 12.0) -> dict[str, Any] | None:
    """Deprecated path: propose copy for rule-based scene id from signals."""
    from host.scenes import rule_based_scene

    base = rule_based_scene(signals)
    return propose_copy(base, signals, timeout=timeout)


def propose_or_none(signals: dict) -> dict[str, Any] | None:
    if os.environ.get("TYPEPLAY_MODE", "offline").lower() != "minimax":
        return None
    return propose_scene(signals)


def scene_from_copy_proposal(base: Scene, proposal: dict | None) -> Scene | None:
    chosen = select_copy(proposal)
    if not chosen:
        return None
    return apply_copy(base, chosen)


def _multi_prompt(scene: Scene, signals: dict, n: int = 3) -> str:
    return (
        f"Propose {n} kid-safe typing-game scene COPY variants as JSON only.\n"
        "Soft already locked scene id/hue/energy — you only invent flavor.\n"
        'Return: {"candidates":[{title,blurb,art,style,feedback_en,feedback_zh,line_flavor},...]}\n'
        "style: one of gentle|sparkle|party|soft|wonder\n"
        "line_flavor: short EN hint for the next typing vibe (≤8 words)\n"
        "feedback_en / feedback_zh: encouraging micro lines\n"
        f"Locked id={scene.id} hue={scene.hue} energy={scene.energy} mood={getattr(scene, 'blurb', '')}\n"
        f"signals={json.dumps({k: signals.get(k) for k in ('accuracy','streak','wpm','rhythm_cv','recent_accuracy','burstiness','theme_scene','level_id')})}\n"
        "FORBIDDEN: scary, violent, weapons, death, horror, adult topics.\n"
        "JSON only, no markdown."
    )


def _chat(messages: list[dict], *, timeout: float = 30.0, temperature: float = 0.9) -> dict[str, Any] | None:
    key = os.environ.get("MINIMAX_API_KEY", "").strip()
    if not key:
        return None
    base = _lock_base_url(os.environ.get("MINIMAX_BASE_URL"))
    model = os.environ.get("MINIMAX_MODEL", DEFAULT_MODEL)
    url = f"{base}/chat/completions"
    body = {"model": model, "messages": messages, "temperature": temperature}
    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        headers={"Content-Type": "application/json", "Authorization": f"Bearer {key}"},
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = json.loads(resp.read().decode("utf-8"))
        content = raw["choices"][0]["message"]["content"]
    except Exception:  # noqa: BLE001
        return None
    return _extract_json_obj(content or "")


def propose_copy_multi(
    scene: Scene,
    signals: dict,
    *,
    n: int = 3,
    timeout: float = 35.0,
) -> list[dict[str, Any]]:
    """MiniMax multi-propose copy/style/feedback; Soft/host select-best later."""
    data = _chat(
        [
            {
                "role": "system",
                "content": "Kids game copywriter. JSON only. Never scary/violent.",
            },
            {"role": "user", "content": _multi_prompt(scene, signals, n=n)},
        ],
        timeout=timeout,
        temperature=0.92,
    )
    if not data:
        return []
    cands = data.get("candidates")
    if isinstance(cands, list):
        return [c for c in cands if isinstance(c, dict)]
    # single object fallback
    if "title" in data or "art" in data:
        return [data]
    return []


def select_best_copy(
    candidates: list[dict[str, Any]],
    scene: Scene,
    signals: dict,
) -> dict[str, Any] | None:
    """Thin host select-best among MiniMax candidates using Soft signals.

    No gold rewrite of LLM strings — score + kid-safe accept/reject only.
    Soft owns scene id; preference uses streak/rhythm/accuracy.
    """
    streak = int(signals.get("streak", 0) or 0)
    rhythm = float(signals.get("rhythm_cv", 0) or 0)
    acc = float(signals.get("accuracy", 1) or 1)
    prefer_style = "gentle"
    if streak >= 12:
        prefer_style = "party"
    elif streak >= 6:
        prefer_style = "sparkle"
    elif rhythm > 0.75 or acc < 0.75:
        prefer_style = "soft"
    elif scene.id in ("space",):
        prefer_style = "wonder"

    best: dict[str, Any] | None = None
    best_score = -1.0
    for raw in candidates:
        chosen = select_copy(raw)
        if not chosen:
            continue
        style = str(raw.get("style") or "gentle")
        if style and not kid_safe_copy(style):
            continue
        fe = str(raw.get("feedback_en") or "")
        fz = str(raw.get("feedback_zh") or "")
        lf = str(raw.get("line_flavor") or "")
        for extra in (fe, fz, lf):
            if extra and not kid_safe_copy(extra):
                fe, fz, lf = "", "", lf if kid_safe_copy(lf) else ""
                break
        score = 1.0
        if style == prefer_style:
            score += 2.0
        if fe and fz:
            score += 0.8
        if lf:
            score += 0.4
        if len(chosen["art"].splitlines()) >= 4:
            score += 0.5
        if score > best_score:
            best_score = score
            best = {
                **chosen,
                "style": style or prefer_style,
                "feedback_en": fe,
                "feedback_zh": fz,
                "line_flavor": lf,
            }
    return best


def continuous_enrich(
    scene: Scene,
    signals: dict,
    *,
    use_minimax: bool,
) -> tuple[Scene, dict[str, Any], str]:
    """Background path: multi-propose → select-best → scene + extras.

    Returns (scene, extras, tag). extras may include style/feedback/line_flavor.
    """
    extras: dict[str, Any] = {}
    if not use_minimax or not has_api_key():
        return rule_based_copy(scene), extras, "copy/offline"
    cands = propose_copy_multi(scene, signals)
    chosen = select_best_copy(cands, scene, signals)
    if not chosen:
        return rule_based_copy(scene), extras, "copy/offline(fallback)"
    extras = {
        "style": chosen.get("style") or "gentle",
        "feedback_en": chosen.get("feedback_en") or "",
        "feedback_zh": chosen.get("feedback_zh") or "",
        "line_flavor": chosen.get("line_flavor") or "",
        "n_propose": len(cands),
    }
    return apply_copy(scene, chosen), extras, "copy/minimax-select-best"
