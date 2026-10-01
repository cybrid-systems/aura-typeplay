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
make venv                     # or: ./scripts/run.sh (auto-venv)
make offline                  # rule-based scene swap, no MiniMax
# or
./scripts/run.sh
```

With MiniMax scene propose:

```bash
export MINIMAX_API_KEY=...
make minimax
```

Soft wire-up (later; v0 TUI runs without Soft):

```bash
export AURA_BIN=/workspace/aura-grok/build/aura
make doctor
```

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
  metrics.py        accuracy / WPM / streak / rhythm_cv
  scenes.py         ANSI scenes + offline rule-based picker
  minimax_scene.py  MiniMax propose (env key); Soft/host select
  lines.py          kid-friendly target lines
aura/               Soft product stubs (.aura) + integration notes
  typeplay_*.aura   session / observe / scene hooks (stubs)
  INTEGRATION.md    sockets Soft will serve later
scripts/run.sh      offline-by-default launcher
Makefile            venv / offline / minimax / doctor
```

## Soft sockets (v0 host drops JSON)

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
