# S31: a better federal design than D4? (dev on the design set only)

**Outcome: no dev winner.** None of the five variants passed the gate on the design set: paired difference vs D4 of at
least +0.02 on all 1,357 items, with the 95% interval above 0. The S25 held-out items were **not used**. Nothing was
pre-registered, no test was run and nothing in `src/` changed. The S25 items are still unspent for a future single winner.

All numbers are as measured. Points are truncated. Wilson 95% intervals are rounded outward to 3 decimals. Paired
intervals use a percentile bootstrap over items (2,000 resamples, seed 2026), rounded outward to 4 decimals.

## Setup
- **Items:** the S9/S16 design set (1,357 federal affairs; gold = APS editors' chapter). Input is the S9 German title,
  long title and text, the same input S16 used.
- **Leave-one-out examples:** every example list excludes the item itself. The five examples are the frozen S9
  neighbours (`eval/spikes/s9-aps/data/d3_neighbours.json`), built leave-one-out. They match the current, fixed BM25 order
  on 1,306 of 1,357 items. Extra neighbours for k = 10 come from the shipped `ExamplePool` BM25 over
  `data/eval/aps_pool.jsonl`, excluding the item and the frozen five.
- **Reuse:** S9 rows d3m (identity order + 5 examples) and d0b (S1 order, no examples) are reused, as are the S9 d1 and
  S16 subtopic rows whenever the chapter list matches. Only missing readings were asked.
- **Decision rule, the same for every design:** this is `compose.chapter_decision` generalised to n readings.
  P = the mean of the readings, G = their normalised geometric mean. If G's top chapter is "no policy topic", that is the
  answer. Otherwise one subtopic request goes over `subtopic_chapters(P)` and the chapter is read back. Under this rule D4
  scores 0.7376. S16 reported 0.7406 with its own rule, which lacks the "no policy topic" check; 4 items differ.
- **Calls:** `querschnitt.client.Client` with `expect_build` = `vllm-0.23.1rc1.dev1029+ga601a9d99-tp8-pp2-dd237840`,
  model `swiss-ai/apertus-v1.5-8b`, no system message, at most 0.5 req/s, 2 workers, cap USD 4 on `eval/s31/ledger.jsonl`.

## Why these variants (free dev analysis, before any S31 call)
These checks used existing rows only.
- **Adding readings without examples dilutes the examples:**
  - D4 prior top-1 is 0.731.
  - Adding d0a (identity, no examples) as a third reading gives 0.697.
  - Adding the French reading d2fr (French title + text) gives 0.691.
  - The French reading alone scores 0.588, so the French variant was dropped. Production also has only the French title
    for federal affairs, not the French text.
- **The examples are weak but useful:** the gold chapter is among the 5 example labels for 63% of items, and the
  examples' majority label is right for only 37%.
- **Where D4 fails:** the two readings disagree on 486 of 1,357 items (36%), and D4 is right on only 58.6% of those. On
  those items d3m (with examples) is right 50.4% of the time and d0b (without) 25.5%.
- **Subtopic read-back over the top 3 always:** it can help at most 19 items (+0.014 upper bound), below the +0.02 gate
  even if every one were fixed. It was dropped.

The five variants:
| | Variant | What changes vs D4 |
|---|---|---|
| V1 | k10 | Reading 1 shows the 10 nearest examples (frozen 5 + next 5) |
| V2 | subn | Reading 1's 5 examples also name the editors' main subtopic (1,547/1,654 pool affairs have one) |
| V3 | ex2 | Reading 2 (S1 order) also shows the 5 examples |
| V4 | third | When reading 1 and reading 2 disagree, a third reading is added (5 examples, a third code order, `Random(31)`) |
| V5 | ex2+third | V3, plus V4's third reading when V3's two readings disagree |

V5 was fixed after V1–V4 had been seen on the 400 subset; this was still dev only. It was chosen because V3 and V4 were
each a little ahead, as the combination of the two.

## Stage 1: a fixed random 400-item subset (`random.Random(31).sample`)
| Design | top-1 [95%] | top-3 | minus D4 [95%] |
|---|---|---|---|
| D4 (shipped) | 0.7075 [0.661, 0.750] | 0.8575 | |
| V1 k10 | 0.7200 [0.674, 0.762] | 0.8625 | +0.0125 [−0.0050, +0.0300] |
| V2 subn | 0.7000 [0.653, 0.743] | 0.8575 | −0.0075 [−0.0176, +0.0025] |
| V3 ex2 | 0.7200 [0.674, 0.762] | 0.8475 | +0.0125 [−0.0100, +0.0375] |
| V4 third | 0.7175 [0.671, 0.760] | 0.8550 | +0.0100 [0.0000, +0.0225] |
| V5 ex2+third | 0.7175 [0.671, 0.760] | 0.8525 | +0.0100 [−0.0100, +0.0325] |

The best two by paired difference were V1 and V3, tied at +0.0125. They went to all 1,357 items.

## Stage 2: all 1,357 design-set items
| Design | top-1 [95%] | top-3 | minus D4 [95%] | Gate (≥ +0.02 and interval > 0) |
|---|---|---|---|---|
| D4 (shipped) | 0.7376 [0.713, 0.761] | 0.8835 | | |
| V1 k10 | 0.7450 [0.721, 0.768] | 0.8901 | +0.0073 [−0.0030, +0.0170] | no |
| V3 ex2 | 0.7494 [0.725, 0.772] | 0.8739 | +0.0117 [−0.0008, +0.0244] | no |

On the 957 items stage 1 did not see:
- V1: +0.0052 [−0.0074, +0.0178]
- V3: +0.0114 [−0.0032, +0.0262]

Both gains shrank from stage 1. V3 lowers top-3 (0.8739 vs 0.8835): with examples in both code orders, the two readings
agree more often (82% vs 64%), which likely concentrates P on fewer chapters. That also changes what the readings-agree signal
means. The shipped lane uses the calibrated p, but that map was fitted on D4.

Single-reading top-1 over 1,357 items:

| Reading | Top-1 |
|---|---|
| r1k10 | 0.7199 |
| d3m | 0.7081 |
| r2ex | 0.7096 |
| d0b | 0.6190 |

## Fresh test items?
None can be recovered with the S25 pipeline:
- **New captures:** a new Wayback CDX prefix listing of `anneepolitique.swiss/prozesse/` and `/fr/prozesse/` from
  2026-10-11 on (the S25 listings end at captures of 2026-10-11) returned one 301 capture each and 0 new process ids with
  a 200 capture. It went through `polite.py`: RFC 9309 robots checked, and web.archive.org robots.txt returned 404, which
  means allow all. The listing is in `cdx_check/`. This was 2 CDX requests plus the robots.txt fetch.
- **Unjoined S25 pages:** some fetched S25 pages have a chapter but no OPD join and carry a Geschäftsnr. Their 61 numbers
  were matched against the newer OPD snapshot: 4 match, and 0 of those have a production input.

S25 had already fetched every process id with a 200 capture that earlier sets had not.

## Calls and cost
| Run | Calls | USD (list price) |
|---|---|---|
| Stage 1 (V1–V4) | 1,714 | |
| V5 | 24 | |
| Stage 2 (V1, V3 on the remaining 957) | 2,534 | |
| **Total** | **4,272** | **0.6822** |

Every call was on the locked build. No model call touched an S25 item. `analyze.py check` only re-composed the shipped
S25 decisions from `runs/s25`, as a no-call check of the test harness: it reproduced 646/927 with 0 mismatches.

## Files
| File | What it is |
|---|---|
| `dev.py` | Variants, leave-one-out examples, calls (`call`) and scoring (`score`) |
| `dev_raw.jsonl` | One row per asked step |
| `ledger.jsonl` | The S31 call ledger |
| `dev_run*.log` | Run logs |
| `analyze.py dev` | Writes `results.json["dev"]`: stage 1, stage 2, the 957 split and the gate |
| `analyze.py check` | The no-call S25 harness check |
| `run.py` | The S25 test harness for a single winner. Not run. |
| `results.json` | Dev tables, the gate, the "no test" record and the fresh-item search |

## If someone continues
V3 is the closest candidate: +0.0117 [−0.0008, +0.0244] on all 1,357 items. Reusing this design set for a new round would
mean tuning further on the same items. A clean next step is one pre-registered look at V3 on the S25 items, with the
primary outcome and the "holds" rule written down first. Expect a gain of about +0.01 at most. With 927 items the paired
interval is about ±0.02, so the test would likely be inconclusive.
