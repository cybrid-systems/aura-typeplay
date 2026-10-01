#!/usr/bin/env bash
# Run typeplay TUI. TYPEPLAY_MODE=offline|soft|minimax
# Soft: AURA_BIN=/workspace/aura-grok/build/aura
# Uses python3 for venv (hosts may lack a `python` binary).
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

resolve_py() {
  if [[ -x .venv/bin/python3 ]]; then
    echo .venv/bin/python3
  elif [[ -x .venv/bin/python ]]; then
    echo .venv/bin/python
  else
    echo ""
  fi
}

PY="$(resolve_py)"
if [[ -z "$PY" ]]; then
  if ! command -v python3 >/dev/null 2>&1; then
    echo "error: python3 not found on PATH; install python3 then: make venv" >&2
    exit 1
  fi
  echo "creating .venv with python3...” >&2
  python3 -m venv .venv
  PY="$(resolve_py)"
  if [[ -z "$PY" ]]; then
    echo "error: venv missing python3/python — run: make venv" >&2
    exit 1
  fi
  "$PY" -m pip install -U pip
  "$PY" -m pip install -r requirements.txt
fi

export TYPEPLAY_MODE="${TYPEPLAY_MODE:-offline}"
export AURA_BIN="${AURA_BIN:-/workspace/aura-grok/build/aura}"
export AURA_SANDBOX="${AURA_SANDBOX:-off}"
exec "$PY" -m host.app "$@"
