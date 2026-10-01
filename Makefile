# aura-typeplay — kids typing TUI + Soft observe/evolve + DeepSeek (default) copy
# Soft binary ONLY: AURA_BIN=/workspace/aura-grok/build/aura
#
# First time (needs python3 on PATH; `python` alone may be missing):
#   make venv
#   make soft
AURA_BIN   ?= /workspace/aura-grok/build/aura
PYTHON3    ?= python3
export AURA_BIN

# Resolve venv interpreter at recipe time (prefer python3; fall back to python).
# Do not bake the path at Makefile parse time — `make venv soft` must see a fresh venv.
PY_SH = if [ -x .venv/bin/python3 ]; then echo .venv/bin/python3; elif [ -x .venv/bin/python ]; then echo .venv/bin/python; else echo ""; fi

.PHONY: venv install ensure-venv run offline soft deepseek minimax doctor smoke-soft smoke-llm-copy smoke-minimax-copy clean

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

# Soft serve + DeepSeek Flash copy when key resolves (default TYPEPLAY_LLM=deepseek)
soft: ensure-venv
	@test -x "$(AURA_BIN)" || echo "warn: Soft missing at AURA_BIN=$(AURA_BIN) — TUI runs offline(soft_down); set AURA_BIN to your Soft binary"
	@PY=$$($(PY_SH)); TYPEPLAY_MODE=soft TYPEPLAY_LLM=deepseek AURA_BIN=$(AURA_BIN) $$PY -m host.app

# Soft + DeepSeek copy (explicit)
deepseek: ensure-venv
	@PY=$$($(PY_SH)); $$PY -c "from host.llm_copy import has_api_key; import sys; sys.exit(0 if has_api_key(provider='deepseek') else 1)" \
	  || (echo "DeepSeek key not found (DEEPSEEK_API_KEY / KEY_FILE / deepseek.env) — rule-based copy"; true)
	@PY=$$($(PY_SH)); TYPEPLAY_MODE=deepseek TYPEPLAY_LLM=deepseek AURA_BIN=$(AURA_BIN) $$PY -m host.app

# Optional MiniMax copy path
minimax: ensure-venv
	@PY=$$($(PY_SH)); $$PY -c "from host.llm_copy import has_api_key; import sys; sys.exit(0 if has_api_key(provider='minimax') else 1)" \
	  || (echo "MiniMax key not found (MINIMAX_API_KEY / KEY_FILE / minimax.env) — rule-based copy"; true)
	@PY=$$($(PY_SH)); TYPEPLAY_MODE=minimax TYPEPLAY_LLM=minimax AURA_BIN=$(AURA_BIN) $$PY -m host.app

doctor: ensure-venv
	@echo "AURA_BIN=$(AURA_BIN)"
	@test -x "$(AURA_BIN)" && echo "Soft binary: ok" || echo "Soft binary: MISSING"
	@PY=$$($(PY_SH)); $$PY -c "import textual; print('textual', textual.__version__)"
	@PY=$$($(PY_SH)); $$PY -c "from host.llm_copy import active_provider, resolve_llm; c=resolve_llm(); print('LLM provider:', active_provider()); print('LLM key:', 'resolved' if c.api_key else 'missing', c.error or ''); print('LLM base:', c.base_url, 'model:', c.model); m=resolve_llm(provider='minimax'); print('MiniMax key:', 'resolved' if m.api_key else 'missing')"
	@PY=$$($(PY_SH)); TYPEPLAY_MODE=soft AURA_BIN=$(AURA_BIN) $$PY -c "from host.soft_bridge import doctor; import json; print(json.dumps(doctor(), indent=2))"

smoke-soft: ensure-venv
	@PY=$$($(PY_SH)); TYPEPLAY_MODE=soft AURA_BIN=$(AURA_BIN) $$PY scripts/smoke_soft.py

smoke-llm-copy: ensure-venv
	@PY=$$($(PY_SH)); $$PY scripts/smoke_llm_copy.py

smoke-minimax-copy: smoke-llm-copy

clean:
	rm -rf .venv __pycache__ host/__pycache__ .pytest_cache
