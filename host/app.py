"""Typeplay Textual TUI — target line, keystrokes, live metrics, evolving scene.

v0 runs without Soft: local metrics → rule-based (or MiniMax) scene.
Later wire-up: AURA_BIN=/workspace/aura-grok/build/aura
"""

from __future__ import annotations

import os
from pathlib import Path

from textual import events
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Footer, Header, Static

from host.lines import next_line
from host.metrics import SessionScore
from host.minimax_scene import propose_or_none
from host.scenes import Scene, rule_based_scene, scene_from_proposal

# Soft binary path for later wire-up (v0 does not invoke Soft).
AURA_BIN = os.environ.get("AURA_BIN", "/workspace/aura-grok/build/aura")
SOCKET_DIR = Path(os.environ.get("TYPEPLAY_SOCKET_DIR", "/tmp/aura-typeplay"))


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
            # flash last wrong char
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
    """Kids typing host — Soft observe hooks documented, not required for v0."""

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
        self.score = SessionScore()
        self.line_index = 0
        self.target = next_line(0)
        self.typed_len = 0
        self.last_ok: bool | None = None
        self.scene: Scene = rule_based_scene(self.score.observe_signals())
        self.scene_source = "offline"
        self._evolve_every = 8  # chars between auto-evolve attempts

    def compose(self) -> ComposeResult:
        yield Header()
        yield MetricsPanel(id="metrics")
        with Horizontal(id="main"):
            yield TargetPanel(id="target")
            yield ScenePanel(id="scene")
        yield Static(
            "Ctrl+N skip · Ctrl+E evolve scene · Ctrl+C quit  ·  "
            f"mode={os.environ.get('TYPEPLAY_MODE', 'offline')}  ·  "
            f"AURA_BIN={AURA_BIN}",
            id="hint",
        )
        yield Footer()

    def on_mount(self) -> None:
        self._refresh_all()
        self._write_observe_stub()

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

    def _maybe_evolve(self, force: bool = False) -> None:
        if not force and self.score.chars_done % self._evolve_every != 0:
            return
        signals = self.score.observe_signals()
        self._write_observe_stub(signals)
        proposal = propose_or_none(signals)
        if proposal:
            scene = scene_from_proposal(proposal)
            if scene:
                self.scene = scene
                self.scene_source = "minimax"
                self._refresh_all()
                return
        self.scene = rule_based_scene(signals)
        self.scene_source = "offline"
        self._refresh_all()

    def _write_observe_stub(self, signals: dict | None = None) -> None:
        """Documented socket Soft will serve later — thin JSON drop for v0."""
        try:
            SOCKET_DIR.mkdir(parents=True, exist_ok=True)
            payload = signals or self.score.observe_signals()
            path = SOCKET_DIR / "observe.json"
            import json

            path.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
            scene_path = SOCKET_DIR / "scene.json"
            scene_path.write_text(
                json.dumps(
                    {
                        "id": self.scene.id,
                        "title": self.scene.title,
                        "hue": self.scene.hue,
                        "energy": self.scene.energy,
                        "source": self.scene_source,
                    },
                    indent=2,
                )
                + "\n",
                encoding="utf-8",
            )
        except OSError:
            pass

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
        self.exit()


def main() -> None:
    TypeplayApp().run()


if __name__ == "__main__":
    main()
