# s3-accuracy: what is not in this repository

- `data/aps_curia_texts_de.jsonl.gz`: full Curia Vista texts (ws.parlament.ch OData) for the 298 APS-gold affairs, written by
  `fetch_aps_texts.py`. Bulk copy of third-party full texts; not redistributed. The script and its query are here.
- `data/curia300.json`: the 300-affair Curia test set **with** full texts. Replaced here by `data/curia300.labels.json`, the
  same 300 records with the `text` fields removed (ids, split, gold tags, BFH scores, titles and the rest unchanged).
  `build_data.py` rebuilds the full file from Curia Vista.
