#!/usr/bin/env bash
# Run typeplay TUI. TYPEPLAY_MODE=offline|soft|minimax
# Soft: AURA_BIN=/workspace/aura-grok/build/aura
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"
if [[ ! -x .venv/bin/python ]]; then
  python3 -m venv .venv
  .venv/bin/pip install -r requirements.txt
fi
export TYPEPLAY_MODE="${TYPEPLAY_MODE:-offline}"
export AURA_BIN="${AURA_BIN:-/workspace/aura-grok/build/aura}"
export AURA_SANDBOX="${AURA_SANDBOX:-off}"
exec .venv/bin/python -m host.app "$@"
