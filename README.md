# aura-typeplay

**Kids typing game** — Soft observes accuracy & rhythm → scene evolves; MiniMax proposes scenes; Textual TUI host.

Not a Soft language tutorial. Not aura-build. A thin product on the Soft floor.

## One-line pitch

Type a line → live accuracy / WPM / streak → Soft (or offline rules / MiniMax) evolves an ANSI/emoji scene. Celebrate rhythm, calm chaos, no gold hardcoded scene fixes.

## Three layers

| Layer | Owns | Does not |
|-------|------|----------|
| **Soft runtime** | Aura binary (`AURA_BIN`), mutate / select-best, honesty | Kids UX |
| **This product** | Textual TUI, typing lines, scene art, MiniMax propose thin client | Soft language features |
| **No Soft language hacks** | Prefer Soft-native when Soft serves them | Invent soft_* string/list helpers here |

See [`docs/three-layers.md`](docs/three-layers.md) and [`aura/INTEGRATION.md`](aura/INTEGRATION.md).

## Quick start

```bash
cd /workspace/aura-typeplay   # or clone
make venv                     # REQUIRED first — uses python3 -m venv (not `python`)
make offline                  # rule-based scene swap (no Soft)
make soft                     # Soft serve observe-steer → scene (offline fallback if Soft down)
make doctor                   # Soft binary + evolve smoke
make smoke-soft               # non-interactive Soft oneshot + serve smoke
```

If `make soft` says `.venv missing`, run `make venv` first. Hosts with only `python3`
(no `python`) are supported; the Makefile prefers `.venv/bin/python3`.

Soft binary **only**:

```bash
export AURA_BIN=/workspace/aura-grok/build/aura
```

MiniMax propose (host thin; Soft/host select) — see below:

```bash
# either export the key:
export MINIMAX_API_KEY=...
# or share aura-build's env (recommended on this box):
#   ~/.config/aura-build/minimax.env  (+ MINIMAX_API_KEY_FILE)
# optional typeplay override:
#   ~/.config/aura-typeplay/minimax.env
make minimax
```

## Levels (bilingual)

Progressive ladder in [`host/levels.py`](host/levels.py) — see [`docs/levels.md`](docs/levels.md).

| Level | Soft scene | Try |
|-------|------------|-----|
| Home Row 基准键 | focus | `asdf jkl;` |
| Animals 可爱动物 | forest | `cat` / `mao is cat` |
| Meadow 阳光草地 | meadow | `yellow sun` |
| Ocean 平静大海 | ocean | `dolphin swims` |
| Space 星星花园 | space | `xing xing` |
| Celebrate 连击派对 | party | `you did great` |

Advance: 3 lines at ≥85% line accuracy. Soft scene may hint the next theme forward.

## What you see: Soft vs MiniMax

- **Soft selects** scene id / hue / energy (multi-propose → select-best from typing signals).
- **MiniMax generates** kid-safe title, blurb, ASCII art, and bilingual cheers — shown in
  the **「🌟 小星星说」** strip and as **「🎨 AI 画画」** on the scene panel when copy is live.
- Top status shows last evolve source (`soft/…+copy/minimax-select-best` or offline).

Typing: wrong keys **do not advance**; the expected letter flashes huge until you hit it.
**Backspace** undoes one correct char. Details: [`docs/auto-evolve.md`](docs/auto-evolve.md).

## MiniMax scene copy

Soft (or offline rules) **select** scene `id` / `hue` / `energy`. MiniMax only
**proposes** kid-safe `title` / `blurb` / ASCII `art` for that scene — host
select-best accepts or rejects (content filter); no gold rewrite of LLM copy.
No key / reject → library rule-based copy.

```bash
# Key resolution (same spirit as aura-build; never print the secret):
#   1) export MINIMAX_API_KEY=...
#   2) export MINIMAX_API_KEY_FILE=~/.config/aura-build/minimax_api_key
#   3) share ~/.config/aura-build/minimax.env  (or ~/.config/aura-typeplay/minimax.env)
# optional: MINIMAX_BASE_URL=https://api.minimaxi.com/v1
# optional: MINIMAX_MODEL=MiniMax-M3
make minimax                        # Soft/host select id → MiniMax copy
# Soft mode + copy: TYPEPLAY_MINIMAX_COPY=1 make soft
make smoke-minimax-copy             # filter smoke (+ live if key resolvable)
```

## Soft live-mutate (Aura-native)

Soft fiber worldlines `mutate:rebind` scene AST as you type — see [`docs/live-mutate.md`](docs/live-mutate.md). Host only displays `compile_epoch` / morph. MiniMax chip on 「小星星说」: 未接 KEY / probing / OK / FAIL.

## Auto-evolve (no Ctrl+E)

Typing itself drives Soft + MiniMax in the **background**. See [`docs/auto-evolve.md`](docs/auto-evolve.md).

- Soft: multi-propose scenes → select-best from rhythm / accuracy / streak
- MiniMax: continuous copy / style / bilingual micro-feedback proposals
- TUI: big glyphs, emoji reactions, color bursts, morphing scene art

```bash
make venv && make soft      # Soft auto-evolve (+ MiniMax copy if key set)
make minimax                # continuous MiniMax multi-propose + Soft select when available
```

### Keys

| Key | Action |
|-----|--------|
| letters / space / punct | Type against the target line |
| `Ctrl+N` | Skip line |
| `Ctrl+C` | Quit |

## Layout

```
host/               Python Textual TUI (thin host)
  app.py            main UI — target, metrics, scene panel
  soft_bridge.py    Soft --serve / oneshot bridge (thin)
  metrics.py        accuracy / WPM / streak / rhythm_cv
  scenes.py         ANSI scenes + offline + apply Soft scene
  minimax_scene.py  MiniMax copy propose (title/blurb/art); Soft owns id/hue/energy
  levels.py         progressive bilingual levels + hints
  lines.py          back-compat re-export
aura/               Soft product brain (.aura) + integration notes
  typeplay_*.aura   session / observe / scene evolve (Soft)
  INTEGRATION.md    sockets Soft will serve later
scripts/run.sh      offline-by-default launcher
Makefile            venv / offline / minimax / doctor
```

## Soft sockets (host ↔ Soft JSON)

Default dir: `/tmp/aura-typeplay` (`TYPEPLAY_SOCKET_DIR`):

- `observe.json` — live signals Soft will observe
- `scene.json` — current scene id / energy / source

## Non-goals

| Deny | Why |
|------|-----|
| Soft language reimplementation | Soft runtime owns brains |
| Gold hardcoded scene “fixes” | MiniMax proposes; Soft/host selects |
| Touching aura-build product orch | Integration points only |

## License

Apache-2.0 (same as sibling cybrid-systems Soft repos).
