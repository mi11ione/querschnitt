# On site: Sun 18 Oct 09:30 → Mon 19 Oct 14:30

## Sun before 09:30 — preflight (laptop on the venue Wi-Fi)
- Terminal 1: `make demo` (loads its store on the first start, then serves; it prints one link per pitch beat).
- Terminal 2: `make preflight`: venv, `app/data`, the demo affair, the Neues-Thema recording, the demo store, assets local,
  disk, a quick test subset, the local API, the deployed site, the model endpoint (`QS_BASE_URL` / `QS_MODEL` / `QS_API_KEY`
  as Neues Thema uses them; one 1-token request). Green / red table, and what to do for each red.
- Red model endpoint: the demo still runs; Neues Thema answers within seconds and offers the recording (docs/DEMO.md,
  Offline). Red deployed site: the laptop is the demo. Warn demo store (a rehearsal decided the demo affair): `Ctrl-C`,
  `make demo FRESH=1`.
- Once, endpoint blocked: the rehearsal in docs/DEMO.md (Offline); look at every `app/dev/shots/rehearsal-*.png`.

## Sun 09:30–10:15 — read the case
Map it onto the variants below; pick the lead screen; note what the partner asks to see measured.

## 10:30–11:30 — deep dive with Christian Gutknecht, in this order
1. How is quality judged — is there a labelled sample we can score now? (`make eval GOLD=…` takes any CSV with `affair_id,label`.)
2. APS chapters only, or both levels? One topic or several?
3. APS labels: for evaluation and for a published field? An APS dump?
4. For DVS: the full list behind the public page, or a POLITmonitor export — as gold and as examples?
5. Where would this run — current server, planned VM, GPU?
6. Delivery: table + API resource, bulk file, Apache Hop?
7. Input: title + text, or documents too?
8. Who defines ad-hoc topics, how fast?
9. Corrections into the admin workbench; private vs public confirmations?
10. Which bias checks convince you?
11. API calls during the event, or exports only?
12. How much does Romansh matter?

## 11:30–13:00 — endpoint hour
```sh
# capabilities of the CSCS endpoint (logprobs, prefill, served model, fingerprint, throughput, replay vs Public AI rows);
# the probe ignores QS_PREFILL / QS_NO_LOGPROBS and ends with the `export` lines to use and a one-line verdict
QS_NAME=cscs QS_BASE_URL=<url> QS_MODEL=<model> QS_API_KEY=<key> .venv/bin/python tools/probe_endpoint.py --n 60 --conc 1,4,8,16
# validated on Public AI 14 Oct: logprobs true, prefill_ok true, deterministic, replay 6/6 (eval/probe-publicai-*.json)
```
Per outcome (`prefill` · `logprobs` in the probe's summary line):
- `honoured` · `honoured`, verdict "measured design runs as measured" → CSCS can take the corpus run: refit cut-offs on
  the CSCS build (S16 analysis on the S9 items: `QS_*=… python eval/s16/run.py` into a fresh dir, then
  `eval/s16/analyze.py`), start a new run dir (a new build is never mixed into `runs/main`), point `ops/pipeline.py` at it.
  Replay `top1_agree` < 0.95 or `mean_abs_dp` > 0.05 → refit before any number from the new build is shown.
- `rejected` or `ignored` prefill → the measured design cannot run there. Either keep Public AI for the corpus and show
  CSCS only as a footprint, or run with `export QS_PREFILL=0` (verdict "runs in a fallback mode — refit + quality gate
  before use"): a fresh run dir, `make eval GOLD=data/eval/gold_aps_s9.csv` on its rows, cut-offs refitted, and every
  number from it labelled no-prefill. `noprefill_ok` false → do not use the endpoint.
  Measured cost on Public AI (S28, 927 held-out affairs): top-1 0.705 without prefill vs 0.696 with it, difference −0.008
  (−0.022 to 0.004), so none is measurable. The lane is the readings rule only (0.642 pass at 0.805 precision, vs 0.673 at
  0.812 calibrated). Same price.
- `absent` or `rejected` logprobs → `export QS_NO_LOGPROBS=1`: also unmeasured; lanes still run on generated codes (two
  readings), no chapter probabilities from that endpoint (they stay from Public AI rows).
- Use the printed `QS_MAX_RATE` and batch `--conc … --max-rate …` (`0.8 ×` the best rate without a `429`).
- A batch that stops with `# Endpoint capability` in `STOP.md` is never resumed automatically: re-probe, decide as above.

## Variants
| Variant | Lead screen | What changes | Rework | Commands |
|---|---|---|---|---|
| V1 APS chapters only | Karte on chapters | hide subtopics; chapter metrics | < 1 h | app: subtopics off |
| V2 Two levels, hierarchical metrics | Prüfstand per level | add hierarchical F1 | 1 h | `make eval` per level |
| V3 Ad-hoc first | Neues Thema | lead with §3; the partner's topic live | 1 h | `POST /adhoc` |
| V4 Documents (900k) | Pult with document passages | scorer on document text (input switch); sample, not all 900k | 3–4 h | `data.py` text choice → docs only |
| V5 Hidden labelled set | Prüfstand | `make eval GOLD=`; cut-offs from our gold only | < 1 h | `make eval GOLD=…` |
| V6 DVS demo required | §3 + Pult | as built | 0 | — |
| V7 API in/out | Terminal | thin adapter if API calls are allowed; write-back endpoints exist | 2 h | `querschnitt serve` |
| V8 Strict VPS limit | Terminal + `lite` footprint | endpoint-based service; footprint as measured | < 1 h | `docker compose --profile lite` |
| V9 Taxonomy handed over | Karte on the new scheme | new `schemes/<name>.yaml`; cut-offs and examples from any gold | 2–3 h | copy `be-directorates.yaml` shape |
| V10 Cantonal/communal emphasis | Karte, communes on | per-level table first; bilingual lane | 1 h | — |

## Live `make eval` on whatever the partner hands over
```sh
make eval GOLD=their.csv            # columns affair_id,label in OUR schemes (APS code, ad-hoc yes/no)
make eval GOLD=data/eval/gold_aps_s9.csv     # fallback: 1,357 APS editors' chapters on production rows
make scheme-eval GOLD=their.xlsx    # THEIR categories (POLITmonitor / DVS export, any CSV or XLSX): own scheme, scored
```
`make scheme-eval` turns their list into the S20/S21 test in one command: it reads the file, joins OPD ids or business
numbers (Curia `24.4266`, cantonal numbers) to the inputs, writes `src/querschnitt/schemes/partner-<slug>.yaml` from
their category names (verbatim, `status: test`: never composed or exported until someone removes that line), freezes the
keyword baseline, pre-registers, samples `N` affairs (stratified by label, `random.Random(2026)`), runs the shipped named
step through the batch runner (`--conc 2 --max-rate 0.5 --cap $CAP`, build locked first), with `EXAMPLES>0` a second arm
with their own labelled affairs as examples (S21 shape, two folds by id parity), and scores: top-1, top-3, any of their
labels in top-1/top-3, per-label recall, majority and keyword baselines, lanes, examples minus names (Wilson intervals,
points truncated). Report on screen and in `runs/scheme-<slug>/report.json`. Runbook:
1. `make scheme-eval GOLD=their.xlsx DRY=1`: read the printed line (key column, label column, joined, why the rest did not
   join); fix a wrong guess with `ID=col`, `LABEL=col` (`LABEL="Thema 1+Thema 2"`), `BODY=CHE`, `SEP=';'`, `NAME=slug`.
2. Look at `runs/scheme-<slug>/scheme.yaml` (their names) with Christian; agree `N` and `EXAMPLES` (defaults `N=200 EXAMPLES=5`).
3. `make scheme-eval GOLD=their.xlsx REGISTER=1`: writes the scheme file and appends the pre-registration to
   `eval/PREREG-BUILD.md` with `tools/prereg_append.py --no-push`, no call yet. Decide here whether to push it
   (`git commit eval/PREREG-BUILD.* -m … && git push`) so it is public before the numbers.
4. `make scheme-eval GOLD=their.xlsx CAP=2`: finds the entry (same plan, no second entry) and starts the calls; a stop
   (`STOP.md`, network, budget) resumes with the same command, cached rows are not asked again.
5. Show the printed report (top-1 against keyword and majority on the same items, the agree lane); the number is a
   measurement on their labels, registered before the calls; it goes into the docs only through `eval/claims.tsv`.

Pre-registration text: the generic template `PREREG` in `src/querschnitt/scheme_eval.py`, filled from the plan (file and
its sha256, columns, join counts, scheme, sample ids and their sha256, arms, outcomes, baselines, run flags, model and
build). `PREREG=local` writes it to the run dir instead (tooling checks), `PREREG=off` skips it.
Checked on 16 Oct on Basel-Stadt's own labels (`../data/manual/bs_100086.csv`, `N=150 EXAMPLES=0 PREREG=local`;
a tooling check, not a registered result): `runs/scheme-bs-100086/report.json`. Hand-built variants stay possible:
copy `src/querschnitt/schemes/bs-themen.yaml` → `querschnitt run --named <file> --ids …` (S20); `eval/s21/run.py` (S21).

## Afternoon / night
Tailor per variant; check-in with the partner on the live path; `make eval` on any sample received; re-runs; polish; rehearse
both scripts against the real demo (timer on screen).

## Mon 10:00 freeze → 13:30 submit (sprintd closes 14:30, no extension)
- [ ] `git status` clean; tag `v1.0-submission` (repo public since 14 Oct: github.com/mi11ione/querschnitt)
- [ ] README: setup, one-command run, samples, model roles (Apertus decides every topic; Claude/Qwen only as blind annotators in the evaluation), licences
- [ ] LICENSE (Apache-2.0 code), docs CC BY 4.0, data CDLA-Permissive-2.0 (topics file), third-party licences listed
- [ ] `make test` green; CI green on the tag
- [ ] claims check over README, report, pitch slides: `python tools/claims_check.py README.md docs/*.md`
- [ ] demo URL answers; static app shows the frozen data; live API on the laptop; `make preflight` has no red but the endpoint
- [ ] backup video (≤ 2 min) uploaded next to the repo
- [ ] report PDF/MD link; Prüfstand page link
- [ ] sprintd form: text and links in `docs/SUBMISSION.md` (repo, live, video, report, team, challenge); Roman submits
