# Pre-registration, build week (append-only; each entry is hashed into PREREG-BUILD.sha256 before its result exists)

Earlier entries: `bern/ideation2/PREREG.md` (hash-locked 13 Oct) and `PREREG-ADDENDA.md`. Same conventions: Wilson 95% for
proportions, paired bootstrap (2,000 resamples, percentile) for differences, results reported as measured whatever they show.

## 2026-10-14 01:05 CEST — S16 read-back combined with examples (written before any S16 call)
Items: the 1,357 S9 held-out federal affairs (APS editors' chapter), same inputs as S9.
Design D4 (production rule for federal affairs): prior P4 = arithmetic mean of the S9 rows d3m (identity order, five APS-labelled
examples) and d0b (S1 order, no examples); one subtopic request over the top 2–3 chapters of P4 (S9 rule, top chapter first); the
chapter is read back from the best subtopic (score = p(subtopic) × P4(chapter)). Existing S9 d1 rows are reused where the chapter list
equals P4's (the prompt is then byte-identical); the other items get one new call. Secondary D4s: as D4 but d0b used only when d3m's
top probability is below 0.9 (the corpus run's rule).
Outcomes: top-1 and top-3 of D4 and D4s; paired differences D4 − D3 and D4 − D1. Decision rule (fixed now): the corpus run ships D4
for federal affairs if its top-1 point estimate is ≥ D3's; otherwise the federal chapter is D3's top-1 and subtopics come from the
read-back call. Recalibration (isotonic, 2-fold cross-fitted) is fitted for the shipped design and reported as ECE before/after.

## 2026-10-14 01:20 CEST — S17 communal slice on the production run (written before any S17 sample or annotation)
Items: 200 communal affairs (numeric OPD body key = BFS commune number), begin date 1 Jan–11 Oct 2026, drawn uniformly at
random (random.Random(20261017).sample over the id-sorted list) among those with a shipped production chapter; affairs in the
S6 sample are excluded. Input shown to annotators = the exact block the production prompt contained (title, long title, first
1,500 characters of the chosen text), with parliament and type.
Gold: the S6 annotation guide unchanged; two blind Claude annotators (A in shuffled order, B in reverse), packet only; a third
blind run (C) decides where A and B differ on the first chapter. Consensus = A if A = B, else C.
Outcomes: shipped production chapter vs consensus, top-1 (Wilson 95%), by language and by lane (readings agree / please check);
top-3 from the chapter ranking; baselines on the same items: the majority chapter of the sample's consensus (computed after) and
the frozen S9 keyword baseline (`ideation2/spikes/s9-aps/data/keywords_frozen.json`). κ between A and B. Reported as measured.

## 2026-10-14 01:35 CEST — S18 Bern directorates on the production run (written before any S18 row is read)
Items: every Kanton Bern Grand Council affair begun 1 Jan 2025–11 Oct 2026 with a German or French title and a lead-directorate
entry in OPD's contributors export (role `leading_department`); the entry's first token maps to the 8 directorates (BKD, BVD,
DIJ, FIN, GSI, SID, STA, WEU); "GR"/"Grosser Rat" entries map to "none of these". Prediction: the `be-directorates` scheme file
(S6 prompt, title only, the affair's language), argmax over the 9 options. Outcomes: accuracy (Wilson 95%) overall, German vs
French titles, and on the affairs whose title exists in both languages (each language scored; paired difference). Baselines on
the same items: the S6 keyword stems (frozen 13 Oct, `ideation/spikes/s6-cantonal/scripts/be_scheme.py`) and the majority
directorate. Reported as measured.

## 2026-10-14 03:00 CEST — S19 three new ad-hoc topics, quality against a blind judge (before any S19 call)
Topics: the three S13 topics never used in any tuning ("Wolf und Grossraubtiere", "Hitzeschutz / Hitzewellen", "Künstliche
Intelligenz an Schulen"), question texts verbatim from `ideation2/spikes/s13-timing/s13.py`, as `schemes/adhoc/*.yaml`.
Population: every affair begun 1 Aug–6 Oct 2026 with a title (11 Oct export; 4,305). Decision: the shipped yes/no rule
(order a; order b when 0.1 < p < 0.9; flag at mean p ≥ 0.5). Keyword baselines frozen in `eval/s19/keywords_frozen.json`.
Gold sample per topic: every affair flagged by Apertus or by keywords, plus 120 random affairs flagged by neither
(random.Random(20261019) over the id-sorted list). Blind Claude annotators A (shuffled) and B (reverse), packet only (parliament,
type, date, title, long title; the topic question), Y/N; tie-break C on disagreements; Qwen-SEA-LION as a cross-family check
on the same packet. Outcomes per topic: Apertus precision (Wilson 95%), recall against the judge (weighted by the neither-stratum
sampling fraction; stratified bootstrap 2,000), the same for keywords, flags per topic. Reported as measured.

## 2026-10-14 07:50 CEST — S20 Basel-Stadt topics, human cantonal gold, scheme handed over as a file (before any S20 call)
Items: all 2,437 Grand Council affairs of Basel-Stadt OGD dataset 100086 (Jan 2019–Mar 2024; topics assigned by hand by the
canton's Kantons- und Stadtentwicklung), joined to OPD by number (Signatur = OPD `number`; 2,437 of 2,437 join).
Scheme: `schemes/bs-themen.yaml` — the 46 theme names verbatim from the dataset, alphabetical, codes A–Z then a–t, plus
"Keines dieser Themen"; no descriptions, nothing tuned; German frame. Input: the production input block (title, long title,
first 1,500 characters of the affair's text as chosen by `data.py`). Readings: identity order; a second code order
(random.Random(7) permutation) when the first top probability is below 0.9; decision = top of the mean.
Gold: «Thema 1». Outcomes: top-1 = Thema 1 (primary, Wilson 95%); top-1 ∈ {Thema 1, Thema 2} (secondary); top-3 contains
Thema 1; lanes (orders agree / disagree) with precision each; by affair type. Baselines on the same items: majority theme;
frozen keyword stems (`eval/s20/keywords_frozen.json`). Reported as measured.
