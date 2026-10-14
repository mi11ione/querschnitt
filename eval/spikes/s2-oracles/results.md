# S2: free label oracles + BFH baseline (13 Oct 2026, no LLM calls)

Folder: `~/Desktop/hackapertus/bern/ideation/spikes/s2-oracles/` (scripts/ = code, data/ = outputs). All numbers are **[measured]** unless marked [guess].
Python: `python3 -I`. BFH baseline: `arch -x86_64 .venv-bfh/bin/python -I` (see E).

## 0. Robots verdicts (RFC 9309 longest match via `gegenprobe/robots9309.py`; full texts in `data/robots_log.jsonl`)
| Host | robots.txt | Paths used | Verdict |
|---|---|---|---|
| ws.parlament.ch | 404 | /odata.svc/Business, /Tags | allowed |
| www.digitale-verwaltung-schweiz.ch | 200 (`*`: Disallow /application/* only) | /aktuelles/politische-geschaefte (1 GET) | allowed |
| web.archive.org | 404 | /cdx/search/cdx, /web/<ts>id_/… | allowed |
| minio.la.utexas.edu | **403** | /compagendas/datasetfiles/switzerland_government.csv (1 GET) | allowed under RFC 9309 §2.3.1.3 (4xx = "unavailable"). Note: stdlib treats 401/403 as deny-all |
| swissvotes.ch | 200 (Crawl-delay 10, Disallow /auth/) | /page/dataset/swissvotes_dataset.csv (1 GET, 10 s gap) | allowed |
| huggingface.co | 200 (`Allow: /`) | /api/…/tree, /api/models, /resolve/main/… | allowed |
| us.aws.cdn.hf.co (HF LFS redirect target) | 404 | signed blob URLs | allowed |
Not touched: data.bs.ch, api.openparldata.ch, gitlab.com, anneepolitique.swiss (live site).
Politeness: one UA, ≥1.2 s per host, backoff, fail closed on 429/5xx. No 429 seen. Curia returned an empty body twice for 2020-Q2 (each language); the script fell back to monthly windows, which worked. **One lapse:** I started the clean-pool text job while the main Curia job was still running. That put 2 processes on ws.parlament.ch for about 5 s (about 4 requests at a combined gap of about 0.6 s). I killed the second job and chained it to run after the first.

## A. Curia Vista Sachbereiche (main oracle)
- Fetched Business (DE/FR/IT, SubmissionDate 2000-01-01 → today) in quarterly windows with a minimal $select: `data/curia_business_{de,fr,it}.jsonl.gz` (62,099 / 62,099 / 62,100 rows). Tags entity (28 × de/fr/it): `data/curia_tags.json`; name map `data/curia_tagnames.json`. Script `scripts/a_curia_fetch.py`, about 28 min.
- Tag sets are **identical across DE/FR/IT for all 62,100 IDs**, so one label set per affair.
- **Join:** OPD CHE `external_id` = Curia `ID` (e.g. 20237041), and OPD `number` = `BusinessShortNumber` ("23.7041"). Joined **61,853 / 62,100 = 99.6%**. Of the OPD CHE affairs with begin_date ≥ 2000, 61,852 / 61,857 are covered. Only 2 number mismatches (20230204: OPD "23.0204" vs Curia "23.204"; 20253909: "25.3057" vs "25.3909"); joining on ID avoids both. Examples: OPD 46912 ↔ 20000001 "00.001"; 138093 ↔ 20000003 "00.003".
- Output `data/oracle_curia.jsonl.gz` (61,853 rows): {opd_affair_id, curia_id, short_number, submitted, type, dept, tags[ids], titles{de,fr,it}, has_text_on_disk, clean_pool}.
- **Labels:** 59,589 tagged (96.3%). Mean 1.99 labels per tagged affair. Distribution 0:2,264 · 1:23,836 · 2:18,973 · 3:11,466 · 4:4,243 · 5:903 · 6+:168. (R1's "mean 2.4" came from a 3k sample from 2023 on; the full-period mean is lower.)
- **Frequency:** Wirtschaft 11,023 · Gesundheit 10,273 · Staatspolitik 8,852 · Finanzwesen 8,485 · Umwelt 7,596 · Int. Politik 7,339 · Soziale Fragen 6,975 · Sicherheitspolitik 6,649 · Verkehr 6,548 · Migration 4,827 · Medien u. Komm. 4,697 · Landwirtschaft 3,894 · Energie 3,703 · Beschäftigung 3,004 · Europapolitik 2,814 · Recht Allg. 2,504 · Bildung 2,451 · Sozialer Schutz 2,100 · Raumplanung 2,096 · Steuer 2,019 · Menschenrechte 1,947 · Strafrecht 1,817 · Kultur 1,740 · Wiss./Forschung 1,610 · Parlament 1,362 · Zivilrecht 1,146 · Int. Recht 826 · Gerichtswesen 434 (25:1 imbalance).
- **Coverage by year (n / tagged):** 2000: 1,370/293 (21%, an outlier). 2001–2008: 98–99%. 2009–2019: 97–99%. 2020: 3,239/3,184 · 2021: 3,331/3,250 · 2022: 2,971/2,887 · 2023: 2,834/2,761 · 2024: 3,118/3,042 · 2025: 3,580/3,468 · 2026: 3,064/2,957.
- **Types (tagged):** Fra. 17,143 · Ip. 15,679 · Mo. 11,946 · Po. 5,291 · Pa.Iv. 2,595 · A 2,515 · BRG 2,098 · Kt.Iv. 550 · Pet. 514.
- **All three Curia titles present:** 38,684 tagged affairs, of which 36,276 have an "Eingereichter Text/Texte déposé/Testo depositato" row in `census/texts.tsv.gz`. **Caveat:** texts.tsv.gz is metadata only (type and length). The text itself is not on disk, since the OPD bulk export has no texts and api.openparldata.ch/v1 is disallowed. So `has_text_on_disk` means "OPD has the text", not "we have it". IT titles are often missing in Curia for questions (Fra.); OPD's `title_it` fills more of them.
- **Clean test pool (submitted ≥ 2024-11-06, after the BFH model upload of 2024-10-30 and Space edit of 2024-11-05): 7,181 tagged affairs** (plus 241 untagged in that window).
  - Curia titles: DE 7,180 · FR 7,181 · IT 4,669. OPD titles: DE 6,938 · FR 6,719 · IT 6,556.
  - Types: Fra. 2,597 · Ip. 1,995 · Mo. 1,545 · Po. 478 · Pa.Iv. 193 · BRG 170 · A 138.
  - Every label is present; the rarest is Recht Allgemein with 118.
  - **Texts for the clean pool were fetched** from Curia (Title, SubmittedText, ReasonText, Description, InitialSituation): `data/curia_cleanpool_texts_{de,fr,it}.jsonl.gz` (7,435 rows each, 20 MB total). Rows with a body: DE 6,974 · FR 6,773 · IT 4,142. Untranslated items carry the text in its original language. The DE rows include **6,934 tagged affairs with German text** (stopword test), which is the ready DE test set.
- Licence: public OData, no key [measured]. Reuse terms: parlament.ch open-data page https://www.parlament.ch/de/services/open-data-webservices [not re-read; guess: free reuse with attribution].

## B. DVS digitalisation list
- 1 GET of the DE page (FR/IT/EN not needed). Raw copy `data/raw_dvs/politische-geschaefte_de.html`, parsed to `data/dvs_items.json`, script `scripts/b_dvs.py`.
- **30 items, 30/30 matched to OPD affairs**, all by exact link = OPD `url_external_*`. Number and title fallbacks were not needed.
  - Bodies: BE 12 · CHE 5 · ZG 3 · OW 3 · TG 2 · BS 2 · ZH 1 · AG 1 · BL 1.
  - OPD types: Government affairs 9 · Interpellation 8 · Motion 6 · **Consultation 5** · Postulate 2. The 5 consultations are in OPD as "Consultation" affairs.
  - 5 items have no "Body, Geschäftsnummer" line; their body comes from the OPD match.
- Positives only, rolling window, so it gives a recall check (n=30 today). Licence: public page, none stated.

## C. APS gold via Wayback
- CDX (`data/raw_cdx/`, script `scripts/c_cdx_overlap.py`):
  - Only **1,150 /articles/<id> URLs** are captured, mostly 301/302 redirects. Just **177 of the 9,258 OPD-linked article ids** have such a capture (about 1.9%), so sampling by article id is a dead end.
  - **4,301 /prozesse/<id> pages have a 200 HTML capture** (DE + FR). **1,740** have a slug ending in a Curia number found in OPD CHE (e.g. `…-brg-00-042`), and 1,692 of those OPD affairs also carry an aps_affair link.
- Fetched 300 random joined process captures (`id_` raw mode). Script `scripts/c_aps_fetch.py`, output `data/aps_gold_sample.jsonl`.
  - **298 OK, 2 connection errors.** Chapter found **298/298**, main subtopic 280/298. 23 of 24 chapters and 99 subtopics occur.
  - Each record: {opd_affair_id, curia_number, aps_process_id, aps_article_id, chapter_code, chapter_name, subtopic_id, subtopic_name, capture_url, keyword_chapters, join_quality}.
  - **Join quality:** 201 contain the OPD-linked APS article id in the page (strong); 80 have the Curia number in the page's Geschäftsnr (strong); 17 rely on the slug only (process pages bundle several affairs, so treat these as weak).
  - 199/298 have keywords from more than one chapter, so multi-label APS is recoverable. 293/298 also carry Curia tags, so the sample can seed an **APS↔Sachbereich crosswalk**.
  - Captures date 2019–2026 (2024: 106).
- **Yield and time:** 99% yield; 3.46 s per item wall time including the 1.2 s gap (median request 2.3 s).
  - Extending to all 1,740 slug-joined processes takes about 1.7 h.
  - The other 2,561 captured processes have no number in the slug but can be joined through the page Geschäftsnr; fetching them takes about 2.5 h more [guess: half to two thirds of them are CHE affairs].
  - Upper bound is therefore about 2–3k federal APS-labelled affairs, about 25–30% of the 9.5k linked ones.
- Licence: APS has no open licence (R1). Use chapter and subtopic labels as evaluation facts only, and do not redistribute article text. Wayback terms: https://archive.org/about/terms.php.

## D. Small oracles
- **CAP Swiss federal reports** (`data/raw_cap/switzerland_government.csv`, 1,951 rows, 21 majors): **1,011 joined (51.8%)**, all OPD "Government affairs". Output `data/oracle_cap.jsonl.gz`.
  - By period: 1978–89 4/703 (OPD has almost no pre-1990 CHE affairs); 1990–99 446/638; 2000–08 561/610.
  - Licence: open download, citation required (https://www.comparativeagendas.net/pages/How-to-cite).
- **Swissvotes** (`data/raw_swissvotes/swissvotes_dataset.csv`, 714 votes): 671 have a gesch_nr, **288 join OPD CHE** (257 of the 390 votes since 2000). All 714 have policy area d1e1; 382 have an APS link column. CC BY 4.0 (https://swissvotes.ch/page/dataset).

## E. BFH baseline (rcds/SwissParlTopicModelling + kapllan omikuji models)
- Files (`data/bfh/hf_trees.json`):
  - Space: only small files. `app.py`, `requirements.txt`, `install_packages.py`, `prepare_everything.py`, `id2label.json` (233 = 28 Haupt + 205 Unter), `label2id.json`, `topics_hierarchy.json` and README are copied to `data/bfh/` (.py saved as .py.txt).
  - Each model repo is about 0.68–0.70 GB: `vectorizer` 651 MB, 3 omikuji trees about 18 MB, train file 34 MB.
  - DE model uploaded 2024-10-30, **no licence tag** (HF API), so use it as a baseline only and do not redistribute.
- **What it expects** (from app.py and a pickle audit):
  - One free text per call. fastText lid.176 routes it to the de/fr/it model.
  - The `vectorizer` is a sklearn 1.4.2 `TfidfVectorizer` (11,515 features). Its tokenizer is `annif.analyzer.spacy.SpacyAnalyzer("de_core_news_lg").tokenize_words`, which lemmatises (tok2vec, tagger, morphologizer, lemmatizer, attribute_ruler, senter) and drops tokens under 3 characters.
  - **The whole de_core_news_lg pipeline is pickled inside**, so no separate spaCy download is needed. It does need spaCy 3.7.4, annif 1.1.0, omikuji 0.5.1 and numpy<2.
  - Output: omikuji Bonsai scores for all 233 labels; the Space shows those ≥ a user threshold (default 0).
  - "input_long" [guess] = title plus the long texts. I used Title + SubmittedText (or InitialSituation/Description) + ReasonText, HTML stripped.
- **Recipe that ran:**
  - `uv venv -p cpython-3.11-macos-x86_64 .venv-bfh` (on macOS the omikuji wheel is x86_64 only, so it runs under Rosetta; building from source needs a Rust toolchain, and none is configured).
  - `uv pip install scikit-learn==1.4.2 spacy==3.7.4 omikuji==0.5.1 "numpy<2" flask click nltk simplemma` and `annif==1.1.0 --no-deps`.
  - Load through the **allow-listed unpickler** `scripts/e_safe_load.py`. It refuses any global outside sklearn, spacy, thinc, numpy, scipy, annif.analyzer, confection, preshed and joblib (plus functools.partial, re._compile, builtins.getattr/slice). The audit found only library classes.
  - Runner: `scripts/e_bfh_run.py`.
- **Results on 500 random clean-pool DE affairs** (German text, all Curia-tagged; 28 Hauptthemen mapped 1:1, e.g. "Rechte und Freiheiten" = Menschenrechte). Values are micro-F1 / macro-F1 (micro P / R):
  - threshold 0.2: **0.692 / 0.636** (0.687 / 0.696)
  - threshold 0.3: 0.692 / 0.594 (0.773 / 0.626)
  - threshold 0.5: 0.620 / 0.509 (0.844 / 0.490)
  - threshold tuned on 150 dev affairs (0.25), scored on the other 350: **0.699 / 0.595**
  - top-1: 0.522 / 0.414 (P 0.882)
  - top-2: 0.657 / 0.570
  - oracle-k (top-k with k = gold count): 0.715 / 0.660
- **Cost:** load 12 s, vectorising 500 docs 15 s, prediction 2.4 s (single CPU, Rosetta). The whole 6,934-doc DE pool would take about 4 min [guess, linear]. Outputs: `data/bfh/baseline_results.json`, `data/bfh/baseline_predictions_de.jsonl.gz` (with subtopic scores ≥ 0.05). FR/IT were not run; they use the same recipe with about 0.68 GB per language.
- **Bar to beat on the Curia Hauptthemen: micro-F1 about 0.70, macro-F1 about 0.60–0.64** (DE, clean pool).

## Disk / processes
- Total data is 692 MB: the BFH DE model in `data/bfh/raw/` takes 647 MB, and `.venv-bfh` takes 366 MB. Both can be deleted after the build has copied what it needs.
- All fetch jobs have exited; no processes are left running.
