PYTHON ?= python3
VENV ?= .venv
REQ_FILE ?= src/requirements.txt
DEV_REQ_FILE ?= src/requirements-dev.txt
# Platform detection for virtualenv bin/Scripts directory
ifeq ($(OS),Windows_NT)
    VENV_BIN = $(VENV)/Scripts
else
    VENV_BIN = $(VENV)/bin
endif
VENV_PY = $(VENV_BIN)/python
VENV_PIP = $(VENV_BIN)/pip

.PHONY: help venv reinstall clean format check-layers test ci

help:
	@echo "Targets disponibili:"
	@echo "  venv          - Crea .venv e installa requisiti (dev inclusi)"
	@echo "  reinstall     - Ripulisce .venv e lo ricrea"
	@echo "  clean         - Pulisce cache/log e (opzionale) .venv"
	@echo "  format        - Esegue black su src/ e test/"
	@echo "  check-layers  - Verifica dipendenze tra layer"
	@echo "  test          - Pytest con soglia coverage 80%"
	@echo "  ci            - Sequenza completa: check-layers + test"

$(VENV_PY):
	$(PYTHON) src/scripts/venv_setup.py --env $(VENV)

venv: $(VENV_PY)

reinstall:
	$(PYTHON) src/scripts/clean.py
	$(PYTHON) src/scripts/venv_setup.py --env $(VENV) --recreate

clean:
	$(PYTHON) src/scripts/clean.py

format: $(VENV_PY)
	$(VENV_PY) -m black src test

check-layers: $(VENV_PY)
	$(VENV_PY) src/scripts/check_layers.py

test: $(VENV_PY)
	$(VENV_PY) -m pytest --maxfail=1 --disable-warnings --cov=src --cov-report=term-missing --cov-fail-under=80

ci: check-layers test