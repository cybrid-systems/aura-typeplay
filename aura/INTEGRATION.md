# Integration points (Soft ↔ typeplay)

**Do not touch Soft/aura-build product brains beyond these documented sockets.**

## Env

| Var | Default | Role |
|-----|---------|------|
| `AURA_BIN` | `/workspace/aura-grok/build/aura` | Soft binary (later wire-up) |
| `TYPEPLAY_MODE` | `offline` | `offline` \| `minimax` |
| `MINIMAX_API_KEY` | unset | Required for MiniMax propose |
| `TYPEPLAY_SOCKET_DIR` | `/tmp/aura-typeplay` | JSON observe/scene drop |

## Host → Soft (observe)

Host writes `observe.json` after keystrokes / evolve ticks. Soft reads and
scores fitness. v0: Soft not required; host uses signals locally.

## Soft → Host (scene)

Soft writes `scene.json` (or mutates via future IPC). Host TUI polls / refreshes
scene panel. v0: host selects via `rule_based_scene` or MiniMax proposal.

## Three layers

1. **Soft runtime** — Aura binary, mutate/select-best, honesty flags
2. **This product** — kids typing UX, Textual host, scene art
3. **No Soft language hacks** — do not invent soft_* string helpers here; prefer Soft-native when Soft serves them
