# aura-typeplay — kids typing TUI + Soft observe/evolve hooks
# Soft wire-up later: AURA_BIN=/workspace/aura-grok/build/aura
AURA_BIN ?= /workspace/aura-grok/build/aura
PYTHON   ?= .venv/bin/python
PIP      ?= .venv/bin/pip

.PHONY: venv install run offline minimax doctor clean

venv:
	python3 -m venv .venv
	$(PIP) install -r requirements.txt

install: venv

# Offline: rule-based scene swap (no MiniMax)
run offline: offline

offline:
	TYPEPLAY_MODE=offline $(PYTHON) -m host.app

# MiniMax propose scenes when MINIMAX_API_KEY is set
minimax:
	TYPEPLAY_MODE=minimax $(PYTHON) -m host.app

doctor:
	@echo "AURA_BIN=$(AURA_BIN)"
	@test -x "$(AURA_BIN)" && echo "Soft binary: ok" || echo "Soft binary: missing (v0 TUI runs without Soft)"
	@$(PYTHON) -c "import textual; print('textual', textual.__version__)"
	@test -n "$$MINIMAX_API_KEY" && echo "MINIMAX_API_KEY: set" || echo "MINIMAX_API_KEY: unset (offline scenes)"

clean:
	rm -rf .venv __pycache__ host/__pycache__ .pytest_cache
