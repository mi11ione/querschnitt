# s14-neutrality: what is not in this repository

- `data/opd_subset.json` (6.2 MB): contributor rows (authors, co-signers with names and parties) and affair types for the
  S6/S8/S9/S10 affairs, extracted by `scripts/extract.py` from the OpenParlData export. A bulk extract of the export,
  not a result; rebuild with `scripts/extract.py` from the OPD export (`make data`). The aggregated results
  (`results.json`, `results.md`, `results_tables.md`) are here.
