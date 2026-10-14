# S25 fetch: fresh APS-labelled federal affairs (2026-10-14)

Pre-registration: `../PREREG-BUILD.md`, entry S25. Nothing here is scored, and no model was called.

## What was searched (network: web.archive.org only)
- `cdx.py` ran new Wayback CDX prefix listings (no collapse; CDX folds www. and http/https together) and saved them to `cdx/`:
  `anneepolitique.swiss/prozesse/` (12,317 rows), `/fr/prozesse/` (2,036), `/de/`, `/it/`, `/en/prozesse/` and
  `/fr/processus/` (0 each), `/articles/` (75,714) and `/fr/articles/` (11,632). That gives 4,330 process ids with a 200
  text/html capture, compared with 4,301 in ideation-1's dumps.
- `fetch.py` fetched every process id that ideation-1 (298) or S9 (1,440 in `aps_ext.jsonl`) had not already fetched. It
  dropped pages whose slug number points to an excluded affair, used the newest DE-path capture (or the FR path when no DE
  capture exists), and went from the newest process id to the oldest. It fetched 2,585 pages: 2,572 returned HTTP 200, 13
  returned 404, and 9 transient connection errors were retried successfully.
- `art.py` checked the 28 OPD-linked article ids that have a capture and whose affair is not excluded. It read the archived
  301/302 Location headers without following redirects, so the calls never left web.archive.org. This found 7 extra process
  ids, which were then fetched.
- Parsing copies the chapter, main subtopic, article anchor, Geschäftsnr. and keyword regexes verbatim from ideation-1
  `c_aps_fetch.py` and S9 `fetch_aps.py`. `chapter` is the index into S9's `APS_CODES` (0–23).
- Politeness: ideation-1 `polite.py`, which applies RFC 9309 robots via `robots9309`, sends one UA, waits ≥ 1.2 s per host,
  and fails closed on 429/5xx. web.archive.org returned robots.txt 404, which RFC 9309 treats as allow-all (see
  `robots_log.jsonl`). There were no 429s and no blocks. Total fetch time was about 2.7 h.

## Join to OPD federal affairs (CHE)
Joins were tried in this order:
1. **`aps_link_in_page`:** article anchors on the page that OPD links as `aps_affair` (`external_links.ndjson.gz`) resolve to
   one OPD affair, or to the affair whose number matches the page's Geschäftsnr.
2. **`geschaeftsnr_on_page`:** the page's Geschäftsnr. equals an OPD CHE number.
3. **`slug_only`:** a Curia number at the end of the slug. None of these survived.

Pages that link to several OPD affairs without a matching number are dropped as `aps_link_ambiguous` (5 pages). Of the 2,585
pages, 1,651 did not join. Most are cantonal elections, party pages or other processes that are not affairs. 77 pages have
no chapter tag.

`finalize.py` runs without network. It rebuilds `items.jsonl` and `ids.txt` from `fetched.jsonl` and fills `curia_number`
from `bern/data/opd-new`. Four `x.9xxx` affairs were missing from the older OPD snapshot. All 927 items exist in opd-new,
and all are CHE.

## Dedupe and exclusions
An affair is excluded if its OPD id appears in any of:
- S9 `items.json` (1,357)
- S9 `aps_ext.jsonl` (all 1,436 fetched affairs)
- S5/ideation-1 `aps_gold_sample.jsonl` and `mem_ideation1.json` (297)
- the example pool `querschnitt/data/eval/aps_pool.jsonl` (1,654)

Pages were also excluded by process id against S9 and ideation-1. After this, the overlap of `ids.txt` with each set is 0.
Two affairs appeared on two process pages each, with the same chapter and subtopic on both, so one row per affair is kept
(the newest process id).

## Result
- **927 items** (`items.jsonl`, `ids.txt`).
- Join: `aps_link_in_page` 714, `geschaeftsnr_on_page` 213.
- Period by Curia number: 2020+ 219, 2010–19 580, pre-2010 128.
- Main subtopic present: 891. Of these, 878 are among the 190 DE subtopic names. Two captures are FR pages.
- Chapters (index:n): 0:15 1:57 2:108 3:11 5:93 6:23 7:53 8:54 9:35 10:46 11:28 12:78 13:18 14:36 15:17 16:50 17:92 18:68
  19:20 20:14 21:8 23:3. No items for 4 (1.1.5.) or 22 (2.0.1.).

## Files
| File | Contents |
|---|---|
| `cdx.py`, `fetch.py`, `art.py`, `finalize.py` | Scripts |
| `cdx/` | CDX listings, 21 MB |
| `fetched.jsonl` | Every fetched page with its parsed fields |
| `raw_pages.jsonl.gz` | Raw HTML of the fetched pages, 13 MB |
| `extra_cands.json`, `art_log.json` | Article-route output |
| `fetch.log` | Fetch log |

`fetch.py` also writes interim `items.jsonl` and `ids.txt` files. `finalize.py` produces the authoritative ones, so run it
after any re-fetch.
