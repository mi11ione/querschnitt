
## Design definitions as implemented
- **D0** (v14 shipped): L1 variant (c) (24 chapter names + their APS subtopic names, codes A–Y incl. "Kein Sachthema"), identity order (`d0a`) and the S1 permutation (`d0b`), geometric mean → chapter top-1. Prompt code is S5's `q1_prompt` verbatim (`scripts/s9lib.py`).
- **D1** readback: shortlist = top-3 chapters of the D0 *arithmetic* mean (top-2 if their subtopics total > 26; S5 rule), joint L2 over their subtopics, top chapter first, 1 call (`d1`; S5 `q2_prompt` verbatim). Chapter = chapter of argmax over subtopics of p_joint(sub) × P_arith(chapter) (β = 1, as S5; the "none" option is never chosen). Run on every item (not only on items with subtopic gold) so chapter top-1 is on the same items as D0.
- **D2** language pooling: S1 FR template, FR chapter names, DE subtopic names, identity order, on the Curia FR title + text (`d2fr`); averaged as the arithmetic mean of the three probability vectors (d0a, d0b, d2fr).
- **D3** label memory: identity order with the 5 BM25-nearest gold affairs (BM25 over DE titles of the ideation-1 297 + all other S9 items, query = title ×2 + first 400 text characters, S3 `build_data.py` BM25 verbatim), each shown as "- title / → Thema: <code> (<chapter name>)" in the S3 E3 shape (`d3m`); combined with D0's permuted order by geometric mean (D0's combiner). The pool is frozen when both fetchers have finished (`data/d3_neighbours.json`), so D3 runs last.
- **Top-3 / confidence for D1:** the shortlist chapters ranked by their best product score, then the other chapters in D0-arithmetic order; confidence = share of the normalised product mass on the chosen chapter.
- **Period** = year of the Curia number (YY.NNN → 19YY for YY ≥ 90, else 20YY).
- **Keyword baseline:** frozen rule and word lists in `data/keywords_frozen.json` (+ `.sha256`), written before the first model call of S9; majority order for ties = S9 gold frequency.
- **Subtopic gold** = page's main subtopic name exactly among the 190 DE names (ideation-1 rule). FR process pages carry FR subtopic names, so they count as "no subtopic gold"; they keep their chapter gold.

## Deviations
- 2026-10-13T18:22Z: the D2 averaging ("mean of probabilities with D0's two German orders") is implemented as the mean of the three vectors, and the D3 averaging ("averaged with D0's permuted order", combiner unstated) as the geometric mean (D0's combiner). Both choices were fixed and written here before any S9 item was scored.
- 2026-10-13T18:22Z: the reuse check reproduced S5's p within 1e-3 on 16/20, not 20/20, although the request bytes and fingerprint are identical. This is serving-side drift; it is reported, and the pre-registered analysis is unchanged.

## Files
`scripts/fetch_aps.py` (Wayback, parsing copied from ideation-1 `c_aps_fetch.py`), `scripts/fetch_curia.py` (Curia OData DE+FR), `scripts/build_items.py`, `scripts/freeze_keywords.py`, `scripts/verify_s5.py`, `scripts/run.py`, `scripts/analyze.py`, `scripts/render_md.py`; data `data/aps_ext.jsonl`, `data/curia_texts_{de,fr}.jsonl`, `data/items.json`, `data/robots_log.jsonl` (web.archive.org and ws.parlament.ch robots.txt both 404 → allow all under RFC 9309); raw `raw/{d0a,d0b,d1,d2fr,d3m}.jsonl`, `raw/errors.jsonl`. APS labels are used as evaluation facts only; no APS text is redistributed.
