# Task card: Prüfstand — topics of Swiss parliamentary affairs

A re-runnable evaluation of a served Apertus build on labelled sets from Querschnitt's Prüfstand: APS chapters in two
splits (the 1,357 affairs the shipped design was chosen on, and 927 held-out affairs never used while designing) and the
DVS "Digitalisierung" list. Any OpenAI-compatible endpoint works; the result names the build it measured. Spec:
`task.yaml` (lm-evaluation-harness-like, no dependency on the harness). Reference implementation: `run.py`.

## Data

| Set | Items | Labels | Input per item | File |
|---|---|---|---|---|
| APS chapters, federal, split `s9` | 1,357 affairs of the Federal Assembly | the chapter (24 + "no policy topic") assigned by Année Politique Suisse editors, recovered from APS pages joined to OPD by Curia number; = `data/eval/gold_aps_s9.csv` in the repo | Curia Vista title, long title, submitted text (first 1,500 characters used), in German and French; five APS-labelled examples per item | `data/aps_s9.jsonl.gz` |
| APS chapters, federal, split `heldout_s25` | 927 affairs of the Federal Assembly, filed 1990–2025, none used while designing | the APS editors' chapter and main subtopic, recovered from Wayback captures of anneepolitique.swiss process pages; = `eval/s25/items.jsonl` (ids `eval/s25/ids.txt`) | the production input the shipped run sent: title, long title, up to 1,500 characters of the affair's own text, in its language (German 926, French 1; the French titles of a German affair kept, without text); up to five APS-labelled examples per item (917 have them) | `data/aps_heldout_s25.jsonl.gz` |
| DVS "Digitalisierung" | 30 affairs (BE 12, CHE 5, ZG 3, …) | on the public Digitale Verwaltung Schweiz list (all positives); = `data/eval/gold_dvs30.csv` | title, long title, language as in OPD | `data/dvs30.jsonl` |

- The items are frozen copies of the exact inputs of the measured runs (S9/S16, S25 and S8), built by `build_items.py`;
  `data/MANIFEST.json` holds their sha256. The 1,357 `s9` items were held out from prompt design (S9 pre-registration);
  S16 compared the read-back designs on the same items under a rule fixed before its calls, so `s9` is the set the shipped
  design (D4) was chosen on and its D4 row is not a held-out result.
- `heldout_s25` is the held-out test of the shipped design, pre-registered before any of its items was scored
  (`eval/PREREG-BUILD.md`, entry 2026-10-14 20:20 CEST "S25"): affairs not in the S5 or S9 sets and not in the example pool
  (`build_items.py` asserts that none of the 927 is in `data/eval/aps_pool.jsonl`), parsed with the S9 rules
  (`eval/s25/FETCH.md`). Texts: the production inputs (`inputs.jsonl.gz`, built by `querschnitt build-inputs` from the OPD
  exports; not in the repo); for the 40 affairs whose document text was rebuilt on 16 Oct to start at the title, the untrimmed document head the model saw
  on 14 Oct. Examples: those the shipped engine retrieves (`querschnitt.examples.ExamplePool` over the same pool, German
  federal affairs only). Every first-reading prompt of the 927 equals one the shipped run sent (checked by prompt id with
  `build_items.py --s25-run runs/s25`). An item without examples (9 one-word procedural titles such as «Vereidigung» with no
  BM25 neighbour in the pool, and the French affair) gets the plain identity-order prompt as its first reading, as in the
  engine; that prompt is `d0a`'s, so it is sent once.
- Examples (`s9`): for each APS item, the five most similar APS-labelled affairs (BM25 over titles, from a pool of 1,654 that
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
| `d0b` | the same, codes in the S1 permutation | D0, D1, D3, D4, D4E, D4S |
| `d3m` | `d0a` plus the five APS-labelled examples (an item without examples: `d0a`'s prompt) | D3, D4, D4E, D4S |
| `sub` | the subtopics of the top 2–3 chapters of a prior, top chapter first, plus "none of these" | D1, D4, D4E, D4S |
| `yn_a`, `yn_b` | "Digitalisierung" yes/no, A = yes / A = no; `yn_b` only when 0.1 < p(yes) < 0.9 | DVS |

| Design | Chapter |
|---|---|
| D0 | geometric mean of `d0a` and `d0b` (plain list prompting, two code orders) |
| D1 | read back from `sub` (score = p(subtopic) × prior(chapter)), prior = mean of `d0a` and `d0b` |
| D3 | geometric mean of `d3m` and `d0b` |
| D4 | read back from `sub`, prior = mean of `d3m` and `d0b` (S16 D4 as pre-registered: every item read back) |
| D4E | D4 as the engine composes it (`querschnitt.compose.chapter_decision`; Querschnitt's shipped design for federal affairs): when the geometric mean of `d3m` and `d0b` puts "no policy topic" first, that is the answer without read-back; an item without examples whose first reading has top p ≥ 0.9 gets no `d0b` |
| D4S | read back from `sub`, prior = `d3m` when its top p ≥ 0.9, else mean of `d3m` and `d0b` (S16 secondary design, reported, not shipped) |

Calls: 3 chapter readings + 1–3 subtopic requests per APS item (identical prompts are sent once), 1–2 per DVS item.

## Metrics

- APS (either split): top-1 and top-3 accuracy per design with Wilson 95% intervals; paired top-1 differences (D1−D0,
  D3−D0, D4−D0, D4−D3, D4−D1, D4E−D4, D4S−D0, D4S−D3, D4S−D1) with a 2,000-resample paired bootstrap; expected calibration
  error of the top-1 confidence (10 bins), raw and after 2-fold cross-fitted isotonic recalibration; agreement of the two
  code orders and precision where they agree and where they differ (D0, D4, D4E); majority-chapter baseline. Each design
  is scored on the items whose readings are all stored (every item after a complete run; `n` per design in the output).
  Figures are truncated to 4 decimals, interval bounds widened outward.
- DVS: recall with a Wilson 95% interval, and the misses. The question and its 0.5 cut-off were written on these items
  (S3), so this is a recall check; a held-out recall test needs the full POLITmonitor list.

## Run

```sh
make install                                          # repo root; the task imports querschnitt from src/
export QS_BASE_URL=https://<endpoint>/v1 QS_MODEL=<model name> QS_API_KEY=<key>
python tools/probe_endpoint.py                        # log-probabilities, prefill, served build, rate
.venv/bin/python upstream/eval-task/run.py --out runs/eval-<build> --limit 20       # smoke run
.venv/bin/python upstream/eval-task/run.py --out runs/eval-<build> --conc 2 --max-rate 1.0
.venv/bin/python upstream/eval-task/run.py --out runs/eval-<build> --split heldout_s25   # the 927 held-out affairs
.venv/bin/python upstream/eval-task/run.py --out runs/eval-<build> --score-only [--split heldout_s25]   # re-score, no calls
```

`--split` selects the APS items (`s9`, the default, or `heldout_s25`); `heldout_s25` runs the APS task only unless
`--tasks` says otherwise. Both splits can share one `--out`: rows are keyed by prompt id, results go to `results.json` /
`results.md` (`s9`) and `results_heldout_s25.json` / `.md`. Output: `raw.jsonl` (one row per prompt: prompt id, code
log-probabilities, served model, `system_fingerprint`), `ledger.jsonl` (tokens and list-price USD), the results files.
The run locks the first served build and stops when another one answers; an interrupted run resumes without re-sending a prompt. An endpoint without log-probabilities
still yields top-1 and lanes (the generated code), not the calibration metrics. `querschnitt.client` refuses to send a
prefill to a route name containing `-70b` (on Public AI that route answered prefilled requests with another model;
`../APERTUS-NOTES.md`), so the task does not run on such names.

## Reference results

Public AI `swiss-ai/apertus-v1.5-8b`, build `vllm-0.23.1rc1.dev1029+ga601a9d99-tp8-pp2-dd237840`, October 2026.
`stored_rows.py` turns the stored rows of the measured runs into `raw.jsonl` rows keyed by the task's own prompt ids, and
`run.py --score-only` scores them (no calls); the outputs are in `reference/`. Paths are repo-relative.

Split `s9` and DVS (rows: `eval/spikes/s9-aps/raw/`, `eval/s16/raw.jsonl`, `eval/spikes/s8-dvs/raw/`; output
`reference/stored_s9.json`):

| | top-1 [95%] | ECE raw → isotonic | Measured in |
|---|---|---|---|
| D0 | 0.6551 [0.6294, 0.6800] | 0.2623 → 0.0351 | S9 (`eval/spikes/s9-aps/results.md`; ECE `eval/spikes/s9c-calibration/results.json`) |
| D1 | 0.7037 [0.6789, 0.7275] | 0.2791 → 0.0319 | S16 (`eval/s16/results.md`) |
| D3 | 0.7221 [0.6977, 0.7454] | 0.2212 → 0.0167 | S9; ECE `eval/spikes/s9c-calibration/results.json` |
| D4 | 0.7406 [0.7166, 0.7633] | 0.2462 → 0.0211 | S16 |
| D4E | 0.7376 [0.7136, 0.7604] | 0.2475 → 0.0332 | composed by the task from the S9/S16 rows (9 items have "no policy topic" first) |
| D4S | 0.7487 [0.7249, 0.7711] | 0.2416 → 0.0573 | S16 |
| DVS recall | 27/30 [0.7437, 0.9655] | — | S8 (`eval/spikes/s8-dvs/results.md`) |

The cited result files give the same quantities rounded to 3 or 4 decimals; the task truncates points and widens
interval bounds outward at 4. DVS misses 161610, 297879, 337826. Majority-chapter baseline 0.0795; keywords 0.192 (S9,
`eval/spikes/s9-aps/results.md`; not re-run by the task).

Split `heldout_s25`: the shipped result, as pre-registered and composed by the app (`eval/s25/analyze.py` →
`eval/s25/results.json`): top-1 0.696 [0.666, 0.726] (646/927), top-3 0.839 [0.814, 0.862]; frozen S9 keyword rule 0.186
on the same affairs. The task reproduces it from the stored S25 rows (`runs/s25`, local to the build machine, and
`eval/s25b/raw.jsonl`; output `reference/stored_heldout_s25.json`): D4E 646/927 = 0.6968 [0.6665, 0.7256]. Those rows
hold only what the engine and S25b asked, so the other designs there cover a subset (D0 918 items: 0.6546, = S25b's
601/918 in `eval/s25b/results.json`; D3 918; D4 918; D1 and D4S only the items whose prompts coincide). A complete
`--split heldout_s25` run asks every design's prompts.
