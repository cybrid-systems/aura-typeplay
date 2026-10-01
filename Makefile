# aura-typeplay — kids typing TUI + Soft observe/evolve + MiniMax copy
# Soft binary ONLY: AURA_BIN=/workspace/aura-grok/build/aura
AURA_BIN ?= /workspace/aura-grok/build/aura
PYTHON   ?= .venv/bin/python
PIP      ?= .venv/bin/pip
export AURA_BIN
export AURA_SANDBOX ?= off

.PHONY: venv install run offline soft minimax doctor smoke-soft smoke-minimax-copy clean

venv:
	python3 -m venv .venv
	$(PIP) install -r requirements.txt

install: venv

run offline: offline

offline:
	TYPEPLAY_MODE=offline $(PYTHON) -m host.app

# Soft serve observe-steer (falls back offline if Soft down)
soft:
	TYPEPLAY_MODE=soft AURA_BIN=$(AURA_BIN) AURA_SANDBOX=off $(PYTHON) -m host.app

# Soft/host select scene id; MiniMax proposes title/blurb/art (needs MINIMAX_API_KEY)
minimax:
	@test -n "$$MINIMAX_API_KEY" || (echo "MINIMAX_API_KEY unset — will use rule-based copy"; true)
	TYPEPLAY_MODE=minimax AURA_BIN=$(AURA_BIN) AURA_SANDBOX=off $(PYTHON) -m host.app

doctor:
	@echo "AURA_BIN=$(AURA_BIN)"
	@test -x "$(AURA_BIN)" && echo "Soft binary: ok" || echo "Soft binary: MISSING"
	@$(PYTHON) -c "import textual; print('textual', textual.__version__)"
	@test -n "$$MINIMAX_API_KEY" && echo "MINIMAX_API_KEY: set" || echo "MINIMAX_API_KEY: unset"
	@TYPEPLAY_MODE=soft AURA_BIN=$(AURA_BIN) AURA_SANDBOX=off $(PYTHON) -c "from host.soft_bridge import doctor; import json; print(json.dumps(doctor(), indent=2))"

smoke-soft:
	TYPEPLAY_MODE=soft AURA_BIN=$(AURA_BIN) AURA_SANDBOX=off $(PYTHON) scripts/smoke_soft.py

smoke-minimax-copy:
	$(PYTHON) scripts/smoke_minimax_copy.py

clean:
	rm -rf .venv __pycache__ host/__pycache__ .pytest_cache
