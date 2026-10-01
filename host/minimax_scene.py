"""Thin MiniMax scene **copy** propose — Soft/host own id/hue/energy.

MiniMax only proposes kid-safe title / blurb / ASCII art flavor for the
*current* Soft (or offline) scene. Soft or host select-best the scene id;
host never gold-hardcodes overrides of accepted LLM copy (unsafe fields
dropped; Soft/library art may fill if LLM art alone is filtered).

Env:
  MINIMAX_API_KEY   required for live propose
  MINIMAX_BASE_URL  optional (default https://api.minimaxi.com/v1)
  MINIMAX_MODEL     optional (default MiniMax-M3)
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import time
import urllib.error
import urllib.request
from typing import Any

from host.scenes import SCENES, Scene

DEFAULT_BASE = "https://api.minimaxi.com/v1"
DEFAULT_MODEL = "MiniMax-M3"

# Word-boundary blocks — avoid false positives (war⊂warm, sex⊂next, die⊂dier…).
_BLOCK_RE = re.compile(
    r"(?i)(?<![a-z])("
    r"kill|murder|blood|gore|weapon|gun|knife|sword|bomb|explode|explosion|"
    r"war|battle|fight|attack|death|dead|ghost|haunt|horror|"
    r"scary|terror|monster|demon|zombie|skull|violent|abuse|"
    r"hate|racist|nude|drugs?|alcohol|cigarette"
    r")(?![a-z])"
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
    """True if text passes the kid-safe content filter (word-boundary)."""
    if not text or not str(text).strip():
        return False
    return _BLOCK_RE.search(str(text)) is None


def kid_safe_hit(text: str) -> str | None:
    """Return matched blocked token, or None if safe/empty."""
    if not text or not str(text).strip():
        return "empty"
    m = _BLOCK_RE.search(str(text))
    return m.group(0).lower() if m else None


def _extract_json_obj(text: str) -> dict[str, Any] | None:
    """Parse JSON object from model output (may include <think> prose)."""
    if not text:
        return None
    s = text.strip()
    if "</think>" in s:
        s = s.split("</think>", 1)[-1].strip()
    # strip other think open tags leftovers
    if "<think>" in s.lower():
        idx = s.lower().rfind("</think>")
        if idx >= 0:
            s = s[idx + len("</think>") :].strip()
    if s.startswith("```"):
        s = s.strip("`")
        if s.lower().startswith("json"):
            s = s[4:].strip()
    try:
        obj = json.loads(s)
        if isinstance(obj, dict):
            return obj
        if isinstance(obj, list) and obj and isinstance(obj[0], dict):
            return {"candidates": obj}
    except json.JSONDecodeError:
        pass
    decoder = json.JSONDecoder()
    last: dict[str, Any] | None = None
    for i, ch in enumerate(s):
        if ch != "{":
            continue
        try:
            obj, _ = decoder.raw_decode(s, i)
        except json.JSONDecodeError:
            continue
        if not isinstance(obj, dict):
            continue
        if "candidates" in obj or "title" in obj or "art" in obj:
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
        "Avoid words like war/kill/death even inside longer words if unsure.\n"
        "Respond with a single JSON object, no markdown."
    )


class MiniMaxChatError(Exception):
    """Structured MiniMax failure for chip display."""

    def __init__(self, reason: str):
        super().__init__(reason)
        self.reason = reason[:48]


def _chat_raw(
    messages: list[dict],
    *,
    timeout: float = 35.0,
    temperature: float = 0.9,
) -> tuple[dict[str, Any] | None, str]:
    """Return (parsed_obj|None, error_reason). error empty on success."""
    key = os.environ.get("MINIMAX_API_KEY", "").strip()
    if not key:
        return None, "no_key"
    base = _lock_base_url(os.environ.get("MINIMAX_BASE_URL"))
    model = os.environ.get("MINIMAX_MODEL", DEFAULT_MODEL)
    url = f"{base}/chat/completions"
    body = {"model": model, "messages": messages, "temperature": temperature}
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
    except urllib.error.HTTPError as exc:
        detail = ""
        try:
            detail = exc.read().decode("utf-8", errors="replace")[:80]
        except Exception:  # noqa: BLE001
            pass
        return None, f"http:{exc.code}:{detail[:24] or exc.reason}"
    except urllib.error.URLError as exc:
        return None, f"net:{type(exc.reason).__name__ if exc.reason else 'URLError'}"
    except TimeoutError:
        return None, "timeout"
    except json.JSONDecodeError:
        return None, "http_json"
    except OSError as exc:
        return None, f"os:{type(exc).__name__}"

    # MiniMax sometimes wraps status in base_resp
    base_resp = raw.get("base_resp") if isinstance(raw, dict) else None
    if isinstance(base_resp, dict):
        code = base_resp.get("status_code", 0)
        if code not in (0, "0", None):
            msg = str(base_resp.get("status_msg") or code)[:28]
            return None, f"api:{code}:{msg}"

    try:
        content = raw["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError):
        return None, "shape:no_choices"

    data = _extract_json_obj(content or "")
    if not isinstance(data, dict):
        preview = (content or "").strip().replace("\n", " ")[:40]
        return None, f"parse:{preview or 'empty'}"
    return data, ""


def _chat(
    messages: list[dict],
    *,
    timeout: float = 30.0,
    temperature: float = 0.9,
) -> dict[str, Any] | None:
    data, _err = _chat_raw(messages, timeout=timeout, temperature=temperature)
    return data


def propose_copy(
    scene: Scene,
    signals: dict,
    *,
    timeout: float = 30.0,
) -> dict[str, Any] | None:
    """Ask MiniMax for title/blurb/art for *this* Soft scene."""
    data, err = _chat_raw(
        [
            {
                "role": "system",
                "content": (
                    "You are a kids game copywriter. JSON only. "
                    "Never invent violence or scary themes."
                ),
            },
            {"role": "user", "content": _prompt(scene, signals)},
        ],
        timeout=timeout,
        temperature=0.85,
    )
    if err or not data:
        return None
    return data


def select_copy(
    proposal: dict[str, Any] | None,
    *,
    scene: Scene | None = None,
) -> tuple[dict[str, str] | None, str]:
    """Accept LLM fields if kid-safe. Returns (copy|None, reject_reason).

    If art alone is blocked but title is safe and scene known, use library art
    (not a rewrite of LLM title/blurb).
    """
    if not proposal or not isinstance(proposal, dict):
        return None, "empty_proposal"
    title = str(proposal.get("title") or "").strip()
    blurb = str(proposal.get("blurb") or proposal.get("subtitle") or "").strip()
    art = str(proposal.get("art") or "").strip()
    if not title:
        return None, "no_title"
    hit = kid_safe_hit(title)
    if hit:
        return None, f"filter:title:{hit}"
    if art:
        hit = kid_safe_hit(art)
        if hit:
            # Soft/library art fallback for known scene ids
            if scene is not None and scene.id in SCENES:
                art = SCENES[scene.id].art.strip("\n")
            else:
                return None, f"filter:art:{hit}"
    elif scene is not None and scene.id in SCENES:
        art = SCENES[scene.id].art.strip("\n")
    else:
        return None, "no_art"
    if blurb:
        hit = kid_safe_hit(blurb)
        if hit:
            blurb = ""
    return {"title": title, "blurb": blurb, "art": art}, ""


def apply_copy(base: Scene, copy: dict[str, str]) -> Scene:
    """Merge accepted MiniMax copy onto Soft-owned id/hue/energy."""
    return Scene(
        id=base.id,
        title=copy["title"],
        art=copy["art"],
        hue=base.hue,
        energy=base.energy,
        blurb=copy.get("blurb") or "",
    )


def rule_based_copy(scene: Scene) -> Scene:
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
    if use_minimax is None:
        mode = os.environ.get("TYPEPLAY_MODE", "offline").lower()
        flag = os.environ.get("TYPEPLAY_MINIMAX_COPY", "").strip() in ("1", "true", "yes")
        use_minimax = (mode == "minimax" or flag) and has_api_key()
    if not use_minimax:
        return rule_based_copy(scene), "copy/offline"
    proposal = propose_copy(scene, signals)
    chosen, _why = select_copy(proposal, scene=scene)
    if chosen:
        return apply_copy(scene, chosen), "copy/minimax"
    return rule_based_copy(scene), "copy/offline(fallback)"


def propose_scene(signals: dict, *, timeout: float = 12.0) -> dict[str, Any] | None:
    from host.scenes import rule_based_scene

    base = rule_based_scene(signals)
    return propose_copy(base, signals, timeout=timeout)


def propose_or_none(signals: dict) -> dict[str, Any] | None:
    if os.environ.get("TYPEPLAY_MODE", "offline").lower() != "minimax":
        return None
    return propose_scene(signals)


def scene_from_copy_proposal(base: Scene, proposal: dict | None) -> Scene | None:
    chosen, _ = select_copy(proposal, scene=base)
    if not chosen:
        return None
    return apply_copy(base, chosen)


def _multi_prompt(scene: Scene, signals: dict, n: int = 3) -> str:
    return (
        f"Propose {n} kid-safe typing-game scene COPY variants as JSON only.\n"
        "Soft already locked scene id/hue/energy — you only invent flavor.\n"
        'Return: {"candidates":[{title,blurb,art,style,feedback_en,feedback_zh,line_flavor},...]}\n'
        "style: one of gentle|sparkle|party|soft|wonder\n"
        "art: prefer emoji/ascii line art (not long prose paragraphs)\n"
        "line_flavor: short EN hint for the next typing vibe (≤8 words)\n"
        "feedback_en / feedback_zh: encouraging micro lines\n"
        f"Locked id={scene.id} hue={scene.hue} energy={scene.energy}\n"
        f"signals={json.dumps({k: signals.get(k) for k in ('accuracy','streak','wpm','rhythm_cv','theme_scene','level_id')})}\n"
        "FORBIDDEN: violence, weapons, death, horror, adult topics.\n"
        "Do not use the standalone words: war, kill, death, blood, fight.\n"
        "JSON only, no markdown."
    )


def propose_copy_multi(
    scene: Scene,
    signals: dict,
    *,
    n: int = 3,
    timeout: float = 40.0,
) -> tuple[list[dict[str, Any]], str]:
    """Return (candidates, error_reason). error empty on success with ≥1 cand."""
    data, err = _chat_raw(
        [
            {
                "role": "system",
                "content": "Kids game copywriter. JSON only. Never scary/violent.",
            },
            {"role": "user", "content": _multi_prompt(scene, signals, n=n)},
        ],
        timeout=timeout,
        temperature=0.85,
    )
    if err:
        return [], err
    if not data:
        return [], "parse:empty"
    cands = data.get("candidates")
    out: list[dict[str, Any]] = []
    if isinstance(cands, list):
        out = [c for c in cands if isinstance(c, dict)]
    elif "title" in data or "art" in data:
        out = [data]
    if out:
        return out, ""
    # Fallback: single-object propose
    one = propose_copy(scene, signals, timeout=min(30.0, timeout))
    if one:
        return [one], ""
    return [], "no_candidates"


def select_best_copy(
    candidates: list[dict[str, Any]],
    scene: Scene,
    signals: dict,
) -> tuple[dict[str, Any] | None, str]:
    """Select-best among MiniMax candidates. Returns (best|None, reason)."""
    if not candidates:
        return None, "no_candidates"
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
    rejects: list[str] = []
    for raw in candidates:
        chosen, why = select_copy(raw, scene=scene)
        if not chosen:
            rejects.append(why or "reject")
            continue
        style = str(raw.get("style") or "gentle")
        hit = kid_safe_hit(style) if style else None
        if hit and hit != "empty":
            rejects.append(f"filter:style:{hit}")
            continue
        fe = str(raw.get("feedback_en") or "")
        fz = str(raw.get("feedback_zh") or "")
        lf = str(raw.get("line_flavor") or "")
        if fe and kid_safe_hit(fe):
            fe = ""
        if fz and kid_safe_hit(fz):
            fz = ""
        if lf and kid_safe_hit(lf):
            lf = ""
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
    if best:
        return best, ""
    # summarize rejects for chip
    reason = rejects[0] if rejects else "filtered_all"
    if len(rejects) > 1:
        reason = f"{reason}+{len(rejects)-1}more"
    return None, reason[:48]


def continuous_enrich(
    scene: Scene,
    signals: dict,
    *,
    use_minimax: bool,
) -> tuple[Scene, dict[str, Any], str]:
    """Background path: multi-propose → select-best → scene + extras.

    extras.minimax_error carries real reason: http:… / parse:… / filter:…
    """
    extras: dict[str, Any] = {
        "minimax_status": "no_key",
        "minimax_error": "",
        "last_ms": 0,
        "content_hash": "",
    }
    if not has_api_key():
        extras["minimax_status"] = "no_key"
        return rule_based_copy(scene), extras, "copy/offline(no-key)"
    if not use_minimax:
        extras["minimax_status"] = "no_key"
        return rule_based_copy(scene), extras, "copy/offline"

    extras["minimax_status"] = "probing"
    t0 = time.monotonic()
    try:
        cands, cerr = propose_copy_multi(scene, signals)
    except Exception as exc:  # noqa: BLE001
        extras["minimax_status"] = "fail"
        extras["minimax_error"] = type(exc).__name__[:40]
        extras["last_ms"] = int((time.monotonic() - t0) * 1000)
        return rule_based_copy(scene), extras, "copy/minimax-fail"

    elapsed = int((time.monotonic() - t0) * 1000)
    extras["last_ms"] = elapsed
    if cerr:
        extras["minimax_status"] = "fail"
        extras["minimax_error"] = cerr[:48]
        return rule_based_copy(scene), extras, "copy/minimax-fail"

    chosen, sreason = select_best_copy(cands, scene, signals)
    if not chosen:
        extras["minimax_status"] = "fail"
        extras["minimax_error"] = (sreason or "empty_or_filtered")[:48]
        return rule_based_copy(scene), extras, "copy/minimax-fail"

    blob = json.dumps(chosen, ensure_ascii=False, sort_keys=True)
    extras.update(
        {
            "minimax_status": "ok",
            "minimax_error": "",
            "content_hash": hashlib.sha1(blob.encode("utf-8")).hexdigest()[:10],
            "style": chosen.get("style") or "gentle",
            "feedback_en": chosen.get("feedback_en") or "",
            "feedback_zh": chosen.get("feedback_zh") or "",
            "line_flavor": chosen.get("line_flavor") or "",
            "n_propose": len(cands),
        }
    )
    return apply_copy(scene, chosen), extras, "copy/minimax-select-best"
