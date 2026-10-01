"""Background Soft + MiniMax auto-evolve — never blocks the typing TUI.

Soft multi-propose + select-best owns scene id/hue/energy.
MiniMax continuously proposes copy/style/feedback; host thin select-best.
Offline fallback when Soft/key unavailable.
"""

from __future__ import annotations

import json
import os
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Callable

from host import soft_bridge
from host.minimax_scene import continuous_enrich, has_api_key
from host.scenes import SCENES, Scene, apply_soft_scene, rule_based_scene


@dataclass
class EvolveSnapshot:
    scene: Scene
    source: str = "offline"
    style: dict[str, Any] = field(default_factory=dict)
    feedback_en: str = ""
    feedback_zh: str = ""
    line_flavor: str = ""
    soft_ok: bool = False
    updated_at: float = 0.0


class EvolveWorker:
    """Daemon thread: Soft evolve → MiniMax multi-propose → publish snapshot."""

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

    @property
    def busy(self) -> bool:
        return self._busy

    def snapshot(self) -> EvolveSnapshot:
        with self._lock:
            return EvolveSnapshot(
                scene=self._snap.scene,
                source=self._snap.source,
                style=dict(self._snap.style),
                feedback_en=self._snap.feedback_en,
                feedback_zh=self._snap.feedback_zh,
                line_flavor=self._snap.line_flavor,
                soft_ok=self._snap.soft_ok,
                updated_at=self._snap.updated_at,
            )

    def notify_signals(self) -> None:
        """Typing just updated observe — nudge sooner (non-blocking)."""
        self._kick.set()

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._loop, name="typeplay-evolve", daemon=True)
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
        # Drop JSON for Soft/tools
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
                        "source": snap.source,
                    },
                    indent=2,
                    ensure_ascii=False,
                )
                + "\n",
                encoding="utf-8",
            )
        except OSError:
            pass

    def _select_soft_scene(self, signals: dict[str, Any]) -> tuple[Scene, str, bool, dict]:
        style: dict[str, Any] = {}
        if self.mode in ("soft", "minimax"):
            got = soft_bridge.evolve_with_soft(signals, serve=self.soft)
            applied = apply_soft_scene(got.get("scene"), signals) if got.get("ok") else None
            if applied:
                scene, _ = applied
                raw = got.get("scene") or {}
                if isinstance(raw.get("style"), dict):
                    style = raw["style"]
                return scene, f"soft/{got.get('via')}", True, style
        # offline / Soft down
        theme = str(signals.get("theme_scene") or "")
        if theme in SCENES and float(signals.get("accuracy", 1)) >= 0.75:
            return SCENES[theme], "offline/theme", False, style
        return rule_based_scene(signals), "offline/rules", False, style

    def _want_minimax(self) -> bool:
        if not has_api_key():
            return False
        if self.mode == "minimax":
            return True
        if self.mode == "soft":
            # Soft mode: continuous MiniMax copy when key present (auto chat evolve)
            return os.environ.get("TYPEPLAY_MINIMAX_COPY", "1").strip() not in (
                "0",
                "false",
                "no",
            )
        return False

    def _round(self) -> None:
        self._busy = True
        try:
            signals = self.signals_fn()
            soft_bridge.write_observe(signals)
            scene, source, soft_ok, style = self._select_soft_scene(signals)
            scene2, extras, tag = continuous_enrich(
                scene, signals, use_minimax=self._want_minimax()
            )
            if extras.get("style"):
                style = {**style, "burst": extras["style"], "mood": style.get("mood", "")}
            snap = EvolveSnapshot(
                scene=scene2,
                source=f"{source}+{tag}",
                style=style,
                feedback_en=str(extras.get("feedback_en") or ""),
                feedback_zh=str(extras.get("feedback_zh") or ""),
                line_flavor=str(extras.get("line_flavor") or ""),
                soft_ok=soft_ok,
                updated_at=time.monotonic(),
            )
            self._publish(snap)
        finally:
            self._busy = False

    def _loop(self) -> None:
        # Continuous background Soft+MiniMax chat evolve while playing.
        while not self._stop.is_set():
            try:
                self._round()
            except Exception:  # noqa: BLE001
                pass
            if self._stop.is_set():
                break
            # Sleep between rounds; typing can kick for a sooner refresh.
            self._kick.wait(timeout=self.interval_s)
            self._kick.clear()
