"""Typeplay Textual TUI — cute kids play; Soft+MiniMax auto-evolve in background.

No key-triggered evolve. Soft multi-propose + select-best owns scene params.
Python is thin: glyphs, emoji reactions, color bursts, bilingual micro-feedback.
"""

from __future__ import annotations

import os

from textual import events
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Footer, Header, Static

from host import soft_bridge
from host.evolve_worker import EvolveWorker
from host.feedback import (
    MicroFeedback,
    big_glyphs,
    for_key,
    for_level_up,
    for_line_done,
)
from host.levels import LevelProgress
from host.metrics import SessionScore
from host.minimax_scene import has_api_key
from host.scenes import SCENES, Scene, rule_based_scene

AURA_BIN = soft_bridge.resolve_aura_bin()


class MetricsPanel(Static):
    def show(self, score: SessionScore, progress: LevelProgress, burst: str) -> None:
        s = score.observe_signals()
        st = progress.status()
        stars = "⭐" * min(5, max(1, st["ok_lines"]))
        streak_bar = "🔥" * min(8, s["streak"] // 2) if s["streak"] else "💤"
        self.update(
            f"[bold #ffd700]Lv{st['level_idx']+1}[/] "
            f"[bold]{st['level_title_en']}[/] [cyan]{st['level_title_zh']}[/]  {stars}\n"
            f"[green]命中 Acc {s['accuracy']*100:4.0f}%[/]   "
            f"[magenta]速度 WPM {s['wpm']:4.0f}[/]   "
            f"[yellow]连击 {s['streak']}[/] {streak_bar}   "
            f"[dim]burst={burst} rhythm={s['rhythm_cv']:.2f}[/]"
        )


class TargetPanel(Static):
    def show(
        self,
        target: str,
        typed_len: int,
        last_ok: bool | None,
        hint_zh: str,
        progress: LevelProgress,
        scale: float,
        line_flavor: str,
    ) -> None:
        glyphs = big_glyphs(target, typed_len, last_ok, scale=scale)
        lv = progress.level
        flavor = f"\n[italic #aaf]💫 {line_flavor}[/]" if line_flavor else ""
        zh = f"[bold cyan]中文提示[/] {hint_zh}" if hint_zh else ""
        self.update(
            f"[bold #ffa]🏰 {lv.title_en}[/]  [cyan]{lv.title_zh}[/]\n"
            f"{zh}{flavor}\n\n"
            f"  {glyphs}\n"
        )


class ScenePanel(Static):
    def show(self, scene: Scene, source: str, morph_tick: int) -> None:
        hue = scene.hue if scene.hue in {
            "green", "blue", "magenta", "yellow", "cyan", "white", "red"
        } else "cyan"
        # Soft morph: nudge art lines with sparkles as tick grows
        art_lines = scene.art.strip("\n").splitlines() or ["  …  "]
        spark = ["✨", "🌟", "💫", "🌸", "🍀"][morph_tick % 5]
        if art_lines:
            art_lines[0] = f"{spark} {art_lines[0].strip()}"
        art = "\n".join(art_lines)
        blurb = f"\n[i #ddd]{scene.blurb}[/]" if scene.blurb else ""
        self.update(
            f"[bold {hue} on #1a1a2e] {scene.title} [/]\n"
            f"[dim]{scene.id} · e={scene.energy:.2f} · {source}[/]"
            f"{blurb}\n\n"
            f"[{hue}]{art}[/]"
        )


class ReactionPanel(Static):
    """Big emoji + EN/ZH encouraging micro-feedback."""

    def show(self, fb: MicroFeedback | None, async_en: str, async_zh: str) -> None:
        if fb is None:
            fb = MicroFeedback("🐣", "Ready when you are", "准备好就打字吧", "gentle")
        async_line = ""
        if async_en or async_zh:
            async_line = f"\n[dim]🎧 Soft/MiniMax:[/] {async_en}  [cyan]{async_zh}[/]"
        self.update(
            f"\n  [bold]{fb.emoji}  {fb.emoji}  {fb.emoji}[/]\n"
            f"  [bold #ff9]{fb.en}[/]    [bold cyan]{fb.zh}[/]"
            f"{async_line}\n"
        )


class TypeplayApp(App):
    """Kids typing — auto background Soft+MiniMax evolve; cute feedback TUI."""

    CSS = """
    Screen {
        layout: vertical;
        background: #0f0f1a;
    }
    #metrics {
        height: 4;
        padding: 0 1;
        border: heavy #ffd700;
        background: #1a1430;
    }
    #main { height: 1fr; }
    #left { width: 3fr; }
    #target {
        height: 1fr;
        padding: 1 2;
        border: tall #66ffaa;
        background: #12182a;
    }
    #reaction {
        height: 7;
        padding: 0 1;
        border: wide #ff88cc;
        background: #201028;
        text-align: center;
    }
    #scene {
        width: 2fr;
        padding: 1 1;
        border: tall #88aaff;
        background: #101828;
    }
    #hint {
        height: 2;
        padding: 0 1;
        color: #8899aa;
    }
    .burst-party { background: #402060; }
    .burst-sparkle { background: #203040; }
    .burst-soft { background: #182018; }
    .burst-oops { background: #301818; }
    .burst-gentle { background: #1a1a2e; }
    """

    BINDINGS = [
        ("ctrl+c", "quit", "Quit"),
        ("ctrl+n", "skip", "Skip line"),
    ]

    TITLE = "aura-typeplay ✿"
    SUB_TITLE = "cute typing · Soft auto-evolve · MiniMax copy"

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
        self.scene: Scene = SCENES.get("forest", rule_based_scene({}))
        self.scene_source = "boot"
        self._soft: soft_bridge.SoftServe | None = None
        self._worker: EvolveWorker | None = None
        self._fb: MicroFeedback | None = None
        self._burst = "gentle"
        self._glyph_scale = 1.0
        self._async_en = ""
        self._async_zh = ""
        self._line_flavor = ""
        self._morph_tick = 0
        self._keys_since_kick = 0

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
        yield Header(show_clock=True)
        yield MetricsPanel(id="metrics")
        with Horizontal(id="main"):
            with Vertical(id="left"):
                yield TargetPanel(id="target")
                yield ReactionPanel(id="reaction")
            yield ScenePanel(id="scene")
        soft_note = self.mode
        mm = "on" if has_api_key() else "offline-copy"
        yield Static(
            "Auto Soft+MiniMax evolve while you type · Ctrl+N skip · Ctrl+C quit  ·  "
            f"mode={self.mode} soft={soft_note} minimax={mm}",
            id="hint",
        )
        yield Footer()

    def on_mount(self) -> None:
        if self.mode in ("soft", "minimax"):
            self._soft = soft_bridge.SoftServe.start()
            if self._soft and not self._soft.alive:
                self.scene_source = f"offline(soft_down:{self._soft.last_error})"
        interval = float(os.environ.get("TYPEPLAY_EVOLVE_INTERVAL", "5"))
        self._worker = EvolveWorker(
            mode=self.mode,
            interval_s=max(3.0, interval),
            soft=self._soft if self._soft and self._soft.alive else None,
            signals_fn=self._signals,
        )
        self._worker.start()
        self.set_interval(0.45, self._poll_evolve)
        self._refresh_all()
        soft_bridge.write_observe(self._signals())

    def on_unmount(self) -> None:
        if self._worker:
            self._worker.stop()
            self._worker = None
        if self._soft:
            self._soft.stop()
            self._soft = None

    def _apply_burst_class(self) -> None:
        react = self.query_one("#reaction", ReactionPanel)
        for name in ("party", "sparkle", "soft", "oops", "gentle"):
            react.remove_class(f"burst-{name}")
        react.add_class(f"burst-{self._burst}")

    def _refresh_all(self) -> None:
        self.query_one("#metrics", MetricsPanel).show(
            self.score, self.progress, self._burst
        )
        self.query_one("#target", TargetPanel).show(
            self.target,
            self.typed_len,
            self.last_ok,
            self.progress.hint_zh(),
            self.progress,
            self._glyph_scale,
            self._line_flavor,
        )
        self.query_one("#scene", ScenePanel).show(
            self.scene, self.scene_source, self._morph_tick
        )
        self.query_one("#reaction", ReactionPanel).show(
            self._fb, self._async_en, self._async_zh
        )
        self._apply_burst_class()

    def _poll_evolve(self) -> None:
        if not self._worker:
            return
        snap = self._worker.snapshot()
        if snap.updated_at <= 0:
            return
        # Apply Soft-selected scene + MiniMax copy without blocking keys
        if snap.scene.id != self.scene.id or snap.scene.art != self.scene.art:
            self._morph_tick += 1
        self.scene = snap.scene
        self.scene_source = snap.source
        if snap.style:
            try:
                self._glyph_scale = float(snap.style.get("glyph_scale") or self._glyph_scale)
            except (TypeError, ValueError):
                pass
            burst = str(snap.style.get("burst") or self._burst)
            if burst in ("party", "sparkle", "soft", "oops", "gentle", "wonder"):
                self._burst = "sparkle" if burst == "wonder" else burst
        if snap.feedback_en:
            self._async_en = snap.feedback_en
        if snap.feedback_zh:
            self._async_zh = snap.feedback_zh
        if snap.line_flavor:
            self._line_flavor = snap.line_flavor
        # Soft scene may hint level forward
        if self.progress.hint_from_scene(self.scene.id):
            self.target = self.progress.target_text()
            self.typed_len = 0
            self._fb = for_level_up()
            self._burst = "party"
        self._refresh_all()

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
        self._fb = for_level_up() if event.get("advanced") else for_line_done()
        self._burst = "party" if event.get("advanced") else "sparkle"
        if event.get("advanced"):
            theme = self.progress.level.theme_scene
            if theme in SCENES:
                # Soft worker will refine; show theme immediately
                self.scene = SCENES[theme]
                self.scene_source = f"level-up:{event['to_level']}"
        if self._worker:
            self._worker.notify_signals()

    def on_key(self, event: events.Key) -> None:
        if getattr(event, "is_control", False):
            return
        if hasattr(event, "is_printable") and not event.is_printable:
            return
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
                self._fb = for_key(True, self.score.streak)
                if self.score.streak >= 8:
                    self._burst = "party"
                elif self.score.streak >= 4:
                    self._burst = "sparkle"
                else:
                    self._burst = "gentle"
        else:
            self.line_wrong += 1
            self.last_ok = False
            self._fb = for_key(False, self.score.streak)
            self._burst = "oops"
        soft_bridge.write_observe(self._signals())
        self._keys_since_kick += 1
        # Nudge background evolve on rhythm — never block; no Ctrl+E
        if self._worker and self._keys_since_kick >= 6:
            self._keys_since_kick = 0
            self._worker.notify_signals()
        self._refresh_all()

    def action_skip(self) -> None:
        self.progress.skip_line()
        self._reset_line_counters()
        self._fb = MicroFeedback("⏭️", "Skipped — next!", "跳过，下一句！", "soft")
        self._refresh_all()

    def action_quit(self) -> None:
        if self._worker:
            self._worker.stop()
            self._worker = None
        if self._soft:
            self._soft.stop()
            self._soft = None
        self.exit()


def main() -> None:
    TypeplayApp().run()


if __name__ == "__main__":
    main()
