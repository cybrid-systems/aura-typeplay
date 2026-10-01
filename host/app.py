"""Typeplay Textual TUI — cute kids play; Soft+MiniMax auto-evolve in background.

No key-triggered evolve. Soft multi-propose + select-best owns scene params.
Python is thin: glyphs, emoji reactions, color bursts, bilingual micro-feedback.
"""

from __future__ import annotations

import os
import time

from textual import events
from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import Footer, Header, Static

from host import soft_bridge
from host.evolve_worker import EvolveWorker
from host.feedback import (
    BACKSPACE_FB,
    MicroFeedback,
    big_glyphs,
    for_key,
    for_level_up,
    for_line_done,
    for_waiting,
)
from host.levels import LevelProgress
from host.metrics import SessionScore
from host.minimax_scene import has_api_key
from host.scenes import SCENES, Scene, rule_based_scene

AURA_BIN = soft_bridge.resolve_aura_bin()


class MetricsPanel(Static):
    def show(
        self,
        score: SessionScore,
        progress: LevelProgress,
        burst: str,
        evolve_source: str,
    ) -> None:
        s = score.observe_signals()
        st = progress.status()
        stars = "⭐" * min(5, max(1, st["ok_lines"]))
        streak_bar = "🔥" * min(8, s["streak"] // 2) if s["streak"] else "💤"
        src = evolve_source or "boot"
        self.update(
            f"[bold #ffd700]Lv{st['level_idx']+1}[/] "
            f"[bold]{st['level_title_en']}[/] [cyan]{st['level_title_zh']}[/]  {stars}\n"
            f"[green]命中 Acc {s['accuracy']*100:4.0f}%[/]   "
            f"[magenta]速度 WPM {s['wpm']:4.0f}[/]   "
            f"[yellow]连击 {s['streak']}[/] {streak_bar}   "
            f"[dim]burst={burst}[/]\n"
            f"[bold #8cf]📡 进化来源 evolve:[/] [white]{src}[/]"
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
        waiting_correct: bool,
    ) -> None:
        glyphs = big_glyphs(
            target,
            typed_len,
            last_ok,
            scale=scale,
            waiting_correct=waiting_correct,
        )
        lv = progress.level
        flavor = f"\n[italic #aaf]💫 {line_flavor}[/]" if line_flavor else ""
        zh = f"[bold cyan]中文提示[/] {hint_zh}" if hint_zh else ""
        wait = ""
        if waiting_correct and typed_len < len(target):
            wait = "\n[bold #ff8866]按错了不怕 — 看闪烁的大字，按对再走！[/]"
        self.update(
            f"[bold #ffa]🏰 {lv.title_en}[/]  [cyan]{lv.title_zh}[/]\n"
            f"{zh}{flavor}{wait}\n\n"
            f"  {glyphs}\n"
        )


class ScenePanel(Static):
    def show(self, scene: Scene, source: str, morph_tick: int) -> None:
        hue = scene.hue if scene.hue in {
            "green", "blue", "magenta", "yellow", "cyan", "white", "red"
        } else "cyan"
        art_lines = scene.art.strip("\n").splitlines() or ["  …  "]
        spark = ["✨", "🌟", "💫", "🌸", "🍀"][morph_tick % 5]
        if art_lines:
            art_lines[0] = f"{spark} {art_lines[0].strip()}"
        art = "\n".join(art_lines)
        blurb = f"\n[i #ddd]{scene.blurb}[/]" if scene.blurb else ""
        ai = "minimax" in (source or "").lower()
        badge = (
            "[bold #ff88ff on #2a1030] 🎨 AI 画画 MiniMax [/]"
            if ai
            else "[bold #88aaff on #102030] 🌿 Soft 场景 [/]"
        )
        self.update(
            f"{badge}\n"
            f"[bold {hue} on #1a1a2e] {scene.title} [/]\n"
            f"[dim]{scene.id} · e={scene.energy:.2f}[/]"
            f"{blurb}\n\n"
            f"[{hue}]{art}[/]"
        )


class ReactionPanel(Static):
    """Instant emoji + EN/ZH from local feedback (not MiniMax)."""

    def show(self, fb: MicroFeedback | None) -> None:
        if fb is None:
            fb = MicroFeedback("🐣", "Ready when you are", "准备好就打字吧", "gentle")
        self.update(
            f"\n  [bold]{fb.emoji}  {fb.emoji}  {fb.emoji}[/]\n"
            f"  [bold #ff9]{fb.en}[/]    [bold cyan]{fb.zh}[/]\n"
        )


class StarSpeakPanel(Static):
    """Dedicated MiniMax strip — 「小星星说」."""

    def show(self, en: str, zh: str, line_flavor: str, has_mm: bool) -> None:
        if not has_mm and not en and not zh:
            self.update(
                "[bold #ffd700]🌟 小星星说[/]  [dim]（等 MiniMax 钥匙 / waiting for AI copy…）[/]\n"
                "  [dim]Soft 选场景 · MiniMax 写文案与鼓励话[/]"
            )
            return
        zh_line = zh or "…"
        en_line = en or "…"
        flavor = f"\n  [italic #aaf]下一句味道 next vibe: {line_flavor}[/]" if line_flavor else ""
        self.update(
            f"[bold #ffd700 on #302010] 🌟 小星星说 MiniMax [/]\n"
            f"  [bold cyan]{zh_line}[/]\n"
            f"  [bold #ffd]{en_line}[/]"
            f"{flavor}"
        )


class TypeplayApp(App):
    """Kids typing — auto background Soft+MiniMax evolve; cute feedback TUI."""

    CSS = """
    Screen {
        layout: vertical;
        background: #0f0f1a;
    }
    #metrics {
        height: 5;
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
        height: 5;
        padding: 0 1;
        border: wide #ff88cc;
        background: #201028;
        text-align: center;
    }
    #star {
        height: 5;
        padding: 0 1;
        border: heavy #ffd700;
        background: #281808;
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
        # After a wrong key: must hit expected; ignore other printable noise
        self._waiting_correct = False
        self._last_wrong_fb_at = 0.0

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
                yield StarSpeakPanel(id="star")
            yield ScenePanel(id="scene")
        mm = "key✓" if has_api_key() else "no-key"
        yield Static(
            "Auto Soft+MiniMax · Backspace 退格 · Ctrl+N skip · Ctrl+C quit  ·  "
            f"mode={self.mode} minimax={mm}  ·  错了看黄色大字！",
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
            self.score, self.progress, self._burst, self.scene_source
        )
        self.query_one("#target", TargetPanel).show(
            self.target,
            self.typed_len,
            self.last_ok,
            self.progress.hint_zh(),
            self.progress,
            self._glyph_scale,
            self._line_flavor,
            self._waiting_correct,
        )
        self.query_one("#scene", ScenePanel).show(
            self.scene, self.scene_source, self._morph_tick
        )
        self.query_one("#reaction", ReactionPanel).show(self._fb)
        self.query_one("#star", StarSpeakPanel).show(
            self._async_en,
            self._async_zh,
            self._line_flavor,
            has_api_key(),
        )
        self._apply_burst_class()
        # Keep status hint fresh with last evolve source
        try:
            self.query_one("#hint", Static).update(
                "Auto Soft+MiniMax · Backspace 退格 · Ctrl+N skip · Ctrl+C quit  ·  "
                f"mode={self.mode}  ·  last={self.scene_source}"
            )
        except Exception:  # noqa: BLE001
            pass

    def _poll_evolve(self) -> None:
        if not self._worker:
            return
        snap = self._worker.snapshot()
        if snap.updated_at <= 0:
            return
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
        if self.progress.hint_from_scene(self.scene.id):
            self.target = self.progress.target_text()
            self.typed_len = 0
            self._waiting_correct = False
            self._fb = for_level_up()
            self._burst = "party"
        self._refresh_all()

    def _reset_line_counters(self) -> None:
        self.typed_len = 0
        self.line_correct = 0
        self.line_wrong = 0
        self.last_ok = None
        self._waiting_correct = False
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
                self.scene = SCENES[theme]
                self.scene_source = f"level-up:{event['to_level']}"
        if self._worker:
            self._worker.notify_signals()

    def _handle_backspace(self) -> None:
        if self.typed_len <= 0:
            self._fb = MicroFeedback("🛑", "Nothing to undo", "没有可退的字", "soft")
            self._refresh_all()
            return
        self.typed_len -= 1
        if self.line_correct > 0:
            self.line_correct -= 1
        self.score.undo_correct()
        self._waiting_correct = False
        self.last_ok = None
        self._fb = BACKSPACE_FB
        self._burst = "soft"
        soft_bridge.write_observe(self._signals())
        self._refresh_all()

    def on_key(self, event: events.Key) -> None:
        key = (event.key or "").lower()

        # Backspace / delete — undo one correct char
        if key in ("backspace", "delete") or event.character in ("\x7f", "\b"):
            self._handle_backspace()
            return

        if getattr(event, "is_control", False):
            return
        if event.key and event.key.startswith("ctrl+"):
            return

        # Enter: only if target expects newline (kids lines don't)
        if key in ("enter", "return"):
            if self.typed_len < len(self.target) and self.target[self.typed_len] == "\n":
                pass  # fall through as character
            else:
                return

        # Prefer character for printable; skip bare modifiers
        ch = event.character
        if ch is None:
            return
        if hasattr(event, "is_printable") and not event.is_printable:
            # allow space when it is the expected char even if flag quirks
            if ch != " ":
                return

        # Space / other printable only consume when matching or waiting cue
        if self.typed_len >= len(self.target):
            return

        expected = self.target[self.typed_len]

        # Strict: must hit expected. Wrong → wait with big flash; ignore spam.
        if self._waiting_correct:
            if ch == expected:
                self.score.record_key(True)
                self.line_correct += 1
                self.typed_len += 1
                self.last_ok = True
                self._waiting_correct = False
                if self.typed_len >= len(self.target):
                    self._finish_line()
                else:
                    self._fb = for_key(True, self.score.streak)
                    self._burst = "sparkle" if self.score.streak >= 4 else "gentle"
                soft_bridge.write_observe(self._signals())
                self._nudge_evolve()
                self._refresh_all()
            else:
                # Rate-limit oops spam — UI already shows big expected glyph
                now = time.monotonic()
                if now - self._last_wrong_fb_at > 0.6:
                    self._last_wrong_fb_at = now
                    self._fb = for_waiting(expected)
                    self._burst = "oops"
                    self._refresh_all()
            return

        ok = ch == expected
        if ok:
            self.score.record_key(True)
            self.line_correct += 1
            self.typed_len += 1
            self.last_ok = True
            self._waiting_correct = False
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
            # Count once, then wait — never freeze without cue
            self.score.record_key(False)
            self.line_wrong += 1
            self.last_ok = False
            self._waiting_correct = True
            self._last_wrong_fb_at = time.monotonic()
            self._fb = for_waiting(expected)
            self._burst = "oops"

        soft_bridge.write_observe(self._signals())
        self._nudge_evolve()
        self._refresh_all()

    def _nudge_evolve(self) -> None:
        self._keys_since_kick += 1
        if self._worker and self._keys_since_kick >= 6:
            self._keys_since_kick = 0
            self._worker.notify_signals()

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
