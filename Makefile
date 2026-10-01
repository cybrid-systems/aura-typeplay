# aura-typeplay — kids typing TUI + Soft observe/evolve + MiniMax copy
# Soft binary ONLY: AURA_BIN=/workspace/aura-grok/build/aura
#
# First time (needs python3 on PATH; `python` alone may be missing):
#   make venv
#   make soft
AURA_BIN   ?= /workspace/aura-grok/build/aura
PYTHON3    ?= python3
export AURA_BIN
export AURA_SANDBOX ?= off

# Resolve venv interpreter at recipe time (prefer python3; fall back to python).
# Do not bake the path at Makefile parse time — `make venv soft` must see a fresh venv.
PY_SH = if [ -x .venv/bin/python3 ]; then echo .venv/bin/python3; elif [ -x .venv/bin/python ]; then echo .venv/bin/python; else echo ""; fi

.PHONY: venv install ensure-venv run offline soft minimax doctor smoke-soft smoke-minimax-copy clean

venv:
	@command -v $(PYTHON3) >/dev/null 2>&1 || { \
	  echo "error: $(PYTHON3) not found on PATH (this project requires python3)."; \
	  exit 1; \
	}
	$(PYTHON3) -m venv .venv
	@PY=$$($(PY_SH)); \
	  if [ -z "$$PY" ]; then echo "error: venv created but no .venv/bin/python3 or python"; exit 1; fi; \
	  $$PY -m pip install -U pip && \
	  $$PY -m pip install -r requirements.txt && \
	  echo "venv ready: $$PY ($$($$PY --version))"

install: venv

ensure-venv:
	@PY=$$($(PY_SH)); \
	  if [ -z "$$PY" ]; then \
	    echo "error: .venv missing or incomplete — run:  make venv"; \
	    echo "  needs: python3 on PATH ($$(command -v $(PYTHON3) >/dev/null && $(PYTHON3) --version || echo 'python3 NOT FOUND'))"; \
	    exit 1; \
	  fi

run: offline

offline: ensure-venv
	@PY=$$($(PY_SH)); TYPEPLAY_MODE=offline $$PY -m host.app

# Soft serve observe-steer (falls back offline if Soft down)
soft: ensure-venv
	@PY=$$($(PY_SH)); TYPEPLAY_MODE=soft AURA_BIN=$(AURA_BIN) AURA_SANDBOX=off $$PY -m host.app

# Soft/host select scene id; MiniMax proposes title/blurb/art (needs MINIMAX_API_KEY)
minimax: ensure-venv
	@test -n "$$MINIMAX_API_KEY" || (echo "MINIMAX_API_KEY unset — will use rule-based copy"; true)
	@PY=$$($(PY_SH)); TYPEPLAY_MODE=minimax AURA_BIN=$(AURA_BIN) AURA_SANDBOX=off $$PY -m host.app

doctor: ensure-venv
	@echo "AURA_BIN=$(AURA_BIN)"
	@test -x "$(AURA_BIN)" && echo "Soft binary: ok" || echo "Soft binary: MISSING"
	@PY=$$($(PY_SH)); $$PY -c "import textual; print('textual', textual.__version__)"
	@test -n "$$MINIMAX_API_KEY" && echo "MINIMAX_API_KEY: set" || echo "MINIMAX_API_KEY: unset"
	@PY=$$($(PY_SH)); TYPEPLAY_MODE=soft AURA_BIN=$(AURA_BIN) AURA_SANDBOX=off $$PY -c "from host.soft_bridge import doctor; import json; print(json.dumps(doctor(), indent=2))"

smoke-soft: ensure-venv
	@PY=$$($(PY_SH)); TYPEPLAY_MODE=soft AURA_BIN=$(AURA_BIN) AURA_SANDBOX=off $$PY scripts/smoke_soft.py

smoke-minimax-copy: ensure-venv
	@PY=$$($(PY_SH)); $$PY scripts/smoke_minimax_copy.py

clean:
	rm -rf .venv __pycache__ host/__pycache__ .pytest_cache
