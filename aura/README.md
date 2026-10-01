# Soft product (aura-typeplay)

Product brain in Soft. Host is thin TUI + optional MiniMax API.

```bash
export AURA_BIN=/workspace/aura-grok/build/aura
export AURA_PATH=/workspace/aura-grok/lib:/workspace/aura-typeplay/aura
export TYPEPLAY_SOCKET_DIR=/tmp/aura-typeplay
# host writes observe.json, then:
"$AURA_BIN" -e '(begin (require "typeplay_scene" all:) (run-typeplay-evolve))'
```

Or `make soft` / `make smoke-soft`. Soft observe ≠ Hard.
