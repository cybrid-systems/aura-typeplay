"""Thin Soft serve / oneshot bridge for typeplay.

Product brain lives in ``aura/*.aura``. This module only:
  - resolves AURA_BIN=/workspace/aura-grok/build/aura
  - starts/attaches ``aura --serve`` (sync; Soft Ready async not required)
  - pushes typing signals via observe.json
  - invokes ``run-typeplay-evolve``
  - reads scene.json Soft wrote

Offline fallback is the caller's job (host/scenes.rule_based_scene).
Soft observe ≠ Hard.
"""

from __future__ import annotations

import json
import os
import select
import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

DEFAULT_AURA_BIN = "/workspace/aura-grok/build/aura"
DEFAULT_SOCKET_DIR = "/tmp/aura-typeplay"
EVOLVE_FORM = '(begin (require "typeplay_scene" all:) (run-typeplay-evolve))'
REQUIRE_FORM = '(require "typeplay_scene" all:)'
LIVE_REQUIRE = '(require "typeplay_live" all:)'
LIVE_BOOT = '(typeplay-live-boot)'
LIVE_TICK = '(run-typeplay-live-tick)'


def repo_root() -> Path:
    return Path(__file__).resolve().parents[1]


def resolve_aura_bin(aura_bin: str | None = None) -> str:
    return aura_bin or os.environ.get("AURA_BIN") or DEFAULT_AURA_BIN


def socket_dir() -> Path:
    return Path(os.environ.get("TYPEPLAY_SOCKET_DIR") or DEFAULT_SOCKET_DIR)


def aura_path(extra: Path | None = None) -> str:
    soft_lib = Path("/workspace/aura-grok/lib")
    product = extra or (repo_root() / "aura")
    parts = [str(soft_lib), str(product)]
    for p in (os.environ.get("AURA_PATH") or "").split(":"):
        p = p.strip()
        if p:
            parts.append(p)
    # dedupe preserving order
    seen: set[str] = set()
    out: list[str] = []
    for p in parts:
        if p and p not in seen:
            seen.add(p)
            out.append(p)
    return ":".join(out)


def soft_env(*, aura_bin: str | None = None) -> dict[str, str]:
    bin_path = resolve_aura_bin(aura_bin)
    env = {
        **os.environ,
        "AURA_BIN": bin_path,
        "AURA_PATH": aura_path(),
        "AURA_SANDBOX": os.environ.get("AURA_SANDBOX") or "off",
        "AURA_PIPELINE_STRICT": os.environ.get("AURA_PIPELINE_STRICT") or "0",
        "TYPEPLAY_SOCKET_DIR": str(socket_dir()),
    }
    return env


def write_observe(signals: dict[str, Any]) -> Path:
    d = socket_dir()
    d.mkdir(parents=True, exist_ok=True)
    path = d / "observe.json"
    path.write_text(json.dumps(signals, indent=2) + "\n", encoding="utf-8")
    return path


def read_scene() -> dict[str, Any] | None:
    path = socket_dir() / "scene.json"
    if not path.is_file():
        return None
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return data if isinstance(data, dict) else None


def _parse_soft_stdout_line(s: str) -> tuple[str, dict[str, Any] | None]:
    if not s:
        return "", None
    try:
        obj = json.loads(s)
        if isinstance(obj, dict) and "status" in obj:
            return "", obj
    except json.JSONDecodeError:
        pass
    decoder = json.JSONDecoder()
    start = 0
    while True:
        brace = s.find("{", start)
        if brace < 0:
            return s, None
        try:
            obj, _end = decoder.raw_decode(s, brace)
        except json.JSONDecodeError:
            start = brace + 1
            continue
        if isinstance(obj, dict) and "status" in obj:
            return s[:brace], obj
        start = brace + 1


@dataclass
class SoftServe:
    """Host-owned ``aura --serve`` (sync). Soft Ready async not required for typeplay."""

    aura_bin: str
    proc: subprocess.Popen[str] | None = None
    booted: bool = False
    live_booted: bool = False
    last_error: str = ""

    @classmethod
    def start(cls, *, aura_bin: str | None = None, timeout_s: float = 20.0) -> SoftServe:
        bin_path = resolve_aura_bin(aura_bin)
        self = cls(aura_bin=bin_path)
        if not Path(bin_path).is_file():
            self.last_error = "aura_bin_missing"
            return self
        socket_dir().mkdir(parents=True, exist_ok=True)
        try:
            self.proc = subprocess.Popen(
                [bin_path, "--serve"],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                bufsize=1,
                env=soft_env(aura_bin=bin_path),
                cwd=str(repo_root()),
                start_new_session=True,
            )
        except OSError as exc:
            self.last_error = f"spawn:{exc}"
            return self
        # Drain Soft banner / Ready line then ping.
        ping = self.eval_line("(+ 1 1)", timeout_s=timeout_s)
        if ping.get("status") != "ok":
            self.last_error = str(ping.get("msg") or "serve_ping_fail")
            self.stop()
            return self
        req = self.eval_line(REQUIRE_FORM, timeout_s=timeout_s)
        if req.get("status") != "ok":
            self.last_error = str(req.get("msg") or "serve_require_fail")
            self.stop()
            return self
        # Soft-native live mutate workspace (fiber worldlines)
        lr = self.eval_line(LIVE_REQUIRE, timeout_s=timeout_s)
        if lr.get("status") == "ok":
            boot = self.eval_line(LIVE_BOOT, timeout_s=min(45.0, timeout_s + 20))
            if boot.get("status") != "ok":
                self.last_error = str(boot.get("msg") or "live_boot_fail")
                # keep serve for legacy evolve fallback
            else:
                self.live_booted = True
        self.booted = True
        return self

    @property
    def alive(self) -> bool:
        return self.proc is not None and self.proc.poll() is None and self.booted

    def eval_line(self, line: str, *, timeout_s: float = 15.0) -> dict[str, Any]:
        proc = self.proc
        if proc is None or proc.poll() is not None:
            return {"status": "error", "msg": "serve_dead"}
        assert proc.stdin is not None and proc.stdout is not None
        try:
            proc.stdin.write(line.rstrip("\n") + "\n")
            proc.stdin.flush()
        except OSError as exc:
            return {"status": "error", "msg": f"serve_write:{exc}"}
        display_parts: list[str] = []
        t0 = time.monotonic()
        stdout = proc.stdout
        while time.monotonic() - t0 < timeout_s:
            try:
                ready, _, _ = select.select([stdout], [], [], 0.4)
            except (ValueError, OSError):
                break
            if not ready:
                if proc.poll() is not None:
                    break
                continue
            raw = stdout.readline()
            if raw == "" and proc.poll() is not None:
                break
            s = raw.rstrip("\n")
            if not s:
                continue
            prefix, obj = _parse_soft_stdout_line(s)
            if prefix:
                display_parts.append(prefix)
            if obj is not None:
                obj = dict(obj)
                obj["display"] = "".join(display_parts) + str(obj.get("display") or "")
                return obj
            if not prefix:
                display_parts.append(s)
        return {
            "status": "error",
            "msg": "serve_timeout",
            "display": "".join(display_parts),
        }

    def evolve(self, *, timeout_s: float = 20.0) -> dict[str, Any]:
        # Module already required at boot; re-invoke entry.
        r = self.eval_line("(run-typeplay-evolve)", timeout_s=timeout_s)
        scene = read_scene()
        ok = r.get("status") == "ok" and isinstance(scene, dict) and scene.get("source") == "soft"
        return {
            "ok": ok,
            "via": "serve",
            "raw": r,
            "scene": scene,
            "soft_observe_ne_hard": True,
        }

    def stop(self) -> None:
        proc = self.proc
        self.booted = False
        self.proc = None
        if proc is None:
            return
        try:
            if proc.poll() is None:
                proc.terminate()
                try:
                    proc.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    proc.kill()
        except OSError:
            pass



def live_tick_serve(serve: SoftServe, *, timeout_s: float = 60.0) -> dict[str, Any]:
    """One Soft live-mutate tick on persistent serve (fiber worldlines → land)."""
    if serve is None or not serve.alive:
        return {"ok": False, "via": "serve", "reason": "serve_dead", "scene": None}
    if not getattr(serve, "live_booted", False):
        serve.eval_line(LIVE_REQUIRE, timeout_s=min(30.0, timeout_s))
        b = serve.eval_line(LIVE_BOOT, timeout_s=min(45.0, timeout_s))
        if b.get("status") == "ok":
            serve.live_booted = True
    r = serve.eval_line(LIVE_TICK, timeout_s=timeout_s)
    scene = read_scene()
    ok = r.get("status") == "ok" and isinstance(scene, dict) and bool(
        scene.get("soft_mutate") or scene.get("source") == "soft-live-mutate"
    )
    return {
        "ok": ok,
        "via": "serve-live",
        "raw": r,
        "scene": scene,
        "soft_observe_ne_hard": True,
        "soft_mutate": True,
    }


def live_tick_oneshot(*, timeout_s: float = 90.0, aura_bin: str | None = None) -> dict[str, Any]:
    """Oneshot Soft live boot+tick (slower; serve preferred)."""
    bin_path = resolve_aura_bin(aura_bin)
    if not Path(bin_path).is_file():
        return {"ok": False, "via": "oneshot-live", "reason": "aura_bin_missing", "scene": None}
    socket_dir().mkdir(parents=True, exist_ok=True)
    form = (
        '(begin (require "typeplay_live" all:) '
        "(typeplay-live-boot) (run-typeplay-live-tick))"
    )
    try:
        proc = subprocess.run(
            [bin_path, "-e", form],
            capture_output=True,
            text=True,
            timeout=timeout_s,
            check=False,
            env=soft_env(aura_bin=bin_path),
            cwd=str(repo_root()),
            start_new_session=True,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {
            "ok": False,
            "via": "oneshot-live",
            "reason": f"exc:{type(exc).__name__}",
            "scene": None,
            "soft_mutate": True,
        }
    scene = read_scene()
    stdout = (proc.stdout or "").strip()
    ok = ("TYPEPLAY_LIVE ok=true" in stdout) and isinstance(scene, dict)
    return {
        "ok": ok,
        "via": "oneshot-live",
        "returncode": proc.returncode,
        "stdout": stdout[:500],
        "stderr": (proc.stderr or "")[:200],
        "scene": scene,
        "soft_observe_ne_hard": True,
        "soft_mutate": True,
    }


def evolve_live(
    signals: dict[str, Any],
    *,
    serve: SoftServe | None = None,
    aura_bin: str | None = None,
) -> dict[str, Any]:
    """Preferred Soft path: live mutate tick. Falls back to legacy evolve."""
    write_observe(signals)
    if serve is not None and serve.alive:
        got = live_tick_serve(serve)
        if got.get("ok"):
            return got
        # serve live failed → oneshot live once
        one = live_tick_oneshot(aura_bin=aura_bin or serve.aura_bin)
        if one.get("ok"):
            one["via"] = f"serve_live_fail→{one.get('via')}"
            return one
    else:
        one = live_tick_oneshot(aura_bin=aura_bin)
        if one.get("ok"):
            return one
    # last resort: legacy score-only evolve (still Soft .aura, not Python brain)
    return evolve_with_soft(signals, serve=serve, aura_bin=aura_bin)


def evolve_oneshot(*, timeout_s: float = 40.0, aura_bin: str | None = None) -> dict[str, Any]:
    bin_path = resolve_aura_bin(aura_bin)
    if not Path(bin_path).is_file():
        return {"ok": False, "via": "oneshot", "reason": "aura_bin_missing", "scene": None}
    socket_dir().mkdir(parents=True, exist_ok=True)
    try:
        proc = subprocess.run(
            [bin_path, "-e", EVOLVE_FORM],
            capture_output=True,
            text=True,
            timeout=timeout_s,
            check=False,
            env=soft_env(aura_bin=bin_path),
            cwd=str(repo_root()),
            start_new_session=True,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return {
            "ok": False,
            "via": "oneshot",
            "reason": f"exc:{type(exc).__name__}",
            "scene": None,
            "soft_observe_ne_hard": True,
        }
    scene = read_scene()
    stdout = (proc.stdout or "").strip()
    ok = ("TYPEPLAY_EVOLVE ok=true" in stdout) and isinstance(scene, dict)
    return {
        "ok": ok,
        "via": "oneshot",
        "returncode": proc.returncode,
        "stdout": stdout[:400],
        "stderr": (proc.stderr or "")[:200],
        "scene": scene,
        "soft_observe_ne_hard": True,
    }


def evolve_with_soft(
    signals: dict[str, Any],
    *,
    serve: SoftServe | None = None,
    aura_bin: str | None = None,
) -> dict[str, Any]:
    """Push signals → Soft evolve → scene dict. Caller falls back offline on ok=False."""
    write_observe(signals)
    if serve is not None and serve.alive:
        got = serve.evolve()
        if got.get("ok"):
            return got
        # serve failed this round — try oneshot once
        one = evolve_oneshot(aura_bin=aura_bin or serve.aura_bin)
        one["via"] = f"serve_fail→{one.get('via')}"
        return one
    return evolve_oneshot(aura_bin=aura_bin)


def doctor() -> dict[str, Any]:
    bin_path = resolve_aura_bin()
    soft_ok = Path(bin_path).is_file() and os.access(bin_path, os.X_OK)
    out: dict[str, Any] = {
        "AURA_BIN": bin_path,
        "aura_bin_ok": soft_ok,
        "AURA_PATH": aura_path(),
        "TYPEPLAY_SOCKET_DIR": str(socket_dir()),
        "soft_observe_ne_hard": True,
    }
    if not soft_ok:
        out["evolve_smoke"] = "skip_no_bin"
        return out
    write_observe(
        {
            "accuracy": 0.92,
            "wpm": 22.0,
            "streak": 8,
            "best_streak": 8,
            "chars_done": 24,
            "wrong": 2,
            "rhythm_cv": 0.45,
        }
    )
    got = evolve_oneshot(timeout_s=45.0)
    out["evolve_smoke"] = "ok" if got.get("ok") else "fail"
    out["scene_id"] = (got.get("scene") or {}).get("id")
    out["via"] = got.get("via")
    return out
