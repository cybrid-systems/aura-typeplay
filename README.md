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
make venv
make offline                  # rule-based scene swap (no Soft)
make soft                     # Soft serve observe-steer → scene (offline fallback if Soft down)
make doctor                   # Soft binary + evolve smoke
make smoke-soft               # non-interactive Soft oneshot + serve smoke
```

Soft binary **only**:

```bash
export AURA_BIN=/workspace/aura-grok/build/aura
export AURA_SANDBOX=off
```

MiniMax propose (host thin; Soft/host select):

```bash
export MINIMAX_API_KEY=...
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

### Keys

| Key | Action |
|-----|--------|
| letters / space / punct | Type against the target line |
| `Ctrl+N` | Skip line |
| `Ctrl+E` | Force scene evolve |
| `Ctrl+C` | Quit |

## Layout

```
host/               Python Textual TUI (thin host)
  app.py            main UI — target, metrics, scene panel
  soft_bridge.py    Soft --serve / oneshot bridge (thin)
  metrics.py        accuracy / WPM / streak / rhythm_cv
  scenes.py         ANSI scenes + offline + apply Soft scene
  minimax_scene.py  MiniMax propose (env key); Soft/host select
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
