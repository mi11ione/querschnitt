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

## 2026-10-14 09:30 CEST — S21 Basel-Stadt with the canton's own labels as examples (written after S20, before any S21 call)
Question: do the partner's labels, used as examples (no training), raise accuracy on the same human cantonal gold?
Items and gold: as S20 (2,437 affairs, «Thema 1»). Two folds by OPD affair id parity; each item sees the five most similar
affairs of the OTHER fold (BM25 over OPD titles, query = title ×2 + first 400 characters of text — the S9 D3 retrieval) with
their «Thema 1», in the S9 D3 example shape ("Frühere Geschäfte mit ihren Themen (zur Orientierung): - title → Thema: code
(name)"), between the list and the item. Readings (D4 shape): identity order with examples, plus the S20 permuted order without
examples for every item (run where S20 did not); decision = top of the mean of the two.
Primary: top-1 = Thema 1, paired against S20 on the same items (paired bootstrap 2,000). Secondary: Thema 1 or 2, top-3,
lanes. Reported as measured.

## 2026-10-14 14:30 CEST — S22 Italian on human labels (written before any S22 call)
Items: the S9 held-out federal affairs whose OPD Italian title differs from the French one (1,350 of 1,357); gold = APS editors'
chapter. Italian input: OPD `title_it` + `title_long_it` + the Italian submitted text from OPD's texts export («Testo
depositato», first 1,500 characters) where it differs from the French text, else title only. Design D1 in the Italian frame
(S6 frames; chapter names in Italian, subtopic names German as published): both code orders, one subtopic request over the
top 2–3 chapters, chapter read back. Primary: top-1 Italian vs the S9 D1 German top-1 on the same items (paired bootstrap
2,000). Secondary: top-3; Italian with vs without submitted text. Reported as measured.

## 2026-10-14 17:10 CEST — S23 evidence on production rows (written before any S23 sample is drawn)
Items: 200 evidence rows of the corpus run (`runs/ev`, `runs/main`), drawn uniformly at random (random.Random(20261023)) among
2026 affairs with a stored quote: 100 chapter quotes (the shipped APS chapter) and 100 "Digitalisierung" quotes (flagged or
please-check rows). Packet per item: parliament, type, title, long title, text excerpt as the model saw it, the topic name,
and the quoted sentence. Gold: blind Claude annotators A and B (Y = the sentence supports that the affair concerns the
topic, N = it does not), tie-break C. Outcomes: support rate per kind (Wilson 95%), overall; substring check rate (code);
compared descriptively with S12 (0.850, spike). Reported as measured.

## 2026-10-14 20:20 CEST — S25 fresh APS-labelled federal affairs, the shipped design held out (before any S25 item is scored)
Why: D4 (shipped) was designed after S9's results and measured on the same 1,357 items; S25 tests it on items never seen.
Items: federal affairs with an APS editors' chapter recovered from Wayback captures of anneepolitique.swiss process pages
that are NOT in the S5 (297) or S9 (1,357) sets and NOT in the example pool; parsed with the S9 rules (chapter + main
subtopic). Whatever the number recovered (target ≥ 300), all are used. Input: the production input from OPD (`data.py`),
the production pipeline unchanged (D4 for federal affairs: five BM25-nearest APS-labelled examples from the S5+S9 pool,
two code orders, read-back), run in a separate run dir on the same build.
Primary: shipped chapter top-1 vs APS editors (Wilson 95%, outward). Secondary: top-3; lanes (agree/disagree precision);
coverage–precision when routing by calibrated p (calibration map fitted on S16 only); keyword baseline (S9 frozen rule).
Reported as measured.

## 2026-10-14 22:40 CEST — S26 editor decisions as examples on the S19 topics (written after S19's annotations exist, before any S26 call or S19 analysis)
Question: does the shipped feedback loop (an editor's decisions become examples; `examples.topic_examples`, P8.5 shape: the 4
BM25-nearest decided affairs, "Beispiele, von einer Redaktorin entschieden") raise precision on narrow new topics?
Items: the S19 packets (wolf 164, hitze 468, ki-schule 142) with the S19 judge consensus as gold. Per topic, 30 items drawn at
random (random.Random(26) over the pid-sorted packet) are the editor's first decisions (their gold Y/N); every other packet
item is re-scored with the shipped yes/no rule (order a; order b when 0.1 < p < 0.9; flag at mean p ≥ 0.5) with examples.
Primary: precision of flags on the re-scored items vs S19's flags on the same items (paired bootstrap 2,000). Secondary:
weighted recall (S19 estimator), flags per topic. Reported as measured.

## 2026-10-14 23:05 CEST — S27 a second, stricter check on flagged affairs for new topics (after S19/S26 results; dev/test split fixed now)
Question: does a verification step on flagged affairs raise precision of one-sentence topics without losing recall?
Design V: affairs flagged by the shipped yes/no rule get one more closed question, same frame and input (title + long title):
"Ist «{name}» ein zentrales Thema dieses Geschäfts – nicht nur am Rande erwähnt oder bloss ähnlich?" A = Ja, zentral /
B = Nein (order a; order b when 0.1 < p < 0.9; keep the flag at mean p ≥ 0.5); de/fr/it frames as the yes/no step.
Dev (tuning allowed: wording of the verification only, at most 3 variants): the 577 affairs of the S13 census week
(30 Sep–6 Oct 2026) for the three S13 topics, gold = blind Claude judge A/B + tie-break C on every flagged affair and on
60 random unflagged affairs per topic (S19 guide). Test (held out, no tuning): the S19 packets and gold; the single variant
chosen on dev is applied once. Primary (test): precision of flags with V vs without (paired bootstrap over items); secondary:
recall among judged positives, per topic. Reported as measured.
