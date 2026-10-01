# aura-typeplay

**Kids typing game** — Soft observes accuracy & rhythm → scene evolves; DeepSeek proposes scene copy; Textual TUI host.

Not a Soft language tutorial. Not aura-build. A thin product on the Soft floor.

## One-line pitch

Type a line → live accuracy / WPM / streak → Soft (or offline rules / DeepSeek) evolves an ANSI/emoji scene. Celebrate rhythm, calm chaos, no gold hardcoded scene fixes.

## Three layers

| Layer | Owns | Does not |
|-------|------|----------|
| **Soft runtime** | Aura binary (`AURA_BIN`), mutate / select-best, honesty | Kids UX |
| **This product** | Textual TUI, typing lines, scene art, DeepSeek/MiniMax copy thin client | Soft language features |
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

DeepSeek Flash copy (host thin; Soft/host select) — see below:

```bash
# Soft + DeepSeek copy when key resolves (default):
export DEEPSEEK_API_KEY=...          # or KEY_FILE / deepseek.env
#   ~/.config/aura-build/deepseek.env typically:
#     DEEPSEEK_BASE_URL=https://api.deepseek.com
#     DEEPSEEK_MODEL=deepseek-flash
#     DEEPSEEK_API_KEY_FILE=/path/to/key
make soft
# make deepseek
# optional MiniMax: TYPEPLAY_LLM=minimax make minimax
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

## What you see: Soft vs DeepSeek

- **Soft selects** scene id / hue / energy (multi-propose → select-best from typing signals).
- **DeepSeek generates** kid-safe title, blurb, ASCII art, bilingual cheers, and **typing target words** — shown in
  the **「🌟 小星星说」** strip and as **「🎨 AI 画画」** on the scene panel when copy is live.
- Top status shows last evolve source (`soft/…+copy/deepseek-select-best` or offline).

Typing: wrong keys **do not advance**; the expected letter flashes huge until you hit it.
**Backspace** undoes one correct char. Details: [`docs/auto-evolve.md`](docs/auto-evolve.md).

## DeepSeek scene copy + words (default)

Soft **mutates** aura AST. DeepSeek only writes **copy + typing words** (never edits `.aura`). No key → built-in level word lists.

## DeepSeek scene copy (default)

Soft (or offline rules) **select** scene `id` / `hue` / `energy`. MiniMax only
**proposes** kid-safe `title` / `blurb` / ASCII `art` for that scene — host
select-best accepts or rejects (content filter); no gold rewrite of LLM copy.
No key / reject → library rule-based copy.

```bash
# DeepSeek key (never print the secret):
#   1) export DEEPSEEK_API_KEY=...
#   2) export DEEPSEEK_API_KEY_FILE=/path/to/key
#   3) share ~/.config/aura-build/deepseek.env — typically ONLY:
#        DEEPSEEK_BASE_URL=https://api.deepseek.com
#        DEEPSEEK_MODEL=deepseek-flash
#        DEEPSEEK_API_KEY_FILE=/path/to/key
make soft                           # Soft + DeepSeek copy (default)
make deepseek                       # explicit DeepSeek mode
# Optional MiniMax: TYPEPLAY_LLM=minimax make minimax
make smoke-llm-copy                 # filter + KEY_FILE smoke (+ live if key)
```

## Soft live-mutate (Aura-native)

Soft fiber worldlines `mutate:rebind` scene AST as you type — see [`docs/live-mutate.md`](docs/live-mutate.md). Host only displays `compile_epoch` / morph. DeepSeek chip on 「小星星说」: 未接 KEY / probing / OK / FAIL.

## Auto-evolve (no Ctrl+E)

Typing itself drives Soft + DeepSeek in the **background**. See [`docs/auto-evolve.md`](docs/auto-evolve.md).

- Soft: multi-propose scenes → select-best from rhythm / accuracy / streak
- DeepSeek Flash: continuous copy / style / bilingual micro-feedback (thinking disabled)
- TUI: big glyphs, emoji reactions, color bursts, morphing scene art

```bash
make venv && make soft      # Soft auto-evolve (+ DeepSeek copy if key set)
make deepseek               # explicit DeepSeek copy mode
# make minimax              # optional TYPEPLAY_LLM=minimax
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
  llm_copy.py       DeepSeek/MiniMax copy propose (title/blurb/art); Soft owns id/hue/energy
  minimax_scene.py  back-compat shim → llm_copy
  levels.py         progressive bilingual levels + hints
  lines.py          back-compat re-export
aura/               Soft product brain (.aura) + integration notes
  typeplay_*.aura   session / observe / scene evolve (Soft)
  INTEGRATION.md    sockets Soft will serve later
scripts/run.sh      offline-by-default launcher
Makefile            venv / offline / soft / deepseek / minimax / doctor
```

## Soft sockets (host ↔ Soft JSON)

Default dir: `/tmp/aura-typeplay` (`TYPEPLAY_SOCKET_DIR`):

- `observe.json` — live signals Soft will observe
- `scene.json` — current scene id / energy / source

## Non-goals

| Deny | Why |
|------|-----|
| Soft language reimplementation | Soft runtime owns brains |
| Gold hardcoded scene “fixes” | DeepSeek proposes copy; Soft/host selects |
| Touching aura-build product orch | Integration points only |

## License

Apache-2.0 (same as sibling cybrid-systems Soft repos).
