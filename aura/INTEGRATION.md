# Integration points (Soft ↔ typeplay)

## Env

| Var | Default | Role |
|-----|---------|------|
| `AURA_BIN` | `/workspace/aura-grok/build/aura` | Soft binary **only** this path |
| `AURA_PATH` | Soft sets: `/workspace/aura-grok/lib:…/aura-typeplay/aura` | Module search |
| `AURA_SANDBOX` | `off` | Local Soft ergonomics |
| `TYPEPLAY_MODE` | `offline` | `offline` \| `soft` \| `minimax` |
| `TYPEPLAY_SOCKET_DIR` | `/tmp/aura-typeplay` | JSON observe/scene drop |
| `MINIMAX_API_KEY` | unset | Host MiniMax propose only |

## Wire path

```
 host (thin)                         Soft product brain
 ┌─────────────────────┐            ┌──────────────────────────┐
 │ write observe.json  │───────────►│ typeplay_session.aura    │
 │ aura --serve / -e   │  form      │ typeplay_observe.aura    │
 │   run-typeplay-evolve│───────────►│   query:* sample (≠Hard) │
 │ read scene.json     │◄───────────│ typeplay_scene.aura pick │
 │ render ANSI scene   │            │ write scene.json         │
 └─────────────────────┘            └──────────────────────────┘
         │
         └── Soft down → rule_based_scene (offline fallback)
```

## Soft observe ≠ Hard

- Typing signals (accuracy / WPM / streak / rhythm_cv) are **transform feedback**.
- Soft samples existing Aura `query:*` faces (incremental-relower, dirty-cascade,
  soa-dirty, type-linear-commit-health) for **guidance only**.
- Soft storm may calm-bias the scene; accuracy_red alone is **not** Soft storm.
- No new Soft counters / key renames unless Soft gaps require an Aura issue.

## Host roles (thin)

| Module | Role |
|--------|------|
| `host/soft_bridge.py` | start `--serve`, oneshot `-e`, JSON sockets |
| `host/app.py` | Textual TUI; mode=soft → Soft evolve |
| `host/minimax_scene.py` | optional MiniMax propose (env key) |
| `host/scenes.py` | art library + offline rules + apply Soft scene |

## Soft modules

| File | Entry |
|------|-------|
| `typeplay_session.aura` | read observe.json → session score |
| `typeplay_observe.aura` | query:* sample + soft gate |
| `typeplay_scene.aura` | `run-typeplay-evolve` → scene.json |

## Do not

- Touch Soft / aura-build product brains beyond these sockets
- Invent soft_* language helpers here
- Gold-hardcode scene “fixes”

## MiniMax copy (host thin)

Soft owns `id` / `hue` / `energy` via observe-steer. Host may call MiniMax to
propose `title` / `blurb` / `art` for the locked scene. Host select-best:
kid-safe accept, else rule-based library copy. Never gold-override Soft params
or rewrite accepted LLM strings.

## Auto-evolve (background)

Host `EvolveWorker` thread: Soft `run-typeplay-evolve` (multi-propose + select-best)
then MiniMax multi-propose copy; TUI polls snapshots. No keybinding to evolve.
