# S12 evidence support, status: model phase done, blind judging pending (lead)

Pre-registration: PREREG-ADDENDA.md 2026-10-13 21:20 UTC, S12 paragraph.

## Model phase (2026-10-13)
- Sample: 120 of 1,355 S9 items with non-empty DE text and D1 row; random.Random(20261014).sample over oid-sorted pool (data/sample.json).
- D1 chapter: S9 analyze.py d1_like(o, PA, PA) copied verbatim into scripts/run.py (analyze.py not importable: it runs and rewrites S9 results.json).
- Sentences: title, long title (if different, first 400 chars), first 1,500 chars of text; regex split after . ! ? ; ; keep >= 25 chars; cap 40 (median 11, range 3-18).
- Call: pai.chat, tag bern2-s12-evidence, swiss-ai/apertus-v1.5-8b, user + prefill {"satz": ", max_tokens=3, logprobs, top_logprobs=20, temp 0.
- Fingerprint: 120/120 vllm-0.23.1rc1.dev1029+ga601a9d99-tp8-pp2-dd237840; 0 off-build.
- Parse: 120/120 valid numbers in range. Substring check: 120/120 (Wilson 0.969-1.0); by construction of the closed choice.
- D1 right per APS editors on the sample: 82/120.
- Chosen sentence number: #2 40, #3 19, #1 16, #4 9, other 36 (position skew toward the first sentences).
- Spend: USD 0.0061 (cap 0.50).

## Blind judging
TO MEASURE: packet/ (GUIDE.md, items.txt E001-E120, ann_TEMPLATE.tsv); key.jsonl outside packet. score.py (root) reads ann_A/B(/C).tsv.

## Deviations
- Prereg says "title + first 1,500 chars"; the brief adds the long title (as in the S9 input). Long title included when different from the title.
