# S1: Apertus runtime and scoring modes for APS topic classification (OPD, 325,691 affairs)

Spike run on 13 Oct 2026, 12:51–13:08 UTC. Tags `bern-s1-*`. **Total spend: USD 0.0585** (1,039 ledger rows, 580,953 prompt tokens).
**[M]** = measured here. **[D]** = derived by the arithmetic shown. **[A]** = assumption.
Raw data: `raw/*.jsonl`. Numbers: `analysis.json`. Scripts: `build_sample.py`, `s1lib.py`, `run_main.py`, `run_throughput.py`, `analyze.py`.

## Setup
- Route: `swiss-ai/apertus-v1.5-8b` through `gateway/gw.py` (`full=True`), with no system message. This route serves 70B weights, by inference (R3 §2.1).
- Served model: `swiss-ai/apertus-v1.5-8b` on 1,038 of 1,038 live calls [M]. Fingerprint: `vllm-0.23.1rc1.dev1029+ga601a9d99-tp8-pp2-dd237840` on 1,038 of 1,038 [M]. That is the registered build, and it did not change during the run, so every comparison below uses a single build.
- HTTP statuses (`urllib` observed, `gw.py` untouched): 1,037 × 200 and 12 × 429 [M]. Every 429 was retried by gw and succeeded. There were 0 errors.
- Scheme: the 24 APS chapters plus `Y` = "no policy topic" (election or appointment of persons, naturalisation, resignation, council procedure), so 25 codes `A`–`Y`.
  - Level 2 uses the 190 APS subtopics. Their names are German in every prompt, because R1 has no FR/IT subtopic names.
  - The Italian chapter names are our own translation; APS publishes de/fr only.
- Prompt language follows the affair: de/fr/it user prompts. The JSON key is `kapitel` / `chapitre` / `capitolo`.

## 1. Input realism
- Sample [M]: 110 affairs. The language counts are by prompt language; CHE "it" titles are sometimes French in OPD, and we kept them as they are.

  | Level | Total | With text | Title only |
  |---|---|---|---|
  | Federal | 42 | 15 | 27 |
  | Cantonal | 35 | 31 | 4 |
  | Communal | 33 | 29 | 4 |

  - By language: de 44, fr 34, it 32.
  - Bodies include ZH, SG, TI, JU, VS, SO, Aarau, Locarno, Lugano and others.
  - Input = title, plus the long title (≤400 chars), plus the first 1,500 chars of the text.
- Prompt tokens per M1 request, from `usage` [M]:
  - min 292, p50 689, mean 591.6, p95 810, max 841.
  - With text: mean 710.2 (n = 75). Title only: mean 337.4 (n = 35).
  - About 280 tokens are fixed overhead (instruction plus the 25-code list).
- Title-only share in OPD [M, census `gegenprobe/track_2a/data/census/{texts,docs}.tsv.gz`]: **44.8 %** (145,977 of 325,691).
  - Definition: the affair has neither a substantive `texts` row (type ≠ "Titel des Geschäftes", maxlen > 200) nor a document with status `ok` and > 200 chars.
  - By level: federal 7.7 %, cantonal 56.8 %, communal 53.4 %.
- What is actually on disk:
  - Federal texts: only the length metadata. `texts.tsv.gz` holds id/body/affair/type/maxlen and no text, so full text exists for just 15 federal affairs (`.work/fed/texts`).
  - Cantonal/communal: extracted PDF text for 5,795 affairs (`.work/text`, mapped through `adapters/url_cache.jsonl` + `adapters/state/*.jsonl`). The `docs_meta` `h` field is a text hash, not the PDF sha.
  - A production run therefore has to fetch texts.

## 2. Scoring modes, level 1 (n = affairs; agreement = top-1 in chapter space; 95 % Wilson CI)

| Mode | Requests per affair | Prompt tokens per affair [M] | USD per 1,000 affairs, sample [M] | HTTP latency per request, p50 / p95 [M] | Agreement [M] |
|---|---|---|---|---|---|
| **M1** single request, codes, top-20 | 1 | 591.6 | 0.059 | 0.88 s / 1.32 s (n = 109) | reference |
| **M4** = M1 with permuted code→chapter assignment | 1 | 606.1 | 0.061 | 0.89 s / 1.55 s (n = 60) | vs M1: **44/60 = 73.3 % [61.0, 82.9]** |
| M4 + contextual calibration ("N/A") | +150 one-off requests | — | — | — | vs M1-calibrated: 43/60 = 71.7 % [59.2, 81.5] |
| **M2** exact per-label continuation | 25 | 14,252 (25 × 570.1) | 1.43 | 1.30 s / 2.03 s (n = 375) | vs M1: **13/15 = 86.7 % [62.1, 96.3]** (sum lp); 12/15 = 80.0 % [54.8, 93.0] (mean lp per token) |
| **M3** batched, 8–9 per request | 0.118 (13 requests for 110 affairs) | 329.1 (+4.89 completion) | 0.034 | 5.55 s / 6.69 s per request (≈ 0.64 s per affair) | vs M1: **67/110 = 60.9 % [51.6, 69.5]**; vs M4: 32/60 = 53.3 % [40.9, 65.4] |
| **L2** subtopics of the M1 chapter | 1 (106 of 110; skipped when M1 = `Y`) | 470.9 (text 586.7 / title 214.8) | 0.047 | 1.17 s / 1.99 s (n = 106) | — (7.9 subtopics on average; top-1 p median 0.998) |

M1 mechanics [M]:
- Codes come back as single tokens (`"K"`; `" K"` also appears in the top 20 at e^−15). Generated token = top-1 code on 110 of 110.
- Probability mass on the 25 codes within the top 20: min 0.9978. Censoring of the 5 codes outside the top 20 is therefore irrelevant for top-1.
- Top-1 probability: median 0.993; below 0.5 on 10 of 110. The `Y` option was chosen 4 times.

Position bias (M4) [M]:
- Stability depends strongly on confidence:
  - M1 p ≥ 0.9: 40/46 = **87.0 % [74.3, 93.9]**.
  - M1 p < 0.9: 4/14 = 28.6 % [11.7, 54.6].
- Letter `A` won 0/110 times in identity order and 4/60 when permuted, so there is no slot-A effect like the one 2A saw in 8B A/B/C lists.

Contextual calibration [M]:
- The content-free input ("N/A", with exact per-code `prompt_logprobs`, 25 codes × 3 languages × 2 orders) is semantic, not positional. `Y` = no topic takes p 0.89–1.00 in both orders.
- Among substantive codes, the late slots lead in identity order (X −3.8, W −5.5).
- Subtracting the prior changed top-1 on 9 of 60 (identity) and 12 of 60 (permuted), and did **not** improve stability (43/60 vs 44/60). Not recommended in this form.

M2 [M]:
- Label continuations average 6.25 tokens, with 0 boundary straddles. The 4 HTTP 429s of the main runs all came from M2.
- The continuation must end in `"}`: a bare closing `"` costs about −18 because the tokenizer prefers the merged `"}` token (probe).
- M2's top-1 was within M1's top 3 on 14 of 15.
- The two disagreements:
  - "Benehmen der Asylsuchenden in Chiasso": M1 Verbände (wrong), M2 Umweltschutz (also wrong; the APS chapter is Soziale Gruppen).
  - An IT communal affair: Soziale Gruppen vs Bevölkerung und Arbeit.

M3 [M]:
- All 110 codes parsed, and the output format held: prefill `1: `, then lines `N:  X`.
- Agreement with M1 is low even where M1 is confident: 55/83 = 66.3 % [55.6, 75.5]. Batch context shifts the answers.
- Position within the batch does not matter: first half 59.6 %, second half 62.1 %.

All agreement figures measure consistency, not accuracy, because there is no gold here.

## 3. Throughput (M1 requests on fresh, never-sent affairs; worker processes; mean ≈ 580 prompt tokens)

| Concurrency | n | Wall time | Requests/s, end to end through gw | HTTP p50 / p95 | Mean HTTP in flight | Client overhead p50 | 429s | Errors |
|---|---|---|---|---|---|---|---|---|
| 1 | 16 | 38.8 s | 0.41 | 1.45 / 2.14 s | 0.64 | 0.94 s | 0 | 0 |
| 4 | 40 | 26.1 s | 1.53 | 1.54 / 2.18 s | 2.42 | 0.98 s | 0 | 0 |
| 4 (rerun) | 40 | 43.4 s | 0.92 | 1.42 / 4.06 s | 1.71 | 0.99 s | 8 (×2 retries) | 0 |
| 8 | 64 | 22.8 s | 2.80 | 1.45 / 2.23 s | 4.57 | 1.14 s | 0 | 0 |
| 8 (rerun) | 64 | 23.8 s | 2.69 | 1.48 / 2.03 s | 4.34 | 1.25 s | 0 | 0 |

- **Server latency stays flat** from 1 to 8 concurrent requests (p50 ≈ 1.45 s) [M].
- The end-to-end bottleneck is the client. gw re-reads its 135k-row ledger twice per call, which costs about 1 s of CPU per call, so only about 4.5 of 8 workers are in HTTP at once [M]. Worker processes were used because threads would serialise that CPU under the GIL.
- 429s [M] appeared in windows of 78–90 requests per minute, while windows of up to 108 requests per minute passed without any. They are load-dependent, not a fixed per-minute cap.
- HTTP latency for the same request shape was 0.88 s in the M1 run and 1.45 s 10 minutes later [M]. Latency varies with load.

## 4. Extrapolation to 325,691 affairs [D]

Assumptions:
- Price: list price on the `-8b` route, USD 0.10 per 1M prompt tokens and USD 0.20 per 1M completion tokens (gw `PRICES`) [A].
- Text availability: 55.2 % of affairs have text and 44.8 % are title-only (§1).
- Prompt tokens per affair, weighted by that split:
  - M1: 0.552 × 710.2 + 0.448 × 337.4 = **543**.
  - L2: 0.552 × 586.7 + 0.448 × 214.8 = **420**.
  - M2: 25 × 543 = 13,575.
  - M3: about 33 header tokens + 0.552 × 430 + 0.448 × 57 = **≈ 296** per affair (+4.9 completion).
- L2 is counted for every affair (upper bound; measured rate 106 of 110).
- Rates:
  - Gateway rate: measured c = 8, 2.7 requests/s.
  - Direct rate (a client without the gw ledger overhead): 8 / 1.5 s = 5.3 requests/s. This assumes latency stays flat at a full 8 in flight; only about 4.5 in flight was measured.

| Plan | Requests | Prompt tokens | USD | Wall time via gw at c = 8 | Wall time direct at c = 8 |
|---|---|---|---|---|---|
| **M1 + L2** | 651,382 | 313.6 M | 31.4 + 0.13 = **31.5** | 651,382 / 2.7 = 241k s = **67 h** | 651,382 / 5.3 = 123k s = **34 h** |
| M1 × 2 permutations + L2 (debiased L1) | 977,073 | 490.5 M | 49.2 | 100 h | 51 h |
| M1 + second permuted pass only where p < 0.9 (14/60 = 23 %) + L2 | 726,291 | 354.2 M | 35.5 | 75 h | 38 h |
| M3 for L1 (8.5 per request) + L2 single | 38,317 + 325,691 | 233.2 M | 23.7 | 38,317 / (8 / 6.85 s) = 9.1 h, plus 33.5 h = **43 h** | 7.4 h + 17.1 h = 24.5 h |
| M2 for L1 + L2 single | 8,142,275 + 325,691 | 4,558 M | **457** | 8.47 M / 2.7 = 36 days | 18.5 days |

- Daily delta of about 300 affairs [A]: M1 + L2 = 600 requests and 289k prompt tokens = **USD 0.03 per day**. That is 600 / 2.7 = 3.7 min at c = 8, or 24 min at c = 1.
- Rate limits: 1.1 % of HTTP attempts were 429s at these rates [M]. Daily or monthly quotas on Public AI were not probed.

**CSCS: TO MEASURE in the first on-site hour** (run the 1B `--mode auto` probe and the 2A served-model probe):
1. Are `logprobs` and `top_logprobs` supported, and up to how many? (M1 needs at least 20.)
2. Are assistant prefill, `continue_final_message` and `add_generation_prompt=false` accepted?
3. Is `prompt_logprobs` available? (M2 needs it.)
4. The served model name and `system_fingerprint`; and do `A`–`Y` stay single tokens?
5. Throughput: requests/s and p50/p95 latency at c = 1, 4, 8, 16, 32, plus 429s and quotas.
6. Is vLLM prefix caching on? The roughly 280-token header is shared by every call. With prefix caching, M2's 25 requests per affair share one prefill, so M2's compute cost falls far below its Public AI token bill.
7. Maximum context length, and whether a batch or offline endpoint exists.

## 5. Recommendation
- **Back catalogue: M1 + L2** (2 requests, about 960 prompt tokens per affair; about USD 32 for all affairs; 34–67 h at c = 8).
  - Accept L1 when M1 p ≥ 0.9 (75–77 % of affairs: 83 of 110, 46 of 60; 87 % permutation-stable).
  - Send the rest through a second, permuted M1 pass, sum the log-probs, and flag the affair for review when the two passes disagree. That adds about +12 % USD.
  - Do not use M3. It is the cheapest option (USD 0.034 per 1,000) but agrees with M1 on only 61 %, and with M4 on 53 %.
  - Do not use M2 at catalogue scale on Public AI (14× the tokens, about 36 days through gw).
- **Interactive / single affair: M1 → L2.** Two sequential requests take about 2–3 s of HTTP (0.9–1.5 s + 1.2 s), plus the gw client overhead.
- **Ad-hoc, user-defined topics** (free-text labels with no codes, e.g. "Digitalisierung"): **M2**.
  - It gives an exact log-prob for any label wording, with no letter codes and no top-20 censoring.
  - Per-label thresholds are possible, following the θ calibration pattern in 2A.
  - Cost is one request per label, run in parallel. It suits short label lists.
- Calibration with a content-free input: skip it. The "N/A" prior is semantic (it goes to `Y`) and did not improve stability.

## 6. Request shapes that worked (on `-8b`, fingerprint `…dd237840`)
M1 / M4 / L2: the generated token's `top_logprobs` are read as code → log-prob.
```json
{"model":"swiss-ai/apertus-v1.5-8b","temperature":0.0,"max_tokens":1,
 "messages":[{"role":"user","content":"Ordne das folgende parlamentarische Geschäft genau einem Thema der Année Politique Suisse zu.\n\nThemen:\nA = Politische Grundfragen\n…\nY = Kein Sachthema (…)\n\nGeschäft:\nTitel: …\nLangtitel: …\nText (Auszug): …\n\nAntworte nur mit dem Buchstaben des Themas als JSON: {\"kapitel\": \"<Buchstabe>\"}"},
             {"role":"assistant","content":"{\"kapitel\": \""}],
 "continue_final_message":true,"add_generation_prompt":false,"logprobs":true,"top_logprobs":20}
```
M2: one request per label. The prompt lists the names with no codes. The label's log-prob is the sum of the trailing actual-token `prompt_logprobs` covering `<label>"}`; they arrive at the response top level, under gw `meta.resp.prompt_logprobs`.
```json
{"model":"swiss-ai/apertus-v1.5-8b","temperature":0.0,"max_tokens":1,
 "messages":[{"role":"user","content":"…Themen:\n- Politische Grundfragen\n…\nAntworte nur mit dem Namen des Themas als JSON: {\"kapitel\": \"<Thema>\"}"},
             {"role":"assistant","content":"{\"kapitel\": \"Öffentliche Finanzen\"}"}],
 "continue_final_message":true,"add_generation_prompt":false,"prompt_logprobs":1}
```
M3: there are 8–9 affairs per prompt, numbered `Geschäft 1:` … `Geschäft 9:`. A code token is any generated token that follows `^\d+:\s*$`.
```json
{"model":"swiss-ai/apertus-v1.5-8b","temperature":0.0,"max_tokens":80,
 "messages":[{"role":"user","content":"Ordne jedes der folgenden … zu.\n\nThemen:\nA = …\n\nGeschäft 1:\nTitel: …\n\n…\n\nAntworte mit einer Zeile pro Geschäft im Format <Nummer>: <Buchstabe>, ohne weiteren Text."},
             {"role":"assistant","content":"1: "}],
 "continue_final_message":true,"add_generation_prompt":false,"logprobs":true,"top_logprobs":20}
```
Processes: all worker pools ran in the foreground and exited. `ps` shows no `run_main` or `run_throughput` process left.
