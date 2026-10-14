# Querschnitt. Local targets use .venv (uv, Python 3.12) when present, else python3.
#   make install          uv venv + editable install with dev and Postgres extras
#   make run              API + app on SQLite with the shipped data (data/*.jsonl.gz, else app/data, else the test sample)
#                         -> http://127.0.0.1:8000  (PORT=..., QS_DB=... to change)
#   make test             unit and API tests (fake model endpoint; no network, no model calls)
#   make eval GOLD=f.csv  score a labelled CSV against the stored rows (SCHEME=adhoc/digitalisierung for a positives list)
#   make delta            nightly delta: fresh OPD export -> new/changed affairs -> batch -> rows (SINCE=yesterday)
#   make delta-plan       robots.txt + export index only: what the delta would download
#   make smoke            start the API, check /health and /metrics, stop it (CI)
#   make fake-endpoint    an OpenAI-compatible fake on 127.0.0.1:8099 (QS_BASE_URL=http://127.0.0.1:8099/v1)
#   make up-full / up-lite   docker compose profiles (full: Postgres + API + app + nightly; lite: nightly into QS_PG_DSN)
.PHONY: install run load serve test eval delta delta-plan smoke fake-endpoint docker up-full up-lite clean-db
PY     ?= $(if $(wildcard .venv/bin/python),.venv/bin/python,python3)
HOST   ?= 127.0.0.1
PORT   ?= 8000
SMOKE_PORT ?= 8791
SINCE  ?= yesterday
GOLD   ?=
SCHEME ?=
export PYTHONPATH := $(CURDIR)/src$(if $(PYTHONPATH),:$(PYTHONPATH))

install:
	uv venv -p 3.12 .venv && uv pip install -p .venv/bin/python -e ".[dev,pg]"

run: load serve

load:
	$(PY) -m querschnitt load --auto --if-empty

serve:
	$(PY) -m querschnitt serve --host $(HOST) --port $(PORT)

test:
	$(PY) -m pytest -q

eval:
	@test -n "$(GOLD)" || { echo "usage: make eval GOLD=file.csv [SCHEME=adhoc/digitalisierung]"; exit 2; }
	$(PY) -m querschnitt eval $(GOLD) $(if $(SCHEME),--scheme $(SCHEME)) --out eval/results/eval-$(notdir $(basename $(GOLD))).json

delta:
	$(PY) -m querschnitt delta --since $(SINCE)

delta-plan:
	$(PY) -m querschnitt delta --plan

smoke:
	@mkdir -p runs; QS_DB=$${QS_DB:-$(CURDIR)/runs/smoke.sqlite}; export QS_DB; rm -f $$QS_DB; \
	$(PY) -m querschnitt load --auto --if-empty >/dev/null && \
	{ $(PY) -m querschnitt serve --host 127.0.0.1 --port $(SMOKE_PORT) >runs/smoke.log 2>&1 & echo $$! > runs/smoke.pid; }; \
	ok=1; for i in $$(seq 1 40); do sleep 0.5; \
	  if $(PY) -c "import json,urllib.request as u; h=json.load(u.urlopen('http://127.0.0.1:$(SMOKE_PORT)/health')); assert h['ok'] and h['rows']>0; m=json.load(u.urlopen('http://127.0.0.1:$(SMOKE_PORT)/metrics')); print('health', h); print('metrics', m['line'])" 2>/dev/null; then ok=0; break; fi; done; \
	kill $$(cat runs/smoke.pid) 2>/dev/null; rm -f runs/smoke.pid; \
	if [ $$ok -ne 0 ]; then cat runs/smoke.log; echo "smoke FAILED"; exit 1; fi; echo "smoke ok"

fake-endpoint:
	$(PY) -m querschnitt.fake_endpoint --port 8099

docker:
	docker build -t querschnitt .

up-full:
	docker compose --profile full up -d --build

up-lite:
	docker compose --profile lite up -d --build

clean-db:
	rm -f data/querschnitt.sqlite data/querschnitt.sqlite-wal data/querschnitt.sqlite-shm
