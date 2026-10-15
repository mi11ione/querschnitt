# Querschnitt. Local targets use .venv/bin/python (Python 3.12); the first target that needs it runs make install.
#   make install          .venv (uv, else python3.11+ -m venv) + editable install with dev and Postgres extras
#   make data             the scored data (GitHub release DATA_TAG=data-latest) -> app/data, data/{inputs,topics}.jsonl.gz
#   make run              API + app on SQLite with the shipped data (data/*.jsonl.gz, else app/data, else the test sample)
#                         -> http://127.0.0.1:8000  (PORT=..., QS_DB=... to change)
#   make demo             the pitch demo, no internet needed: make run on its own store (DEMO_DB, FRESH=1 reloads it),
#                         prints the URL of each pitch beat; Neues Thema offers the recorded run when the endpoint is down
#   make preflight        the morning check: venv, data, demo affair, recording, quick tests, API, site, endpoint, disk
#   make test             unit and API tests (fake model endpoint; no network, no model calls)
#   make eval GOLD=f.csv  score a labelled CSV against the stored rows (SCHEME=adhoc/digitalisierung for a positives list);
#                         GOLD=data/eval/gold_aps_s9.csv is scored on its production rows (eval/prod_gold, own store)
#   make claims           every number in README and docs backed by eval/claims.tsv or eval/pruefstand.json
#   make delta            nightly delta: fresh OPD export -> new/changed affairs -> batch -> rows (SINCE=yesterday)
#   make delta-plan       robots.txt + export index only: what the delta would download
#   make smoke            start the API, check /health and /metrics, stop it (CI)
#   make fake-endpoint    an OpenAI-compatible fake on 127.0.0.1:8099 (QS_BASE_URL=http://127.0.0.1:8099/v1)
#   make up-full / up-lite   docker compose profiles (full: Postgres + API + app + nightly; lite: nightly into QS_PG_DSN)
#   make report           docs/REPORT.md -> dist/querschnitt-report.pdf (A4; markdown-it-py + headless Chrome + node;
#                         REPORT_DATE=YYYY-MM-DD fixes the printed date; CHROME=... for another Chrome)
#   make report-png       the PDF's pages as PNGs in dist/report-pages/ for review (needs pdftoppm, poppler)
.PHONY: report report-png report-figure deps install run demo load serve test claims eval delta delta-plan smoke fake-endpoint docker up-full up-lite clean-db data data-release
VENV   := .venv/bin/python
PY     ?= $(VENV)
HOST   ?= 127.0.0.1
PORT   ?= 8000
SMOKE_PORT ?= 8791
SINCE  ?= yesterday
GOLD   ?=
SCHEME ?=
# the S9 APS editors' gold is mostly before 2025, outside the app's slice: score it on its production rows (eval/prod_gold)
EVAL_DB ?= $(if $(filter %gold_aps_s9.csv,$(GOLD)),$(CURDIR)/runs/eval-prodgold.sqlite)
EVAL_OUT ?= eval/results/eval-$(notdir $(basename $(GOLD)))$(if $(EVAL_DB),,$(if $(filter %gold_aps_s9.csv,$(GOLD)),-appstore)).json
export PYTHONPATH := $(CURDIR)/src$(if $(PYTHONPATH),:$(PYTHONPATH))

install:
	@if command -v uv >/dev/null 2>&1; then \
	  echo 'uv venv -p 3.12 .venv && uv pip install -p .venv/bin/python -e ".[dev,pg]"'; \
	  uv venv -p 3.12 .venv && uv pip install -p .venv/bin/python -e ".[dev,pg]"; \
	else \
	  P=$$(for p in python3.12 python3.13 python3.11 python3; do command -v $$p >/dev/null 2>&1 && \
	    $$p -c 'import sys; sys.exit(sys.version_info < (3, 11))' 2>/dev/null && { echo $$p; break; }; done); \
	  test -n "$$P" || { echo "make install needs uv (https://docs.astral.sh/uv/) or Python >= 3.11"; exit 2; }; \
	  echo "no uv: $$P -m venv .venv && .venv/bin/pip install -e \".[dev,pg]\""; \
	  $$P -m venv .venv && PIP_DISABLE_PIP_VERSION_CHECK=1 .venv/bin/pip install -q -e ".[dev,pg]"; \
	fi

# every target that runs Python: create .venv on first use; refuse an interpreter that cannot run the package
deps:
	@if [ "$(PY)" = "$(VENV)" ] && [ ! -x $(VENV) ]; then echo "no .venv yet: make install"; $(MAKE) --no-print-directory install || exit 2; fi
	@$(PY) -c "import sys; assert sys.version_info >= (3, 11), 'Python ' + sys.version.split()[0]; import fastapi, uvicorn, yaml" 2>/dev/null || \
	  { echo "$(PY) cannot run querschnitt (needs Python >= 3.11 with fastapi, uvicorn, pyyaml): make install, or pip install -e '.[dev]' and pass PY=python"; exit 2; }

run: load serve

# the pitch demo (docs/DEMO.md): local data only, its own store so rehearsal decisions stay out of the make run store
DEMO_DB ?= $(CURDIR)/runs/demo/querschnitt.sqlite
DEMO_URL = http://$(HOST):$(PORT)
demo: deps
	@test -f app/data/affairs.json -a -f app/data/topics.jsonl.gz -a -f app/data/neu_replay.json || \
	  { echo "no scored data in app/data: run make data once while online (it downloads the release), then make demo"; exit 2; }
	@if $(PY) -c "import socket,sys; s=socket.socket(); s.settimeout(0.5); sys.exit(s.connect_ex(('$(HOST)', $(PORT))) != 0)"; then \
	  echo "port $(PORT) is in use (another make run / make demo?): stop it, or make demo PORT=8001"; exit 2; fi
	@if [ -n "$(FRESH)" ]; then rm -f $(DEMO_DB) $(DEMO_DB)-wal $(DEMO_DB)-shm; echo "FRESH: $(DEMO_DB) removed"; fi
	@mkdir -p $(dir $(DEMO_DB)); test -f $(DEMO_DB) || echo "first make demo: loading the shipped data into $(DEMO_DB) (about a minute)"
	QS_DB=$(DEMO_DB) $(PY) -m querschnitt load --auto --if-empty
	@QS_DB=$(DEMO_DB) $(PY) -c "from querschnitt.store import Store; import sys; sys.exit(0 if Store().affair(338697) else 1)" || \
	  echo "WARNING: demo affair 338697 is not in $(DEMO_DB) (make demo FRESH=1, or pick another affair for the Gate 1 beat)"
	@$(PY) -I tools/preflight.py --endpoint-only || true
	@echo ""
	@echo "  Diese Woche      $(DEMO_URL)/#woche"
	@echo "  Atlas            $(DEMO_URL)/#ueber"
	@echo "  Demo affair      $(DEMO_URL)/#karte?a=338697"
	@echo "  Pult             $(DEMO_URL)/#karte?m=pult&tab=todo"
	@echo "  Neues Thema      $(DEMO_URL)/#neu?limit=25"
	@echo "  … its recording  $(DEMO_URL)/#neu?rec=1   (offered by itself when the model endpoint does not answer)"
	@echo "  Prüfstand        $(DEMO_URL)/#pruef"
	@echo "  Anbindung        $(DEMO_URL)/#anb"
	@echo "  Basel view       $(DEMO_URL)/#karte?t=bs-themen"
	@echo "  static fallback  https://querschnitt.mi11ion.io (needs internet)"
	@echo ""
	@echo "store $(DEMO_DB); Ctrl-C stops the server"
	QS_DB=$(DEMO_DB) $(PY) -m querschnitt serve --host $(HOST) --port $(PORT)

preflight: deps
	$(PY) -I tools/preflight.py

load: deps
	$(PY) -m querschnitt load --auto --if-empty

serve: deps
	$(PY) -m querschnitt serve --host $(HOST) --port $(PORT)

test: deps
	$(PY) -m pytest -q

claims: deps
	$(PY) -I tools/claims_check.py README.md docs/*.md

eval: deps
	@test -n "$(GOLD)" || { echo "usage: make eval GOLD=file.csv [SCHEME=adhoc/digitalisierung]"; exit 2; }
	@test -f "$(GOLD)" || { echo "no such file: $(GOLD) (labelled CSV: affair_id,label; shipped: data/eval/gold_aps_s9.csv, data/eval/gold_dvs30.csv)"; exit 2; }
	@if [ -n "$(EVAL_DB)" ]; then mkdir -p $(dir $(EVAL_DB)) && rm -f $(EVAL_DB) $(EVAL_DB)-wal $(EVAL_DB)-shm && \
	  echo "store $(EVAL_DB) <- eval/prod_gold (production rows of the S9 affairs; EVAL_DB= to score the app's store instead)" && \
	  QS_DB=$(EVAL_DB) $(PY) -m querschnitt load --inputs eval/prod_gold/inputs.jsonl.gz --topics eval/prod_gold/topics.jsonl.gz >/dev/null; \
	else \
	  test -f data/topics.jsonl.gz || test -n "$$QS_DB" || echo "no data/topics.jsonl.gz: run make data first, or the store holds only the test sample"; \
	  $(PY) -m querschnitt load --auto --if-empty; \
	fi
	$(if $(EVAL_DB),QS_DB=$(EVAL_DB) )$(PY) -m querschnitt eval $(GOLD) $(if $(SCHEME),--scheme $(SCHEME)) --out $(EVAL_OUT)

delta: deps
	$(PY) -m querschnitt delta --since $(SINCE)

delta-plan: deps
	$(PY) -m querschnitt delta --plan

smoke: deps
	@mkdir -p runs; QS_DB=$${QS_DB:-$(CURDIR)/runs/smoke.sqlite}; export QS_DB; rm -f $$QS_DB; \
	$(PY) -m querschnitt load --auto --if-empty >/dev/null && \
	{ $(PY) -m querschnitt serve --host 127.0.0.1 --port $(SMOKE_PORT) >runs/smoke.log 2>&1 & echo $$! > runs/smoke.pid; }; \
	ok=1; for i in $$(seq 1 40); do sleep 0.5; \
	  if $(PY) -c "import json,urllib.request as u; h=json.load(u.urlopen('http://127.0.0.1:$(SMOKE_PORT)/health')); assert h['ok'] and h['rows']>0; m=json.load(u.urlopen('http://127.0.0.1:$(SMOKE_PORT)/metrics')); print('health', h); print('metrics', m['line'])" 2>/dev/null; then ok=0; break; fi; done; \
	kill $$(cat runs/smoke.pid) 2>/dev/null; rm -f runs/smoke.pid; \
	if [ $$ok -ne 0 ]; then cat runs/smoke.log; echo "smoke FAILED"; exit 1; fi; echo "smoke ok"

fake-endpoint: deps
	$(PY) -m querschnitt.fake_endpoint --port 8099

docker:
	docker build -t querschnitt .

up-full:
	docker compose --profile full up -d --build

up-lite:
	docker compose --profile lite up -d --build

clean-db:
	rm -f data/querschnitt.sqlite data/querschnitt.sqlite-wal data/querschnitt.sqlite-shm

# the scored data (app/data + data/{inputs,topics}.jsonl.gz) ships as a GitHub release asset, not in git history
DATA_TAG ?= data-latest
# builds dist/querschnitt-data.tar.gz from the current export (does not publish it)
data-release: deps
	PY=$(PY) sh tools/make_data_release.sh

data:
	@echo "downloading release $(DATA_TAG)/querschnitt-data.tar.gz -> app/data/, data/inputs.jsonl.gz, data/topics.jsonl.gz"
	@mkdir -p app/data data && curl -fL $$( [ -t 2 ] && echo --progress-bar || echo -sS ) https://github.com/mi11ione/querschnitt/releases/download/$(DATA_TAG)/querschnitt-data.tar.gz | tar -xzf -
	@echo "data ok: app/data/ (static export), data/inputs.jsonl.gz, data/topics.jsonl.gz; next: make run"
	@if [ -f data/querschnitt.sqlite ]; then echo "note: data/querschnitt.sqlite exists and make run loads only into an empty store; make clean-db to load this data"; fi

# the evaluation report as a print PDF: Markdown -> HTML (tools/report/render.py, report.css, app/fonts) -> Chrome printToPDF
REPORT_PDF ?= dist/querschnitt-report.pdf
report:
	@if [ ! -x $(VENV) ] && [ "$(PY)" = "$(VENV)" ]; then $(MAKE) --no-print-directory install || exit 2; fi
	@$(PY) -c "import markdown_it" 2>/dev/null || { echo "$(PY) has no markdown-it-py: make install (dev extras)"; exit 2; }
	@command -v node >/dev/null 2>&1 || { echo "make report needs node >= 22 (WebSocket) to drive headless Chrome"; exit 2; }
	$(PY) tools/report/render.py docs/REPORT.md --out dist/querschnitt-report.html
	node tools/report/chrome.mjs pdf dist/querschnitt-report.html $(REPORT_PDF)
	@command -v pdfinfo >/dev/null 2>&1 && pdfinfo $(REPORT_PDF) | grep -E '^Pages' || true

report-png: report
	@command -v pdftoppm >/dev/null 2>&1 || { echo "report-png needs pdftoppm (brew install poppler)"; exit 2; }
	rm -rf dist/report-pages && mkdir -p dist/report-pages && pdftoppm -r 110 -png $(REPORT_PDF) dist/report-pages/page
	@ls dist/report-pages/*.png

# docs/img/pruefstand.png (figure 3): the Prüfstand lane chart, cropped from the app served on APP_URL, at 2x
APP_URL ?= http://127.0.0.1:8765/
report-figure:
	node tools/report/chrome.mjs shot '$(APP_URL)?lang=de#pruef' docs/img/pruefstand.png --size 1440x900 --scale 2 --clip 984,112,442,400
