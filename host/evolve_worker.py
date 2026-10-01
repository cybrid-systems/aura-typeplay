"""Background Soft LIVE mutate + optional LLM copy — thin host display.

Soft owns product brain: persistent serve → fiber worldlines mutate:rebind
scene AST attrs → select-best → scene.json (compile_epoch / live_tick).
Python does NOT invent scene evolution — it displays Soft landings.

LLM copy (DeepSeek Flash default; TYPEPLAY_LLM=minimax optional):
  no_key | probing | ok (last_ms + hash) | fail (short error).
"""

from __future__ import annotations

import json
import os
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable

from host import soft_bridge
from host.llm_copy import continuous_enrich, has_api_key, active_provider
from host.scenes import SCENES, Scene, apply_soft_scene, rule_based_scene


@dataclass
class EvolveSnapshot:
    scene: Scene
    source: str = "offline"
    style: dict[str, Any] = field(default_factory=dict)
    feedback_en: str = ""
    feedback_zh: str = ""
    line_flavor: str = ""
    targets: list = field(default_factory=list)  # DeepSeek typing words
    soft_ok: bool = False
    soft_mutate: bool = False
    compile_epoch: int = 0
    live_tick: int = 0
    minimax_status: str = "no_key"  # no_key | probing | ok | fail (LLM chip; name kept)
    minimax_error: str = ""
    minimax_last_ms: int = 0
    minimax_hash: str = ""
    llm_provider: str = ""  # deepseek | minimax
    updated_at: float = 0.0


class EvolveWorker:
    """Daemon: Soft live-mutate tick → optional MiniMax → publish snapshot."""

    def __init__(
        self,
        *,
        mode: str = "soft",
        interval_s: float = 4.0,
        soft: soft_bridge.SoftServe | None = None,
        signals_fn: Callable[[], dict[str, Any]] | None = None,
    ) -> None:
        self.mode = mode
        self.interval_s = interval_s
        self.soft = soft
        self.signals_fn = signals_fn or (lambda: {})
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._lock = threading.Lock()
        self._snap = EvolveSnapshot(scene=SCENES.get("forest", rule_based_scene({})))
        self._busy = False
        self._kick = threading.Event()
        # After MiniMax fail, keep FAIL chip visible; skip re-probe for a bit
        self._mm_cooldown_until = 0.0
        self._mm_last_fail = ""

    @property
    def busy(self) -> bool:
        return self._busy

    def snapshot(self) -> EvolveSnapshot:
        with self._lock:
            s = self._snap
            return EvolveSnapshot(
                scene=s.scene,
                source=s.source,
                style=dict(s.style),
                feedback_en=s.feedback_en,
                feedback_zh=s.feedback_zh,
                line_flavor=s.line_flavor,
                targets=list(s.targets or []),
                soft_ok=s.soft_ok,
                soft_mutate=s.soft_mutate,
                compile_epoch=s.compile_epoch,
                live_tick=s.live_tick,
                minimax_status=s.minimax_status,
                minimax_error=s.minimax_error,
                minimax_last_ms=s.minimax_last_ms,
                minimax_hash=s.minimax_hash,
                llm_provider=s.llm_provider or active_provider(),
                updated_at=s.updated_at,
            )

    def notify_signals(self) -> None:
        self._kick.set()

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(
            target=self._loop, name="typeplay-evolve", daemon=True
        )
        self._thread.start()

    def stop(self) -> None:
        self._stop.set()
        self._kick.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)
        self._thread = None

    def _publish(self, snap: EvolveSnapshot) -> None:
        with self._lock:
            self._snap = snap
        try:
            d = soft_bridge.socket_dir()
            d.mkdir(parents=True, exist_ok=True)
            (d / "style.json").write_text(
                json.dumps(snap.style, indent=2) + "\n", encoding="utf-8"
            )
            (d / "feedback.json").write_text(
                json.dumps(
                    {
                        "en": snap.feedback_en,
                        "zh": snap.feedback_zh,
                        "line_flavor": snap.line_flavor,
                        "targets": snap.targets,
                        "note": "DeepSeek=copy+words; Soft=mutate AST",
                        "source": snap.source,
                        "compile_epoch": snap.compile_epoch,
                        "live_tick": snap.live_tick,
                        "soft_mutate": snap.soft_mutate,
                        "llm_provider": getattr(snap, "llm_provider", "") or active_provider(),
                        "llm_status": snap.minimax_status,
                        "llm_error": snap.minimax_error,
                        "minimax_status": snap.minimax_status,
                        "minimax_error": snap.minimax_error,
                        "last_ms": snap.minimax_last_ms,
                        "content_hash": snap.minimax_hash,
                    },
                    indent=2,
                    ensure_ascii=False,
                )
                + "\n",
                encoding="utf-8",
            )
        except OSError:
            pass

    def _want_llm_copy(self) -> bool:
        if not has_api_key():
            return False
        if self.mode in ("minimax", "deepseek"):
            return True
        if self.mode == "soft":
            # TYPEPLAY_LLM_COPY preferred; TYPEPLAY_MINIMAX_COPY kept as alias
            for key in ("TYPEPLAY_LLM_COPY", "TYPEPLAY_MINIMAX_COPY"):
                raw = os.environ.get(key)
                if raw is not None and raw.strip() != "":
                    return raw.strip().lower() not in ("0", "false", "no")
            return True  # default on when key resolves
        return False

    def _soft_live(self, signals: dict[str, Any]) -> tuple[Scene, str, bool, dict, dict]:
        """Soft live-mutate (preferred). Returns scene, source, ok, style, raw."""
        style: dict[str, Any] = {}
        raw: dict[str, Any] = {}
        if self.mode not in ("soft", "minimax", "deepseek"):
            theme = str(signals.get("theme_scene") or "")
            if theme in SCENES and float(signals.get("accuracy", 1)) >= 0.75:
                return SCENES[theme], "offline/theme", False, style, raw
            return rule_based_scene(signals), "offline/rules", False, style, raw

        got = soft_bridge.evolve_live(signals, serve=self.soft)
        raw = got.get("scene") or {}
        applied = apply_soft_scene(raw, signals) if got.get("ok") else None
        if applied:
            scene, tag = applied
            if isinstance(raw.get("style"), dict):
                style = dict(raw["style"])
            # Soft-native feedback until LLM copy overlays
            via = got.get("via") or "live"
            return scene, f"soft-live/{via}", True, style, raw
        # Soft down — honest offline display (not Python inventing Soft)
        why = str(got.get("reason") or "down")[:28]
        theme = str(signals.get("theme_scene") or "")
        tag = f"offline(soft_down:{why})"
        if theme in SCENES:
            return SCENES[theme], tag, False, style, raw
        return rule_based_scene(signals), tag, False, style, raw

    def _round(self) -> None:
        self._busy = True
        mm_status = "no_key"
        mm_err = ""
        mm_ms = 0
        mm_hash = ""
        try:
            signals = self.signals_fn()
            soft_bridge.write_observe(signals)
            scene, source, soft_ok, style, raw = self._soft_live(signals)

            fb_en = str(raw.get("feedback_en") or "")
            fb_zh = str(raw.get("feedback_zh") or "")
            line_flavor = ""
            targets: list = []
            tag = "copy/offline"

            want_mm = self._want_llm_copy()
            now = time.monotonic()
            on_cooldown = now < self._mm_cooldown_until
            if not has_api_key():
                mm_status = "no_key"
                tag = "copy/offline(no-key)"
                scene2 = scene
            elif want_mm and on_cooldown:
                # Keep last FAIL visible instead of perpetual probing…
                mm_status = "fail"
                mm_err = self._mm_last_fail or "cooldown"
                tag = f"copy/{active_provider()}-cooldown"
                scene2 = scene
            elif want_mm:
                mm_status = "probing"
                # Publish probing so TUI chip updates mid-round
                self._publish(
                    EvolveSnapshot(
                        scene=scene,
                        source=source + "+probing",
                        style=style,
                        feedback_en=fb_en,
                        feedback_zh=fb_zh,
                        soft_ok=soft_ok,
                        soft_mutate=bool(raw.get("soft_mutate")),
                        compile_epoch=int(raw.get("compile_epoch") or 0),
                        live_tick=int(raw.get("live_tick") or 0),
                        minimax_status="probing",
                        llm_provider=active_provider(),
                        updated_at=time.monotonic(),
                    )
                )
                scene2, extras, tag = continuous_enrich(
                    scene, signals, use_llm=True
                )
                mm_status = str(extras.get("minimax_status") or "fail")
                mm_err = str(extras.get("minimax_error") or "")
                mm_ms = int(extras.get("last_ms") or 0)
                mm_hash = str(extras.get("content_hash") or "")
                if mm_status == "ok":
                    self._mm_cooldown_until = 0.0
                    self._mm_last_fail = ""
                    if extras.get("feedback_en"):
                        fb_en = str(extras["feedback_en"])
                    if extras.get("feedback_zh"):
                        fb_zh = str(extras["feedback_zh"])
                    line_flavor = str(extras.get("line_flavor") or "")
                    targets = list(extras.get("targets") or [])
                    if extras.get("style"):
                        style = {
                            **style,
                            "burst": extras["style"],
                            "mood": style.get("mood", ""),
                        }
                else:
                    self._mm_last_fail = mm_err or "fail"
                    # 25s cool-down so chip shows FAIL, not endless probing
                    self._mm_cooldown_until = time.monotonic() + 25.0
            else:
                scene2, extras, tag = continuous_enrich(
                    scene, signals, use_llm=False
                )
                mm_status = "no_key"

            snap = EvolveSnapshot(
                scene=scene2,
                source=f"{source}+{tag}",
                style=style,
                feedback_en=fb_en,
                feedback_zh=fb_zh,
                line_flavor=line_flavor,
                targets=targets,
                soft_ok=soft_ok,
                soft_mutate=bool(raw.get("soft_mutate")),
                compile_epoch=int(raw.get("compile_epoch") or 0),
                live_tick=int(raw.get("live_tick") or 0),
                minimax_status=mm_status,
                minimax_error=mm_err,
                minimax_last_ms=mm_ms,
                minimax_hash=mm_hash,
                llm_provider=active_provider(),
                updated_at=time.monotonic(),
            )
            self._publish(snap)
        except Exception as exc:  # noqa: BLE001
            # Never leave the chip stuck on probing…
            self._mm_last_fail = type(exc).__name__[:40]
            self._mm_cooldown_until = time.monotonic() + 25.0
            with self._lock:
                prev = self._snap
            self._publish(
                EvolveSnapshot(
                    scene=prev.scene,
                    source=(prev.source or "offline") + "+mm_exc",
                    style=dict(prev.style),
                    feedback_en=prev.feedback_en,
                    feedback_zh=prev.feedback_zh,
                    soft_ok=prev.soft_ok,
                    soft_mutate=prev.soft_mutate,
                    compile_epoch=prev.compile_epoch,
                    live_tick=prev.live_tick,
                    minimax_status="fail",
                    minimax_error=self._mm_last_fail,
                    updated_at=time.monotonic(),
                )
            )
        finally:
            self._busy = False

    def _loop(self) -> None:
        while not self._stop.is_set():
            try:
                self._round()
            except Exception:  # noqa: BLE001 — _round already clears probing
                pass
            if self._stop.is_set():
                break
            self._kick.wait(timeout=self.interval_s)
            self._kick.clear()
