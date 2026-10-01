"""Scene **copy** LLM propose — Soft owns id/hue/energy; LLM only title/blurb/art/feedback.

Default provider: DeepSeek V4.1 Flash (`deepseek-flash`).
Optional: ``TYPEPLAY_LLM=minimax`` keeps the MiniMax path.

DeepSeek proposes **copy** (title/blurb/art/feedback) AND **typing
target words** for the current level/theme. Soft alone mutates aura
AST — this module never writes ``.aura`` files.

Key resolve (never logged) mirrors aura-build style per provider:
  DeepSeek: DEEPSEEK_API_KEY → DEEPSEEK_API_KEY_FILE → env files →
            ~/.config/aura-build/deepseek_api_key
  MiniMax:  MINIMAX_* equivalents (only when TYPEPLAY_LLM=minimax or MODE=minimax)
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Callable

from host.scenes import SCENES, Scene

REPO_ROOT = Path(__file__).resolve().parents[1]

# Word-boundary kid-safe filter (war⊂warm must NOT block).
_BLOCK_RE = re.compile(
    r"(?i)(?<![a-z])("
    r"kill|murder|blood|gore|weapon|gun|knife|sword|bomb|explode|explosion|"
    r"war|battle|fight|attack|death|dead|ghost|haunt|horror|"
    r"scary|terror|monster|demon|zombie|skull|violent|abuse|"
    r"hate|racist|nude|drugs?|alcohol|cigarette"
    r")(?![a-z])"
)

_HINT_KEY_MISSING_FILE = "密钥文件不存在"
_HINT_KEY_INVALID = "密钥无效"
_HTTP_401_HINT = f"http:401:{_HINT_KEY_INVALID}"


def _sanitize_api_key(raw: str | None) -> str:
    if not raw:
        return ""
    key = str(raw).strip().strip("\ufeff")
    if key.lower().startswith("bearer "):
        key = key[7:].strip()
    if "\n" in key or "\r" in key:
        key = "".join(part.strip() for part in key.splitlines() if part.strip())
    return key


def _parse_env_file(path: Path) -> dict[str, str]:
    out: dict[str, str] = {}
    try:
        if not path.is_file():
            return out
        for raw in path.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            out[k.strip()] = v.strip().strip('"').strip("'")
    except OSError:
        return {}
    return out


def _expand_key_path(raw: str | None, *, home: str | None = None) -> Path | None:
    if not raw or not str(raw).strip():
        return None
    s = str(raw).strip()
    if s.startswith("~"):
        homedir = home or os.environ.get("HOME") or str(Path.home())
        if s == "~":
            s = homedir
        elif s.startswith("~/"):
            s = str(Path(homedir) / s[2:])
        else:
            s = str(Path(s).expanduser())
    return Path(s)


def _read_key_file(path: Path) -> tuple[str, str]:
    try:
        if not path.is_file():
            return "", _HINT_KEY_MISSING_FILE
        key = _sanitize_api_key(path.read_text(encoding="utf-8"))
        if not key:
            return "", _HINT_KEY_MISSING_FILE
        return key, ""
    except OSError:
        return "", _HINT_KEY_MISSING_FILE


def _lock_deepseek_base(url: str | None) -> str:
    """Official OpenAI-compatible base: https://api.deepseek.com (no forced /v1)."""
    raw = (url or "").strip().rstrip("/")
    if not raw:
        return "https://api.deepseek.com"
    lower = raw.lower()
    if "deepseek.com" in lower:
        # Accept both https://api.deepseek.com and .../v1
        return raw
    return "https://api.deepseek.com"


def _lock_minimax_base(url: str | None) -> str:
    default = "https://api.minimax.cn/v1"
    raw = (url or "").strip().rstrip("/")
    if not raw:
        return default
    lower = raw.lower()
    allow_com = (os.environ.get("TYPEPLAY_MINIMAX_ALLOW_COM") or "").strip().lower() in (
        "1",
        "true",
        "yes",
    )
    if allow_com and "minimaxi.com" in lower:
        return "https://api.minimaxi.com/v1"
    if any(h in lower for h in ("minimax.io", "minimaxi.com", "minimax.cn")):
        return default
    return default


@dataclass(frozen=True)
class ProviderSpec:
    name: str
    label: str  # chip display name
    default_base: str
    default_model: str
    key_env: str
    key_file_env: str
    base_env: str
    model_env: str
    env_path_envs: tuple[str, ...]
    repo_env: Path
    typeplay_env: Path
    aura_build_env: Path
    default_key_file: Path
    lock_base: Callable[[str | None], str]
    disable_thinking: bool
    default_timeout: float


DEEPSEEK = ProviderSpec(
    name="deepseek",
    label="DeepSeek",
    default_base="https://api.deepseek.com",
    default_model="deepseek-flash",
    key_env="DEEPSEEK_API_KEY",
    key_file_env="DEEPSEEK_API_KEY_FILE",
    base_env="DEEPSEEK_BASE_URL",
    model_env="DEEPSEEK_MODEL",
    env_path_envs=(
        "TYPEPLAY_DEEPSEEK_ENV",
        "DEEPSEEK_ENV_FILE",
        "AURA_BUILD_DEEPSEEK_ENV",
    ),
    repo_env=REPO_ROOT / "deepseek.env",
    typeplay_env=Path.home() / ".config" / "aura-typeplay" / "deepseek.env",
    aura_build_env=Path.home() / ".config" / "aura-build" / "deepseek.env",
    default_key_file=Path.home() / ".config" / "aura-build" / "deepseek_api_key",
    lock_base=_lock_deepseek_base,
    disable_thinking=True,
    default_timeout=25.0,
)

MINIMAX = ProviderSpec(
    name="minimax",
    label="MiniMax",
    default_base="https://api.minimax.cn/v1",
    default_model="MiniMax-M3",
    key_env="MINIMAX_API_KEY",
    key_file_env="MINIMAX_API_KEY_FILE",
    base_env="MINIMAX_BASE_URL",
    model_env="MINIMAX_MODEL",
    env_path_envs=(
        "TYPEPLAY_MINIMAX_ENV",
        "MINIMAX_ENV_FILE",
        "AURA_BUILD_MINIMAX_ENV",
    ),
    repo_env=REPO_ROOT / "minimax.env",
    typeplay_env=Path.home() / ".config" / "aura-typeplay" / "minimax.env",
    aura_build_env=Path.home() / ".config" / "aura-build" / "minimax.env",
    default_key_file=Path.home() / ".config" / "aura-build" / "minimax_api_key",
    lock_base=_lock_minimax_base,
    disable_thinking=False,
    default_timeout=45.0,
)

_PROVIDERS = {"deepseek": DEEPSEEK, "minimax": MINIMAX}


def active_provider(*, environ: dict[str, str] | None = None) -> str:
    """Default deepseek; TYPEPLAY_LLM=minimax or TYPEPLAY_MODE=minimax → minimax."""
    env = environ if environ is not None else os.environ
    llm = (env.get("TYPEPLAY_LLM") or "").strip().lower()
    if llm in _PROVIDERS:
        return llm
    mode = (env.get("TYPEPLAY_MODE") or "").strip().lower()
    if mode == "minimax":
        return "minimax"
    return "deepseek"


def provider_spec(name: str | None = None, *, environ: dict[str, str] | None = None) -> ProviderSpec:
    return _PROVIDERS[name or active_provider(environ=environ)]


@dataclass(frozen=True)
class LlmResolved:
    provider: str
    label: str
    api_key: str
    base_url: str
    model: str
    key_file: str
    env_file: str
    error: str = ""

    def public_dict(self) -> dict[str, str]:
        return {
            "provider": self.provider,
            "label": self.label,
            "base_url": self.base_url,
            "model": self.model,
            "key_file": self.key_file or "",
            "env_file": self.env_file or "",
            "api_key": "<redacted>" if self.api_key else "",
            "error": self.error,
            "has_key": "1" if self.api_key else "0",
        }


def _candidate_env_files(spec: ProviderSpec, environ: dict[str, str]) -> list[Path]:
    paths: list[Path] = []
    for key in spec.env_path_envs:
        raw = (environ.get(key) or "").strip()
        if raw:
            paths.append(Path(raw).expanduser())
    paths.extend([spec.repo_env, spec.typeplay_env, spec.aura_build_env])
    seen: set[str] = set()
    uniq: list[Path] = []
    for p in paths:
        s = str(p.resolve()) if p.exists() else str(p)
        if s in seen:
            continue
        seen.add(s)
        uniq.append(p)
    return uniq


def resolve_llm(
    *,
    provider: str | None = None,
    environ: dict[str, str] | None = None,
) -> LlmResolved:
    """Resolve API key + base + model for the active (or named) provider."""
    env = environ if environ is not None else os.environ
    pname = provider or active_provider(environ=env)
    spec = provider_spec(pname, environ=env)

    merged: dict[str, str] = {}
    used_env_file = ""
    for ef in _candidate_env_files(spec, env):
        vals = _parse_env_file(ef)
        if vals and not used_env_file:
            used_env_file = str(ef)
        for k, v in vals.items():
            merged.setdefault(k, v)

    base = spec.lock_base(env.get(spec.base_env) or merged.get(spec.base_env))
    model = (
        (env.get(spec.model_env) or merged.get(spec.model_env) or spec.default_model).strip()
        or spec.default_model
    )

    direct = _sanitize_api_key(env.get(spec.key_env))
    if direct:
        return LlmResolved(
            provider=spec.name,
            label=spec.label,
            api_key=direct,
            base_url=base,
            model=model,
            key_file="",
            env_file=used_env_file,
        )

    proc_kf = _expand_key_path(env.get(spec.key_file_env), home=env.get("HOME"))
    if proc_kf is not None:
        key, _err = _read_key_file(proc_kf)
        if key:
            return LlmResolved(
                provider=spec.name,
                label=spec.label,
                api_key=key,
                base_url=base,
                model=model,
                key_file=str(proc_kf),
                env_file=used_env_file,
            )

    file_key = _sanitize_api_key(merged.get(spec.key_env))
    if file_key:
        return LlmResolved(
            provider=spec.name,
            label=spec.label,
            api_key=file_key,
            base_url=base,
            model=model,
            key_file="",
            env_file=used_env_file,
        )

    file_kf = _expand_key_path(merged.get(spec.key_file_env), home=env.get("HOME"))
    if file_kf is not None:
        key, err = _read_key_file(file_kf)
        if key:
            return LlmResolved(
                provider=spec.name,
                label=spec.label,
                api_key=key,
                base_url=base,
                model=model,
                key_file=str(file_kf),
                env_file=used_env_file,
            )
        return LlmResolved(
            provider=spec.name,
            label=spec.label,
            api_key="",
            base_url=base,
            model=model,
            key_file=str(file_kf),
            env_file=used_env_file,
            error=err or _HINT_KEY_MISSING_FILE,
        )

    key, _err = _read_key_file(spec.default_key_file)
    if key:
        return LlmResolved(
            provider=spec.name,
            label=spec.label,
            api_key=key,
            base_url=base,
            model=model,
            key_file=str(spec.default_key_file),
            env_file=used_env_file,
        )

    if proc_kf is not None:
        return LlmResolved(
            provider=spec.name,
            label=spec.label,
            api_key="",
            base_url=base,
            model=model,
            key_file=str(proc_kf),
            env_file=used_env_file,
            error=_HINT_KEY_MISSING_FILE,
        )

    return LlmResolved(
        provider=spec.name,
        label=spec.label,
        api_key="",
        base_url=base,
        model=model,
        key_file="",
        env_file=used_env_file,
        error="no_key",
    )


def has_api_key(*, provider: str | None = None) -> bool:
    return bool(resolve_llm(provider=provider).api_key)


def provider_label(*, environ: dict[str, str] | None = None) -> str:
    return provider_spec(environ=environ).label


def _friendly_http_error(code: int) -> str:
    if code in (401, 403):
        return _HTTP_401_HINT
    return f"http:{code}"


def kid_safe_copy(text: str) -> bool:
    if not text or not str(text).strip():
        return False
    return _BLOCK_RE.search(str(text)) is None


def kid_safe_hit(text: str) -> str | None:
    if not text or not str(text).strip():
        return "empty"
    m = _BLOCK_RE.search(str(text))
    return m.group(0).lower() if m else None


def _extract_json_obj(text: str) -> dict[str, Any] | None:
    if not text:
        return None
    s = text.strip()
    if "</think>" in s:
        s = s.split("</think>", 1)[-1].strip()
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
        "You write kid-safe COPY and typing TARGETS for a kids typing game.\n"
        "Do NOT change scene id, hue, or energy — those are fixed by Soft.\n"
        "Return JSON only with keys:\n"
        "  title  (short cheerful English title, ≤6 words)\n"
        "  blurb  (one kind sentence, EN or EN+中文, ≤20 words)\n"
        "  art    (5-7 lines ascii/emoji art matching the scene theme)\n"
        "  targets (array of 4-8 objects: {text, hint_zh})\n"
        "    text = ASCII English/pinyin kids can type on a Latin keyboard\n"
        "    (short words or 2-4 word phrases, lowercase preferred, ≤28 chars)\n"
        "    hint_zh = optional Chinese gloss (NOT typed)\n"
        f"Locked scene id={scene.id} hue={scene.hue} energy={scene.energy}\n"
        f"Level/theme hints: {json.dumps({k: signals.get(k) for k in ('level_id','theme_scene','accuracy','streak','wpm')})}\n"
        "Rules: friendly animals, nature, space wonder, calm focus, celebration.\n"
        "FORBIDDEN: scary, violent, weapons, death, horror, adult topics.\n"
        "Avoid words like war/kill/death even inside longer words if unsure.\n"
        "Respond with a single JSON object, no markdown."
    )


def _multi_prompt(scene: Scene, signals: dict, n: int = 3) -> str:
    return (
        f"Propose {n} kid-safe typing-game COPY+TARGETS variants as JSON only.\n"
        "Soft already locked scene id/hue/energy — you only invent flavor + words.\n"
        'Return: {"candidates":[{title,blurb,art,style,feedback_en,feedback_zh,line_flavor,targets},...]}\n'
        "style: one of gentle|sparkle|party|soft|wonder\n"
        "art: prefer emoji/ascii line art (not long prose paragraphs)\n"
        "line_flavor: short EN hint for the next typing vibe (≤8 words)\n"
        "feedback_en / feedback_zh: encouraging micro lines\n"
        "targets: 4-8 items {text, hint_zh}; text = ASCII kids typing targets\n"
        "  (English or pinyin, lowercase preferred, 1-4 words, ≤28 chars each)\n"
        "  Match the level/theme; easy for ages ~5-10; no punctuation except space/\'-\n"
        f"Locked id={scene.id} hue={scene.hue} energy={scene.energy}\n"
        f"signals={json.dumps({k: signals.get(k) for k in ('accuracy','streak','wpm','rhythm_cv','theme_scene','level_id')})}\n"
        "FORBIDDEN: violence, weapons, death, horror, adult topics.\n"
        "Do not use the standalone words: war, kill, death, blood, fight.\n"
        "JSON only, no markdown. Soft mutates the game world; you only write words/copy."
    )


def _chat_url(base: str) -> str:
    b = base.rstrip("/")
    if b.endswith("/chat/completions"):
        return b
    return f"{b}/chat/completions"


def _chat_raw(
    messages: list[dict],
    *,
    timeout: float | None = None,
    temperature: float = 0.85,
    provider: str | None = None,
) -> tuple[dict[str, Any] | None, str]:
    cfg = resolve_llm(provider=provider)
    spec = provider_spec(cfg.provider)
    if not cfg.api_key:
        return None, cfg.error or "no_key"
    to = float(timeout if timeout is not None else spec.default_timeout)
    url = _chat_url(cfg.base_url)
    body: dict[str, Any] = {
        "model": cfg.model,
        "messages": messages,
        "temperature": temperature,
    }
    if spec.disable_thinking:
        body["thinking"] = {"type": "disabled"}
    req = urllib.request.Request(
        url,
        data=json.dumps(body).encode("utf-8"),
        headers={
            "Content-Type": "application/json",
            "Authorization": f"Bearer {cfg.api_key}",
            "Accept": "application/json",
        },
        method="POST",
    )
    host = cfg.base_url.replace("https://", "").replace("http://", "").split("/")[0]
    try:
        with urllib.request.urlopen(req, timeout=to) as resp:
            raw = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        try:
            exc.read()
        except Exception:  # noqa: BLE001
            pass
        return None, _friendly_http_error(int(exc.code))
    except urllib.error.URLError as exc:
        reason = exc.reason
        rname = type(reason).__name__ if reason else "URLError"
        if "timed out" in str(reason).lower() or rname in ("timeout", "TimeoutError"):
            return None, f"timeout@{host}"
        return None, f"net:{rname}"
    except TimeoutError:
        return None, f"timeout@{host}"
    except json.JSONDecodeError:
        return None, "http_json"
    except OSError as exc:
        return None, f"os:{type(exc).__name__}"

    # MiniMax base_resp auth wrapping
    base_resp = raw.get("base_resp") if isinstance(raw, dict) else None
    if isinstance(base_resp, dict):
        code = base_resp.get("status_code", 0)
        if code not in (0, "0", None):
            try:
                icode = int(code)
            except (TypeError, ValueError):
                icode = -1
            if icode in (401, 1004, 2013, 2049):
                return None, _HTTP_401_HINT
            msg = str(base_resp.get("status_msg") or code)[:28]
            if "{" in msg or '"' in msg:
                return None, f"api:{code}"
            return None, f"api:{code}:{msg}"

    try:
        msg = raw["choices"][0]["message"]
        content = msg.get("content") or ""
        # thinking models may put answer only in content after reasoning
        if not content and msg.get("reasoning_content"):
            content = str(msg.get("reasoning_content") or "")
    except (KeyError, IndexError, TypeError):
        return None, "shape:no_choices"

    data = _extract_json_obj(content or "")
    if not isinstance(data, dict):
        preview = (content or "").strip().replace("\n", " ")[:40]
        return None, f"parse:{preview or 'empty'}"
    return data, ""


def propose_copy(
    scene: Scene,
    signals: dict,
    *,
    timeout: float | None = None,
) -> dict[str, Any] | None:
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



# ASCII typing targets: letters, digits, space, and a few kid-safe punct.
_TARGET_OK_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9 \'\-]{0,27}$")


def select_targets(
    raw: Any,
    *,
    max_n: int = 8,
) -> tuple[list[dict[str, str]], str]:
    """Filter LLM target words/phrases. Returns (accepted, reject_summary).

    Never invents replacements for rejected text — drops unsafe items only.
    Soft/aura AST is untouched; these are host typing strings only.
    """
    items: list[Any] = []
    if isinstance(raw, list):
        items = raw
    elif isinstance(raw, dict):
        # allow single object or {"targets":[...]}
        if "targets" in raw:
            inner = raw.get("targets")
            items = inner if isinstance(inner, list) else []
        elif raw.get("text") or raw.get("target"):
            items = [raw]
    accepted: list[dict[str, str]] = []
    rejects = 0
    seen: set[str] = set()
    for it in items:
        if len(accepted) >= max_n:
            break
        if isinstance(it, str):
            text, hint = it.strip(), ""
        elif isinstance(it, dict):
            text = str(it.get("text") or it.get("target") or "").strip()
            hint = str(it.get("hint_zh") or it.get("hint") or "").strip()
        else:
            rejects += 1
            continue
        if not text or not _TARGET_OK_RE.match(text):
            rejects += 1
            continue
        # normalize internal whitespace; keep case mostly lower for kids
        text = " ".join(text.split())
        key = text.lower()
        if key in seen:
            continue
        if kid_safe_hit(text):
            rejects += 1
            continue
        if hint and kid_safe_hit(hint):
            hint = ""
        # drop CJK from typed text (hints may be CJK)
        if any(ord(ch) > 127 for ch in text):
            rejects += 1
            continue
        seen.add(key)
        accepted.append({"text": text, "hint_zh": hint[:24]})
    if not accepted:
        return [], "no_targets" if rejects else "empty_targets"
    reason = f"ok:{len(accepted)}" + (f"+drop:{rejects}" if rejects else "")
    return accepted, reason


def apply_copy(base: Scene, copy: dict[str, str]) -> Scene:
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


def propose_copy_multi(
    scene: Scene,
    signals: dict,
    *,
    n: int = 3,
    timeout: float | None = None,
) -> tuple[list[dict[str, Any]], str]:
    spec = provider_spec()
    to = float(timeout if timeout is not None else spec.default_timeout)
    data, err = _chat_raw(
        [
            {
                "role": "system",
                "content": "Kids game copywriter. JSON only. Never scary/violent.",
            },
            {"role": "user", "content": _multi_prompt(scene, signals, n=n)},
        ],
        timeout=to,
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
    one = propose_copy(scene, signals, timeout=min(20.0, to))
    if one:
        return [one], ""
    return [], "no_candidates"


def select_best_copy(
    candidates: list[dict[str, Any]],
    scene: Scene,
    signals: dict,
) -> tuple[dict[str, Any] | None, str]:
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
        targets, _twhy = select_targets(raw.get("targets") or raw.get("words") or [])
        if targets:
            score += 0.6 + min(0.4, 0.05 * len(targets))
        if score > best_score:
            best_score = score
            best = {
                **chosen,
                "style": style or prefer_style,
                "feedback_en": fe,
                "feedback_zh": fz,
                "line_flavor": lf,
                "targets": targets,
            }
    if best:
        return best, ""
    reason = rejects[0] if rejects else "filtered_all"
    if len(rejects) > 1:
        reason = f"{reason}+{len(rejects)-1}more"
    return None, reason[:48]


def continuous_enrich(
    scene: Scene,
    signals: dict,
    *,
    use_llm: bool | None = None,
    use_minimax: bool | None = None,  # back-compat alias
) -> tuple[Scene, dict[str, Any], str]:
    """Multi-propose → select-best. extras use llm_* (+ minimax_* aliases)."""
    if use_llm is None:
        use_llm = use_minimax if use_minimax is not None else False
    cfg0 = resolve_llm()
    label = cfg0.label
    pname = cfg0.provider
    extras: dict[str, Any] = {
        "llm_provider": pname,
        "llm_label": label,
        "llm_status": "no_key",
        "llm_error": "",
        "minimax_status": "no_key",  # alias for older TUI fields
        "minimax_error": "",
        "last_ms": 0,
        "content_hash": "",
    }

    def _set_status(st: str, err: str = "") -> None:
        extras["llm_status"] = st
        extras["llm_error"] = err
        extras["minimax_status"] = st
        extras["minimax_error"] = err

    if not cfg0.api_key:
        if cfg0.error == _HINT_KEY_MISSING_FILE:
            _set_status("fail", _HINT_KEY_MISSING_FILE)
            return rule_based_copy(scene), extras, f"copy/offline(key-file-missing)"
        _set_status("no_key")
        return rule_based_copy(scene), extras, "copy/offline(no-key)"
    if not use_llm:
        _set_status("no_key")
        return rule_based_copy(scene), extras, "copy/offline"

    _set_status("probing")
    t0 = time.monotonic()
    try:
        cands, cerr = propose_copy_multi(scene, signals)
    except Exception as exc:  # noqa: BLE001
        _set_status("fail", type(exc).__name__[:40])
        extras["last_ms"] = int((time.monotonic() - t0) * 1000)
        return rule_based_copy(scene), extras, f"copy/{pname}-fail"

    elapsed = int((time.monotonic() - t0) * 1000)
    extras["last_ms"] = elapsed
    if cerr:
        _set_status("fail", cerr[:48])
        return rule_based_copy(scene), extras, f"copy/{pname}-fail"

    chosen, sreason = select_best_copy(cands, scene, signals)
    if not chosen:
        _set_status("fail", (sreason or "empty_or_filtered")[:48])
        return rule_based_copy(scene), extras, f"copy/{pname}-fail"

    blob = json.dumps(chosen, ensure_ascii=False, sort_keys=True)
    _set_status("ok")
    targets = chosen.get("targets") if isinstance(chosen.get("targets"), list) else []
    if not targets:
        # try sibling candidates for words even if this cand had none
        for raw in cands:
            targets, _ = select_targets(raw.get("targets") or raw.get("words") or [])
            if targets:
                break
    extras.update(
        {
            "content_hash": hashlib.sha1(blob.encode("utf-8")).hexdigest()[:10],
            "style": chosen.get("style") or "gentle",
            "feedback_en": chosen.get("feedback_en") or "",
            "feedback_zh": chosen.get("feedback_zh") or "",
            "line_flavor": chosen.get("line_flavor") or "",
            "targets": targets,
            "n_propose": len(cands),
        }
    )
    return apply_copy(scene, chosen), extras, f"copy/{pname}-select-best"


# --- MiniMax-named aliases (back-compat for older imports / smoke) ---
def resolve_minimax(*, environ: dict[str, str] | None = None) -> LlmResolved:
    return resolve_llm(provider="minimax", environ=environ)


def resolve_deepseek(*, environ: dict[str, str] | None = None) -> LlmResolved:
    return resolve_llm(provider="deepseek", environ=environ)


def resolve_api_key(*, environ: dict[str, str] | None = None) -> str:
    return resolve_llm(environ=environ).api_key


def resolve_base_and_model(*, environ: dict[str, str] | None = None) -> tuple[str, str]:
    c = resolve_llm(environ=environ)
    return c.base_url, c.model
