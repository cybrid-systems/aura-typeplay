"""Typeplay Textual TUI — Soft observe-steer scene evolve; offline fallback.

Soft binary: AURA_BIN=/workspace/aura-grok/build/aura
Product brain: aura/*.aura — Soft observe ≠ Hard.
Levels: host/levels.py (bilingual EN + 中文 hints).
"""

from __future__ import annotations

import os

from textual import events
from textual.app import App, ComposeResult
from textual.containers import Horizontal
from textual.widgets import Footer, Header, Static

from host.levels import LevelProgress
from host.metrics import SessionScore
from host.minimax_scene import enrich_scene_copy, has_api_key
from host.scenes import Scene, apply_soft_scene, rule_based_scene
from host import soft_bridge

AURA_BIN = soft_bridge.resolve_aura_bin()
SOCKET_DIR = soft_bridge.socket_dir()


class MetricsPanel(Static):
    """Live accuracy / WPM / streak + level."""

    def show(self, score: SessionScore, progress: LevelProgress) -> None:
        s = score.observe_signals()
        st = progress.status()
        self.update(
            f"[b]Lv{st['level_idx']+1}[/] {st['level_title_en']} "
            f"[dim]({st['level_title_zh']})[/]  "
            f"ok {st['ok_lines']}/{st['lines_to_advance']}  ·  "
            f"[b]Acc[/] {s['accuracy']*100:5.1f}%  "
            f"[b]WPM[/] {s['wpm']:5.1f}  "
            f"[b]Streak[/] {s['streak']:3d}  "
            f"[dim]rhythm={s['rhythm_cv']}[/]"
        )


class TargetPanel(Static):
    """Target line with typed / remaining + Chinese hint."""

    def show(
        self,
        target: str,
        typed_len: int,
        last_ok: bool | None,
        hint_zh: str,
        progress: LevelProgress,
    ) -> None:
        done = target[:typed_len]
        rest = target[typed_len:]
        caret = "[blink]▍[/]"
        if last_ok is False and typed_len > 0:
            done = target[: typed_len - 1] + f"[red bold]{target[typed_len - 1]}[/]"
        zh = f"  [cyan]中文[/] {hint_zh}" if hint_zh else ""
        lv = progress.level
        self.update(
            f"[b]Level[/] {lv.title_en} / {lv.title_zh}  "
            f"[dim]theme→{lv.theme_scene}[/]\n"
            f"[b]Type this:[/]{zh}\n\n"
            f"  [green]{done}[/]{caret}[white]{rest}[/]"
        )


class ScenePanel(Static):
    """ANSI / emoji scene that evolves with Soft/host params."""

    def show(self, scene: Scene, source: str) -> None:
        hue = scene.hue if scene.hue in {
            "green", "blue", "magenta", "yellow", "cyan", "white", "red"
        } else "cyan"
        art = scene.art.strip("\n")
        blurb = f"\n[i]{scene.blurb}[/]" if scene.blurb else ""
        self.update(
            f"[b {hue}]{scene.title}[/]  "
            f"[dim]({scene.id} · energy={scene.energy:.2f} · via {source})[/]"
            f"{blurb}\n\n"
            f"[{hue}]{art}[/]"
        )


class TypeplayApp(App):
    """Kids typing host — levels + Soft serve observe-steer when mode=soft."""

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
    SUB_TITLE = "kids typing · levels · Soft observe · scene evolve"

    def __init__(self) -> None:
        super().__init__()
        self.mode = os.environ.get("TYPEPLAY_MODE", "offline").lower()
        self.score = SessionScore()
        self.progress = LevelProgress()
        self.target = self.progress.target_text()
        self.typed_len = 0
        self.line_correct = 0
        self.line_wrong = 0
        self.last_ok: bool | None = None
        self.scene: Scene = rule_based_scene(self._signals())
        self.scene_source = "offline"
        self._evolve_every = 8
        self._soft: soft_bridge.SoftServe | None = None

    def _signals(self) -> dict:
        sig = self.score.observe_signals()
        st = self.progress.status()
        sig.update(
            {
                "level_id": st["level_id"],
                "level_idx": st["level_idx"],
                "theme_scene": st["theme_scene"],
                "level_title_en": st["level_title_en"],
            }
        )
        return sig

    def compose(self) -> ComposeResult:
        yield Header()
        yield MetricsPanel(id="metrics")
        with Horizontal(id="main"):
            yield TargetPanel(id="target")
            yield ScenePanel(id="scene")
        soft_note = "serve" if self._soft and self._soft.alive else self.mode
        mm = "key" if has_api_key() else "no-key"
        yield Static(
            "Ctrl+N skip · Ctrl+E evolve · Ctrl+C quit  ·  "
            f"mode={self.mode}  ·  soft={soft_note}  ·  minimax={mm}  ·  "
            f"AURA_BIN={AURA_BIN}",
            id="hint",
        )
        yield Footer()

    def on_mount(self) -> None:
        if self.mode == "soft":
            self._soft = soft_bridge.SoftServe.start()
            if not self._soft.alive:
                self.scene_source = f"offline(soft_down:{self._soft.last_error})"
        self._refresh_all()
        self._push_observe()

    def on_unmount(self) -> None:
        if self._soft is not None:
            self._soft.stop()
            self._soft = None

    def _refresh_all(self) -> None:
        self.query_one("#metrics", MetricsPanel).show(self.score, self.progress)
        self.query_one("#target", TargetPanel).show(
            self.target,
            self.typed_len,
            self.last_ok,
            self.progress.hint_zh(),
            self.progress,
        )
        self.query_one("#scene", ScenePanel).show(self.scene, self.scene_source)

    def _reset_line_counters(self) -> None:
        self.typed_len = 0
        self.line_correct = 0
        self.line_wrong = 0
        self.last_ok = None
        self.target = self.progress.target_text()

    def _line_accuracy(self) -> float:
        total = self.line_correct + self.line_wrong
        if total == 0:
            return 1.0
        return self.line_correct / total

    def _finish_line(self) -> None:
        event = self.progress.complete_line(self._line_accuracy())
        self._reset_line_counters()
        if event.get("advanced"):
            # Level-up: nudge scene toward new theme (offline); Soft may refine.
            theme = self.progress.level.theme_scene
            from host.scenes import SCENES

            if theme in SCENES:
                self.scene = SCENES[theme]
                self.scene_source = f"level-up:{event['to_level']}"

    def _push_observe(self, signals: dict | None = None) -> None:
        try:
            soft_bridge.write_observe(signals or self._signals())
        except OSError:
            pass

    def _apply_offline(self, signals: dict) -> None:
        # Prefer current level theme when accuracy is healthy
        from host.scenes import SCENES

        theme = self.progress.level.theme_scene
        acc = float(signals.get("accuracy", 1.0))
        streak = int(signals.get("streak", 0))
        if streak >= 20 and "party" in SCENES:
            self.scene = SCENES["party"]
        elif acc < 0.7 and "focus" in SCENES:
            self.scene = SCENES["focus"]
        elif theme in SCENES:
            self.scene = SCENES[theme]
        else:
            self.scene = rule_based_scene(signals)
        self.scene_source = "offline"

    def _enrich_copy(self, signals: dict) -> None:
        """MiniMax proposes title/blurb/art; Soft-owned id/hue/energy stay."""
        want = self.mode == "minimax" or (
            os.environ.get("TYPEPLAY_MINIMAX_COPY", "").strip() in ("1", "true", "yes")
        )
        if not want:
            return
        scene, tag = enrich_scene_copy(self.scene, signals, use_minimax=want and has_api_key())
        self.scene = scene
        if "minimax" in tag:
            self.scene_source = f"{self.scene_source}+{tag}"
        elif self.mode == "minimax":
            self.scene_source = f"{self.scene_source}+{tag}"

    def _maybe_evolve(self, force: bool = False) -> None:
        if not force and self.score.chars_done % self._evolve_every != 0:
            return
        signals = self._signals()
        self._push_observe(signals)

        if self.mode == "soft":
            got = soft_bridge.evolve_with_soft(signals, serve=self._soft)
            applied = apply_soft_scene(got.get("scene"), signals)
            if got.get("ok") and applied:
                self.scene, _ = applied
                via = got.get("via") or "soft"
                self.scene_source = f"soft/{via}"
                self.progress.hint_from_scene(self.scene.id)
                self.target = self.progress.target_text()
                self._enrich_copy(signals)
                self._refresh_all()
                return
            self._apply_offline(signals)
            self.scene_source = f"offline(soft_fallback:{got.get('via')})"
            self._enrich_copy(signals)
            self._refresh_all()
            return

        # minimax / offline: Soft or host select-best scene id first
        if self.mode == "minimax":
            # Prefer Soft oneshot for id/hue/energy when binary present
            got = soft_bridge.evolve_with_soft(signals, serve=None)
            applied = apply_soft_scene(got.get("scene"), signals) if got.get("ok") else None
            if applied:
                self.scene, _ = applied
                self.scene_source = "soft-select"
                self.progress.hint_from_scene(self.scene.id)
                self.target = self.progress.target_text()
            else:
                self._apply_offline(signals)
            self._enrich_copy(signals)
            self._refresh_all()
            return

        self._apply_offline(signals)
        self._enrich_copy(signals)
        self._refresh_all()

    def on_key(self, event: events.Key) -> None:
        # Textual versions differ: some have is_control, newer use is_printable.
        if getattr(event, "is_control", False):
            return
        if hasattr(event, "is_printable") and not event.is_printable:
            return
        # Named keys (ctrl+n, etc.) have character None; bindings handle those.
        if event.character is None or (event.key and event.key.startswith("ctrl+")):
            return
        ch = event.character
        if self.typed_len >= len(self.target):
            return
        expected = self.target[self.typed_len]
        ok = ch == expected
        self.score.record_key(ok)
        if ok:
            self.line_correct += 1
            self.typed_len += 1
            self.last_ok = True
            if self.typed_len >= len(self.target):
                self._finish_line()
        else:
            self.line_wrong += 1
            self.last_ok = False
        self._refresh_all()
        self._maybe_evolve()

    def action_skip(self) -> None:
        self.progress.skip_line()
        self._reset_line_counters()
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
