PYTHON := .venv/bin/python

.PHONY: film setup validate script narration keyframes shots music assemble web test

film: setup validate narration keyframes shots music assemble

setup:
	@if [ ! -x "$(PYTHON)" ]; then \
		python3 -m venv .venv && \
		$(PYTHON) -m pip install --quiet -r requirements.txt; \
	fi

validate: setup
	$(PYTHON) pipeline/validate.py

script: setup
	$(PYTHON) pipeline/script.py

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

web: setup
	cd pipeline && ../$(PYTHON) -m uvicorn web:app --host 127.0.0.1 --port 8000

test: setup
	$(PYTHON) -m unittest discover -s tests -v
