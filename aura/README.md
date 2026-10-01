# Soft product stubs (aura-typeplay)

Thin `.aura` hooks Soft will serve later. **Do not** reimplement Soft language
features here — no Soft string/list hacks; host stays thin.

## Later wire-up

```bash
export AURA_BIN=/workspace/aura-grok/build/aura
# Soft observes host sockets, mutates scene params, host renders
```

| File | Role |
|------|------|
| `typeplay_session.aura` | Session score surface Soft may read/write |
| `typeplay_observe.aura` | Observe accuracy / WPM / rhythm_cv signals |
| `typeplay_scene.aura` | Scene mutate hooks (select among proposals) |

Host v0 already drops JSON at `$TYPEPLAY_SOCKET_DIR` (default `/tmp/aura-typeplay`):

- `observe.json` — live signals
- `scene.json` — current scene id / energy / source

Soft runtime owns evolve brains; this product owns kids UX + TUI.
