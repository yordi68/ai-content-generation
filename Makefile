PYTHON := .venv/bin/python

.PHONY: film setup validate narration keyframes shots music assemble

film: setup validate narration keyframes shots music assemble

setup:
	@if [ ! -x "$(PYTHON)" ]; then \
		python3 -m venv .venv && \
		$(PYTHON) -m pip install --quiet -r requirements.txt; \
	fi

validate: setup
	$(PYTHON) pipeline/validate.py

narration: setup
	$(PYTHON) pipeline/narration.py

keyframes: setup
	$(PYTHON) pipeline/keyframes.py

shots: setup
	$(PYTHON) pipeline/shots.py

music: setup
	$(PYTHON) pipeline/music.py

assemble: setup
	$(PYTHON) pipeline/assemble.py
