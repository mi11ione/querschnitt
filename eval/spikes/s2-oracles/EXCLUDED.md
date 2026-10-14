# s2-oracles: what is not in this repository

Vendored: `results.md`, `scripts/` and `data/aps_gold_sample.jsonl` (the 298 APS-labelled federal affairs behind S3/S5:
OPD id, Curia number, capture URL and timestamp, parsed chapter and subtopic; no page content). The rest of `data/` (about
690 MB) and a local virtual environment (`.venv-bfh/`, about 370 MB) are not redistributed:

- `data/raw_aps/`, `data/raw_cdx/`, `data/raw_cap/`, `data/raw_dvs/`, `data/raw_swissvotes/`: fetched third-party pages
  (Wayback captures of anneepolitique.swiss, CDX listings, DVS and Swissvotes pages). Not ours to redistribute.
- `data/curia_business_*.jsonl.gz`, `data/curia_cleanpool_texts_*.jsonl.gz`, `data/oracle_curia.jsonl.gz`,
  `data/dvs_items.json`, `data/curia_tag*.json`: bulk Curia Vista / APS / DVS extracts.
- `data/bfh/`: the downloaded BFH classifier model and its raw outputs (about 650 MB).
- `.venv-bfh/`: a Python environment.

The fetch scripts (`scripts/a_curia_fetch.py`, `scripts/c_aps_fetch.py`, `scripts/c_cdx_overlap.py`, `scripts/b_dvs.py`,
`scripts/e_download.py`, with the polite fetcher `scripts/polite.py`) and the URLs they request are here, so the data can be
fetched again.
