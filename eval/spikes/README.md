# Evaluation spikes S1–S15 (vendored evidence)

Verbatim copies of the pre-registered spikes that `eval/pruefstand.json` and `docs/PRUEFSTAND.md` cite: results, scripts,
blind packets and annotations, keys, frozen keyword files with their sha256, and the raw Apertus outputs (`raw/*.jsonl`).
S1–S7 came from the first evaluation round, S8–S15 from the second; `PREREG.md` (sha256 in `PREREG.sha256`) and
`PREREG-ADDENDA.md` are the second round's pre-registration. `lib/pai.py` is the API client the S8–S15 scripts import
(it reads the key from a local file; no key is stored here). `../research/` holds the prior-art notes cited for baselines.

Vendored files are byte-identical to the originals, so the scripts still carry the absolute paths of the original workspace
(`/Users/mi11ion/Desktop/hackapertus/bern/ideation/spikes/<spike>` and `.../ideation2/spikes/<spike>` are this folder;
`.../ideation2/lib` is `lib/`; OPD exports are the data dir from `make data`). They are kept as evidence, not as runnable
code; the frozen hashes (for example `s10-bilingual/FROZEN.sha256`) would break if they were edited.

Third-party content (fetched web pages, full Curia Vista texts, bulk OPD extracts) is left out; each spike that lost a file
says so in its `EXCLUDED.md`. One file is stored compressed: `s8-dvs/items_cache.json.gz` (the S8 population, gunzip it to
rerun the S8 scripts; `eval/s8full/analyze.py` reads the `.gz` directly).

Three earlier Public AI probes (9 Oct 2026, before the Querschnitt spikes; cited by `upstream/APERTUS-NOTES.md`) are
vendored as their result files only, byte-identical; their scripts and raw outputs stay in the working tree:
`live/results.md` (which build each route serves, determinism, the provider response cache, the `-70b` fallback;
originally `hackapertus/spikes/live/`), `subst/results.md` (the pre-registered system-prompt substitution battery;
`hackapertus/spikes/subst/`) and `mmlu/res_*.json` (the 250-question MMLU size check per route, one row per question:
predicted letter, gold letter, served model).
