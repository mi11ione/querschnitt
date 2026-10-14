# Task card: Prüfstand — topics of Swiss parliamentary affairs

A re-runnable evaluation of a served Apertus build on two labelled sets from Querschnitt's Prüfstand. Any OpenAI-compatible
endpoint works; the result names the build it measured. Spec: `task.yaml` (lm-evaluation-harness-like, no dependency on
the harness). Reference implementation: `run.py`.

## Data

| Set | Items | Labels | Input per item | File |
|---|---|---|---|---|
| APS chapters, federal | 1,357 affairs of the Federal Assembly | the chapter (24 + "no policy topic") assigned by Année Politique Suisse editors, recovered from APS pages joined to OPD by Curia number; = `data/eval/gold_aps_s9.csv` in the repo | Curia Vista title, long title, submitted text (first 1,500 characters used), in German and French; five APS-labelled examples per item | `data/aps_s9.jsonl.gz` |
| DVS "Digitalisierung" | 30 affairs (BE 12, CHE 5, ZG 3, …) | on the public Digitale Verwaltung Schweiz list (all positives); = `data/eval/gold_dvs30.csv` | title, long title, language as in OPD | `data/dvs30.jsonl` |

- The items are frozen copies of the exact inputs of the measured runs (S9/S16 and S8), built by `build_items.py`;
  `data/MANIFEST.json` holds their sha256. The 1,357 APS items were held out from prompt design (S9 pre-registration);
  S16 compared the read-back designs on the same items under a rule fixed before its calls.
- Examples: for each APS item, the five most similar APS-labelled affairs (BM25 over titles, from a pool of 1,654 that
  includes the other test items; the item itself is left out), as S9 retrieved them. They are frozen per item because BM25
  tie order depends on pool order (the shipped engine's pool reproduces 1,311 of the 1,357 example lists exactly).
- Sources and terms: affair texts from Curia Vista (Swiss Parliament open data) and OpenParlData (CC BY 4.0); APS chapter
  labels as published on anneepolitique.swiss; the DVS list from digitale-verwaltung-schweiz.ch. Publishing the frozen
  files is subject to those terms.

## What is asked

Every reading is a closed choice: the user message lists codes, the assistant turn is prefilled with the opening of a JSON
answer (`{"kapitel": "`, `{"unterthema": "`, `{"antwort": "`), and the next-token log-probabilities of the code tokens are
read (`max_tokens` 1, `top_logprobs` 20, temperature 0, no system message). Prompts: `prompts/` holds a verbatim copy of
`src/querschnitt/prompts.py` and each prompt rendered for one item (`render_prompts.py`); `tests/test_prompts.py` pins
their hashes to the measured ones.

| Reading | Prompt | Used by |
|---|---|---|
| `d0a` | chapter list with subtopic names, codes A–Y in identity order | D0, D1 |
| `d0b` | the same, codes in the S1 permutation | D0, D1, D3, D4S |
| `d3m` | `d0a` plus the five APS-labelled examples | D3, D4S |
| `sub` | the subtopics of the top 2–3 chapters of a prior, top chapter first, plus "none of these" | D1, D4S |
| `yn_a`, `yn_b` | "Digitalisierung" yes/no, A = yes / A = no; `yn_b` only when 0.1 < p(yes) < 0.9 | DVS |

| Design | Chapter |
|---|---|
| D0 | geometric mean of `d0a` and `d0b` (plain list prompting, two code orders) |
| D1 | read back from `sub` (score = p(subtopic) × prior(chapter)), prior = mean of `d0a` and `d0b` |
| D3 | geometric mean of `d3m` and `d0b` |
| D4S | read back from `sub`, prior = `d3m` when its top p ≥ 0.9, else mean of `d3m` and `d0b` (Querschnitt's shipped design for federal affairs) |

Calls: 3 chapter readings + 1–2 subtopic requests per APS item (identical prompts are sent once), 1–2 per DVS item.

## Metrics

- APS: top-1 and top-3 accuracy per design with Wilson 95% intervals; paired top-1 differences (D1−D0, D3−D0, D4S−D0,
  D4S−D3, D4S−D1) with a 2,000-resample paired bootstrap; expected calibration error of the top-1 confidence (10 bins),
  raw and after 2-fold cross-fitted isotonic recalibration; agreement of the two code orders and D0 precision where they
  agree and where they differ; majority-chapter baseline.
- DVS: recall with a Wilson 95% interval, and the misses. The question and its 0.5 cut-off were written on these items
  (S3), so this is a recall check; a held-out recall test needs the full POLITmonitor list.

## Run

```sh
make install                                          # repo root; the task imports querschnitt from src/
export QS_BASE_URL=https://<endpoint>/v1 QS_MODEL=<model name> QS_API_KEY=<key>
python tools/probe_endpoint.py                        # log-probabilities, prefill, served build, rate
.venv/bin/python upstream/eval-task/run.py --out runs/eval-<build> --limit 20       # smoke run
.venv/bin/python upstream/eval-task/run.py --out runs/eval-<build> --conc 2 --max-rate 1.0
.venv/bin/python upstream/eval-task/run.py --out runs/eval-<build> --score-only    # re-score, no calls
```

Output: `raw.jsonl` (one row per prompt: prompt id, code log-probabilities, served model, `system_fingerprint`),
`ledger.jsonl` (tokens and list-price USD), `results.json`, `results.md`. The run locks the first served build and stops
when another one answers; an interrupted run resumes without re-sending a prompt. An endpoint without log-probabilities
still yields top-1 and lanes (the generated code), not the calibration metrics. `querschnitt.client` refuses to send a
prefill to a route name containing `-70b` (on Public AI that route answered prefilled requests with another model;
`../APERTUS-NOTES.md`), so the task does not run on such names.

## Reference results

Public AI `swiss-ai/apertus-v1.5-8b`, build `vllm-0.23.1rc1.dev1029+ga601a9d99-tp8-pp2-dd237840`, October 2026:

| | top-1 [95%] | ECE raw → isotonic | Source |
|---|---|---|---|
| D0 | 0.655 [0.629, 0.680] | 0.2623 → 0.035 | `ideation2/spikes/s9-aps/results.md`; ECE `s9c-calibration/results.json` |
| D1 | 0.7038 [0.679, 0.727] | 0.2791 → 0.0319 | `querschnitt/eval/s16/results.md` |
| D3 | 0.7222 [0.698, 0.745] | 0.221 → 0.017 | same; ECE `ideation2/spikes/s9c-calibration/results.json` |
| D4S | 0.7487 [0.725, 0.771] | 0.2416 → 0.0574 | same |
| DVS recall | 27/30 [0.744, 0.965] | — | `ideation2/spikes/s8-dvs/results.md` |

`run.py --score-only` on the stored S9/S16 and S8 rows reproduces every figure in this table (top-1, intervals, ECE,
DVS misses 161610, 297879, 337826). Majority-chapter baseline 0.0796; keywords 0.192 (S9; not re-run by the task).
