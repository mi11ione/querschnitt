# On site: Sun 18 Oct 09:30 → Mon 19 Oct 14:30

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
# capabilities of the CSCS endpoint (logprobs, prefill, served model, fingerprint, throughput, replay vs Public AI rows)
QS_NAME=cscs QS_BASE_URL=<url> QS_MODEL=<model> QS_API_KEY=<key> .venv/bin/python tools/probe_endpoint.py --n 60 --conc 1,4,8,16
# validated on Public AI 14 Oct: logprobs true, prefill_ok true, deterministic, replay 6/6 (eval/probe-publicai-*.json)
```
- `logprobs` true + `prefill_ok` true → CSCS can take the corpus run: refit cut-offs on the CSCS build (S16 analysis on the
  S9 items: `QS_*=… python eval/s16/run.py` into a fresh dir, then `eval/s16/analyze.py`), start a new run dir (a new build is
  never mixed into `runs/main`), point `ops/pipeline.py` at it.
- `logprobs` false → lanes still run on generated codes (two readings); chapter probabilities stay from Public AI rows.
- Replay `top1_agree` < 0.95 or `mean_abs_dp` > 0.05 → refit before any number from the new build is shown.

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
make eval GOLD=their.csv            # columns affair_id,label (APS code, ad-hoc yes/no, or their own scheme code)
make eval GOLD=data/eval/gold_aps_s9.csv     # fallback: 1,357 APS editors' chapters on production rows
```
Their own taxonomy: copy `src/querschnitt/schemes/bs-themen.yaml` (names only) → `querschnitt run --named <file> --ids …`
(S20 shape); their labels as examples: `eval/s21/run.py` shape (two folds).

## Afternoon / night
Tailor per variant; check-in with the partner on the live path; `make eval` on any sample received; re-runs; polish; rehearse
both scripts against the real demo (timer on screen).

## Mon 10:00 freeze → 13:30 submit (sprintd closes 14:30, no extension)
- [ ] `git status` clean; tag `v1.0-submission`; repo public (Roman flips visibility)
- [ ] README: setup, one-command run, samples, model roles (Apertus decides every topic; Claude/Qwen only as blind annotators in the evaluation), licences
- [ ] LICENSE (Apache-2.0 code), docs CC BY 4.0, data CDLA-Permissive-2.0 (topics file), third-party licences listed
- [ ] `make test` green; CI green on the tag
- [ ] claims check over README, report, pitch slides: `python tools/claims_check.py README.md docs/*.md`
- [ ] demo URL answers; static app shows the frozen data; live API on the laptop
- [ ] backup video (≤ 2 min) uploaded next to the repo
- [ ] report PDF/MD link; Prüfstand page link
- [ ] sprintd form: repo URL, demo URL, video URL, team, challenge; Roman submits
