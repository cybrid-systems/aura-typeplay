"""Typeplay Textual TUI — Soft observe-steer scene evolve; offline fallback.

Soft binary: AURA_BIN=/workspace/aura-grok/build/aura
Product brain: aura/*.aura — Soft observe ≠ Hard.
"""

from __future__ import annotations

import os
from pathlib import Path

from textual import events
from textual.app import App, ComposeResult
from textual.containers import Horizontal
from textual.widgets import Footer, Header, Static

from host.lines import next_line
from host.metrics import SessionScore
from host.minimax_scene import propose_or_none
from host.scenes import Scene, apply_soft_scene, rule_based_scene, scene_from_proposal
from host import soft_bridge

AURA_BIN = soft_bridge.resolve_aura_bin()
SOCKET_DIR = soft_bridge.socket_dir()


class MetricsPanel(Static):
    """Live accuracy / WPM / streak."""

    def show(self, score: SessionScore) -> None:
        s = score.observe_signals()
        self.update(
            f"[b]Accuracy[/] {s['accuracy']*100:5.1f}%   "
            f"[b]WPM[/] {s['wpm']:5.1f}   "
            f"[b]Streak[/] {s['streak']:3d}   "
            f"[b]Best[/] {s['best_streak']:3d}   "
            f"[dim]rhythm_cv={s['rhythm_cv']}[/]"
        )


class TargetPanel(Static):
    """Target line with typed / remaining highlighting."""

    def show(self, target: str, typed_len: int, last_ok: bool | None) -> None:
        done = target[:typed_len]
        rest = target[typed_len:]
        caret = "[blink]▍[/]"
        if last_ok is False and typed_len > 0:
            done = target[: typed_len - 1] + f"[red bold]{target[typed_len - 1]}[/]"
        self.update(
            f"[b]Type this:[/]\n\n"
            f"  [green]{done}[/]{caret}[white]{rest}[/]"
        )


class ScenePanel(Static):
    """ANSI / emoji scene that evolves with Soft/host params."""

    def show(self, scene: Scene, source: str) -> None:
        hue = scene.hue if scene.hue in {
            "green", "blue", "magenta", "yellow", "cyan", "white", "red"
        } else "cyan"
        art = scene.art.strip("\n")
        self.update(
            f"[b {hue}]{scene.title}[/]  "
            f"[dim]({scene.id} · energy={scene.energy:.2f} · via {source})[/]\n\n"
            f"[{hue}]{art}[/]"
        )


class TypeplayApp(App):
    """Kids typing host — Soft serve observe-steer when mode=soft."""

    CSS = """
    Screen { layout: vertical; }
    #metrics { height: 3; padding: 0 1; border: solid $accent; }
    #main { height: 1fr; }
    #target { width: 3fr; padding: 1 2; border: tall $primary; }
    #scene { width: 2fr; padding: 1 1; border: tall $secondary; }
    #hint { height: 3; padding: 0 1; color: $text-muted; }
    """

    BINDINGS = [
        ("ctrl+c", "quit", "Quit"),
        ("ctrl+n", "skip", "Skip line"),
        ("ctrl+e", "evolve", "Evolve scene"),
    ]

    TITLE = "aura-typeplay"
    SUB_TITLE = "kids typing · Soft observe · scene evolve"

    def __init__(self) -> None:
        super().__init__()
        self.mode = os.environ.get("TYPEPLAY_MODE", "offline").lower()
        self.score = SessionScore()
        self.line_index = 0
        self.target = next_line(0)
        self.typed_len = 0
        self.last_ok: bool | None = None
        self.scene: Scene = rule_based_scene(self.score.observe_signals())
        self.scene_source = "offline"
        self._evolve_every = 8
        self._soft: soft_bridge.SoftServe | None = None

    def compose(self) -> ComposeResult:
        yield Header()
        yield MetricsPanel(id="metrics")
        with Horizontal(id="main"):
            yield TargetPanel(id="target")
            yield ScenePanel(id="scene")
        soft_note = "serve" if self._soft and self._soft.alive else self.mode
        yield Static(
            "Ctrl+N skip · Ctrl+E evolve · Ctrl+C quit  ·  "
            f"mode={self.mode}  ·  soft={soft_note}  ·  "
            f"AURA_BIN={AURA_BIN}",
            id="hint",
        )
        yield Footer()

    def on_mount(self) -> None:
        if self.mode == "soft":
            self._soft = soft_bridge.SoftServe.start()
            if not self._soft.alive:
                # Soft down → keep running offline; hint shows fallback.
                self.scene_source = f"offline(soft_down:{self._soft.last_error})"
        self._refresh_all()
        self._push_observe()

    def on_unmount(self) -> None:
        if self._soft is not None:
            self._soft.stop()
            self._soft = None

    def _refresh_all(self) -> None:
        self.query_one("#metrics", MetricsPanel).show(self.score)
        self.query_one("#target", TargetPanel).show(
            self.target, self.typed_len, self.last_ok
        )
        self.query_one("#scene", ScenePanel).show(self.scene, self.scene_source)

    def _advance_line(self) -> None:
        self.line_index += 1
        self.target = next_line(self.line_index)
        self.typed_len = 0
        self.last_ok = None

    def _push_observe(self, signals: dict | None = None) -> None:
        try:
            soft_bridge.write_observe(signals or self.score.observe_signals())
        except OSError:
            pass

    def _apply_offline(self, signals: dict) -> None:
        self.scene = rule_based_scene(signals)
        self.scene_source = "offline"

    def _maybe_evolve(self, force: bool = False) -> None:
        if not force and self.score.chars_done % self._evolve_every != 0:
            return
        signals = self.score.observe_signals()
        self._push_observe(signals)

        # Soft mode: Soft product brain steers scene.
        if self.mode == "soft":
            got = soft_bridge.evolve_with_soft(signals, serve=self._soft)
            applied = apply_soft_scene(got.get("scene"), signals)
            if got.get("ok") and applied:
                self.scene, self.scene_source = applied
                via = got.get("via") or "soft"
                self.scene_source = f"soft/{via}"
                self._refresh_all()
                return
            # Soft down / fail → offline fallback
            self._apply_offline(signals)
            self.scene_source = f"offline(soft_fallback:{got.get('via')})"
            self._refresh_all()
            return

        # MiniMax propose (host thin); Soft/host select — no gold fixes.
        if self.mode == "minimax":
            proposal = propose_or_none(signals)
            if proposal:
                scene = scene_from_proposal(proposal)
                if scene:
                    self.scene = scene
                    self.scene_source = "minimax"
                    self._refresh_all()
                    return

        self._apply_offline(signals)
        self._refresh_all()

    def on_key(self, event: events.Key) -> None:
        if event.character is None or event.is_control:
            return
        ch = event.character
        if self.typed_len >= len(self.target):
            return
        expected = self.target[self.typed_len]
        ok = ch == expected
        self.score.record_key(ok)
        if ok:
            self.typed_len += 1
            self.last_ok = True
            if self.typed_len >= len(self.target):
                self._advance_line()
        else:
            self.last_ok = False
        self._refresh_all()
        self._maybe_evolve()

    def action_skip(self) -> None:
        self._advance_line()
        self._refresh_all()

    def action_evolve(self) -> None:
        self._maybe_evolve(force=True)

    def action_quit(self) -> None:
        if self._soft is not None:
            self._soft.stop()
            self._soft = None
        self.exit()


def main() -> None:
    TypeplayApp().run()


if __name__ == "__main__":
    main()
