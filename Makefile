# Querschnitt. Local targets use .venv/bin/python (Python 3.12); the first target that needs it runs make install.
#   make install          .venv (uv, else python3.11+ -m venv) + editable install with dev and Postgres extras
#   make data             the scored data (GitHub release DATA_TAG=data-latest) -> app/data, data/{inputs,topics}.jsonl.gz
#   make run              API + app on SQLite with the shipped data (data/*.jsonl.gz, else app/data, else the test sample)
#                         -> http://127.0.0.1:8000  (PORT=..., QS_DB=... to change)
#   make test             unit and API tests (fake model endpoint; no network, no model calls)
#   make eval GOLD=f.csv  score a labelled CSV against the stored rows (SCHEME=adhoc/digitalisierung for a positives list);
#                         GOLD=data/eval/gold_aps_s9.csv is scored on its production rows (eval/prod_gold, own store)
#   make claims           every number in README and docs backed by eval/claims.tsv or eval/pruefstand.json
#   make delta            nightly delta: fresh OPD export -> new/changed affairs -> batch -> rows (SINCE=yesterday)
#   make delta-plan       robots.txt + export index only: what the delta would download
#   make smoke            start the API, check /health and /metrics, stop it (CI)
#   make fake-endpoint    an OpenAI-compatible fake on 127.0.0.1:8099 (QS_BASE_URL=http://127.0.0.1:8099/v1)
#   make up-full / up-lite   docker compose profiles (full: Postgres + API + app + nightly; lite: nightly into QS_PG_DSN)
.PHONY: deps install run load serve test claims eval delta delta-plan smoke fake-endpoint docker up-full up-lite clean-db data data-release
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
