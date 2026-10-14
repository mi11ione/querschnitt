# s9-aps: what is not in this repository

- `data/curia_texts_de.jsonl`, `data/curia_texts_fr.jsonl` (about 9 MB): full Curia Vista texts (ws.parlament.ch) fetched by
  `scripts/fetch_curia.py`. Bulk copy of third-party full texts; not redistributed. The script and the asked ids
  (`data/curia_asked_de.json`, `data/curia_asked_fr.json`) are here.
- The anneepolitique.swiss pages themselves (Wayback captures) were never stored in this folder: `scripts/fetch_aps.py`
  parsed them on the fly. The capture URL, timestamp and the parsed chapter / subtopic for every affair are in
  `data/aps_ext.jsonl`; the robots log is `data/robots_log.jsonl`.
