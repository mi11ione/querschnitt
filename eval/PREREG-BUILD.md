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
Amendment 2026-10-14 23:10 CEST (before any S27 call): the S13 dev week holds only 33 flags (wolf 4, hitze 24, ki-schule 5),
too few to choose between wordings. S27 therefore uses the single wording above with no tuning and no dev step; it is applied
once to the S19 packets (test). Everything else unchanged.

## 2026-10-15 00:19 CEST — Erratum: header clock times (no change to any design)
The clock times in the headers of S19–S27 were typed by hand and are later than the moment each entry was fixed. The
authoritative time is the sha256 log (`eval/PREREG-BUILD.sha256`, UTC; CEST below), and every entry was hashed before the
first model call of its test (first ledger line) or, for S23, before its sample was drawn:
S19 02:45:41 → first call 02:46:06 · S20 07:35:16 → 07:35:44 · S21 09:23:15 → 09:23:50 · S22 14:19:25 → 14:19:36 ·
S23 17:05:40 → packet written 17:09:04 · S25 20:02:43 → 22:59:24 · S26 22:23:05 → 22:23:39 · S27 22:46:30 and its
amendment 22:46:46 → 22:47:12 (all 14 Oct 2026). Header times from this entry on are taken from the clock when written.

## 2026-10-15 01:29 CEST — S25 amendment: a determinism fix before the final score (after two pre-fix readings were seen)
Found while scoring S25: the BM25 example retrieval (`examples.BM25.top`) summed over `set(q)`, whose order Python
randomises per process, and broke ties by insertion order; a restarted run (the S25 run restarted during the Public AI
outage of 15 Oct 00:00–00:39) could therefore ask a different five examples for the same affair, and composing in another
process could miss the chain that was asked. Two compositions of the finished run were already seen, both with the old code:
904 affairs scored, top-1 0.7035 (636/904), and 905 scored, 0.6994 (633/905). Fix (a bug fix, not a design change): sorted
terms and an index tie-break, so every process picks the same neighbours (test: same neighbours under 12 hash seeds).
Final S25 (primary, reported as measured): the fixed code; the chains it asks that the run does not hold are completed in
`runs/s25` on the same build, then all 927 affairs are scored once with `eval/s25/analyze.py`. Both pre-fix readings are
reported next to it. Nothing else changes (items, gold, metrics, calibration map fitted on S16 only).

## 2026-10-15 01:54 CEST — S25b plain list prompting on the S25 items (after the S25 result; before any S25b call)
Why: the held-out S25 has only the keyword baseline; the design set's plain list prompting baseline (S9 D0, 0.655) is on
other items. Design D0 exactly as S9: the chapter prompt without examples in identity code order (d0a) and in the S1
permutation (d0b); chapter = top of the geometric mean of the two readings. d0b is the S25 run's second reading (already
asked, no examples); d0a is asked now for every S25 affair that does not already hold it (the 10 French/Italian affairs
hold it as their first reading), same build, same inputs, `runs/s25`. Primary: D0 top-1 vs APS editors (Wilson 95%,
outward) and the paired difference shipped − D0 (bootstrap 2,000 over items). Reported as measured. Also reported, not
pre-registered: subtopic and hierarchical metrics on S25 with the eval/s16/hierarchical.py definitions
(eval/s25/hierarchical.py, already computed from the S25 rows, no calls).

## 2026-10-15 16:36 CEST — S28 no-prefill mode on the S25 held-out items (before any S28 call)
Why: the CSCS endpoint on 18 Oct may not continue an assistant message; the labelled fallback `QS_PREFILL=0` (one user
message: the measured prompt plus a line asking the answer to begin with the JSON opening; the code read from the first
token after that opening, from its `top_logprobs`, else from the generated text) has never run against a real model.
S28 measures what it costs against the shipped prefill design on the same held-out items.
Items: the 927 S25 affairs (eval/s25/items.jsonl, ids eval/s25/ids.txt), APS editors' chapter as gold, inputs from
`../data/inputs.jsonl.gz`, unchanged. Design: the shipped pipeline unchanged (D4 for federal German affairs with
neighbours: five BM25-nearest S5+S9 pool examples, two code orders, read-back over the subtopics of the top 2–3 chapters;
D1 otherwise), with `QS_PREFILL=0` in the environment, via `ops/run-start.sh runs/s28 --inputs ../data/inputs.jsonl.gz
--ids eval/s25/ids.txt --steps ch sub --conc 2 --max-rate 0.5 --cap 3`, into a new run dir `runs/s28` whose lock is
written before the first call with the S25 build (vllm-0.23.1rc1.dev1029+ga601a9d99-tp8-pp2-dd237840, mode no-prefill),
so a call on any other build stops the run. Model `swiss-ai/apertus-v1.5-8b`, no system message. First a 20-item smoke
run (`--limit 20`, the same command); its calls are part of the measurement if the code is unchanged afterwards, else an
amendment is appended here before continuing. Calls that fail are retried by resuming the same run dir; affairs that never
complete are reported as missing. Decisions are composed with `compose.decide` in no-prefill mode (no calibration: the
lane is the readings rule only, pass = the two code orders agree, or one reading with top p ≥ 0.9).
Primary: no-prefill chapter top-1 vs APS editors (Wilson 95%, outward) and the paired difference shipped prefill (S25
final, eval/s25/decisions.jsonl) − no-prefill on the same affairs (bootstrap 2,000 over items, seed 2026, bounds outward).
Secondary: top-3 (and its paired difference); the readings lane: pass share and precision (Wilson), next to S25's
readings lane and calibrated lane; chapter agreement prefill vs no-prefill; per step row, how the code was read:
`logprobs` (codes from top_logprobs), `text` (a single code at log-probability exactly 0.0, the engine's text fallback;
an upper bound, since a logprob read could in principle look the same), `unparseable` (no listed code; such a row is
composed as the shipped code would compose it, and the affairs it touches are counted); list-price USD and calls per
affair vs S25. Reported as measured.

## 2026-10-15 16:40 CEST — S28 amendment: a read fix after the smoke run (before any further S28 call)
Found by the 20-item smoke run (stopped after 28 calls, 9 affairs complete; S25 build, no-prefill): every row's mass in
the listed codes was 0.0 (best code log-probability -14 to -26). Apertus writes the JSON opening's quote as its own token
(` "`); `client.read_codes_after` already read that token once the text ended with `{"kapitel":`, so it returned the
quote token's rare merged alternatives (` "B`), not the code distribution, which is on the next token. Fix (a bug fix,
not a design change; prompts and prompt ids unchanged): before the quote, a token is read only when the generated token
itself carries quote and code (` "B`); test `test_no_prefill_reads_the_code_token_not_the_quote`. The fake endpoint sent
the whole opening as one token, so the tests had not seen this. The smoke rows are kept apart in `runs/s28-smoke1` and
never scored (their codes were read wrongly; the ids would otherwise be reused as cached). Then: a new `runs/s28` (same
pre-written S25 lock), a second 20-item smoke run with the fixed code, whose calls count in the measurement if the code
is unchanged after it, then the full run. Design, items, gold and metrics as pre-registered. The 28 smoke calls are
reported in the cost.

## 2026-10-15 16:47 CEST — S29 Ticino Gran Consiglio own scheme in Italian (before any S29 call)
Question: does a parliament's own scheme handed over as a file work for an Italian-speaking parliament, measured against that
parliament's own labels? (All earlier human-labelled tests were German, plus Bern's French titles.) Sources searched:
`eval/s29/SOURCES.md`.
Items (`eval/s29/items.py`, data only, run before this entry): every Ticino Gran Consiglio affair (OPD body TI) in
`../data/inputs.jsonl.gz` begun 1 Jan 2023–11 Oct 2026 with a lead-department entry in OPD's contributors export (role
`leading_department`, position 1): 2,274 affairs, joined by OPD affair id, 2,267 with text. Gold = that entry. The six named
units map to the option of the same name; «Consiglio di Stato del Ticino» and «Gran Consiglio (Ticino)» map to the none option.
Scheme: `schemes/ti-dipartimenti.yaml` (kind named): the 6 unit names verbatim in Italian, alphabetical, codes A–F, then
G = "Nessuno di questi (Consiglio di Stato nel suo insieme o Gran Consiglio stesso)". No descriptions, nothing tuned. The frame
is Italian. `named_prompt` reads the file's `de` slots, which hold the Italian text verbatim. The fixed block labels in code
("Geschäft:", "Titel:", "Text (Auszug):") stay German as shipped. Input: the production input block (title, long title, first
1,500 characters of the text chosen by `data.py`).
Readings as shipped (S20/compose.py): identity order; the second code order (random.Random(7) permutation) when the first top
probability is below 0.9; decision = top of the mean.
Primary: top-1 = gold (Wilson 95%; point value truncated, bounds rounded outward) on the 1,685 items whose input block names
none of the six units (lower case, typographic apostrophes folded). A Messaggio's header prints the competent department
(«competenza»): 589 of the 2,274 inputs name a unit, 487 of them Messaggi. This was measured on the inputs before any call.
Baselines on the same items: the majority gold label (computed at scoring) and the frozen keyword stems
(`eval/s29/keywords_frozen.json`, title only). Paired difference Apertus − keyword: paired bootstrap, 2,000 resamples,
random.Random(2026).
Secondary: the same on all 2,274 items as fed; items whose gold is one of the 5 Dipartimenti; top-2 and top-3 contain gold;
lanes (orders agree / disagree) with accuracy each; by affair type; confusion matrix. S18 (Bern) and S20 (Basel-Stadt) are
reported beside the result but not compared with it: the schemes differ and so do the chance rates. No examples arm in S29 (an
S21-style arm would need its own entry first).
Run: batch runner into `runs/s29` (`--ids runs/s29/ids.txt --topics --steps --named ti-dipartimenti --conc 2 --max-rate 0.5
--cap 3`), `swiss-ai/apertus-v1.5-8b`. The build is locked before the first call to fingerprint
vllm-0.23.1rc1.dev1029+ga601a9d99-tp8-pp2-dd237840: a call reporting another fingerprint stops the run, and no row of another
build is used. Never a system message. Reported as measured.

## 2026-10-15 17:59 CEST — S30 narrow one-sentence topics: a generated scope as a third check on flags, held out (before any S30 test call)
Question: does a generated inclusion/exclusion scope, asked as a third closed question on flags, raise the precision of
narrow one-sentence topics over the shipped design (yes/no + S27 check) on fresh data, without losing recall?
Dev (done, tuning allowed, 4 variants; `eval/s30/dev_*`, the S19 packets with the S19 judge gold, S19/S27 rows; dev
USD 0.0343): scope = one plain generation request per topic, user message only (`eval/s30/common.py` SCOPE_PROMPT:
include ≤ 8 / exclude ≤ 6 keywords per language, JSON); scope question = «Gehört das folgende parlamentarische Geschäft zum
Thema «{name}»?» + «Dazu gehört: …» + «Nicht dazu gehört: …, Geschäfte, deren Titel das Thema nicht erkennen lässt.», A/B,
two-order rule (`common.scope_prompt`). Dev precision / recall of flags (wolf · AI in schools · heat): shipped 0.444/0.444 ·
0.250/1.000 · 0.771/0.970; V1 yes/no + scope question 0.348/0.889 · 0.333/0.667 · 0.836/0.901; V2 yes/no + contrast
question (topic vs its generated neighbours) 0.241/0.778 · 0.176/1.000 · 0.830/0.966; V3 scope question alone = V1 (on
all 774 dev items its flags are a subset of the yes/no flags); V4 scope question + S27 check 0.667/0.444 · 1.000/0.667 ·
0.919/0.879. Chosen after seeing dev (highest mean F1, 0.74 vs shipped 0.56): V4, asked on the yes/no flags (identical
decisions to V4 on all dev items, and its test cost is the shipped cost plus one call per flag).
Test (held out, no tuning; frozen code `eval/s30/{common,run_common,run,flags,build_packet,analyze}.py`):
Topics (one German sentence each, `eval/s30/sentences.json`): «Lichtverschmutzung …», «Drohnen …», «Pestizide und
Pflanzenschutzmittel …»; never used before. Population: every affair with a title begun 16–31 Mar 2026 in
`../data/inputs.jsonl.gz` (1,316; S19 used Aug–Oct). Per topic, one shipped topic generation (adhoc.TOPIC_PROMPT →
adhoc.build_topic, as Neues Thema) and one scope generation, frozen in `eval/s30/topics.json` before scoring.
Arms: shipped = yes/no flag (mean p ≥ 0.5) kept by the S27 check (mean p ≥ 0.5) (the product's verified flags);
variant = shipped ∧ scope question (mean p ≥ 0.5); keywords frozen in `eval/s30/keywords_frozen.json`. Secondary: the
yes/no step alone; yes/no + scope question without S27. Build vllm-0.23.1rc1.dev1029+ga601a9d99-tp8-pp2-dd237840 pinned,
max rate 0.5/s, 2 workers, cap USD 2.
Gold sample per topic: every affair flagged by any arm (all yes/no flags) or by keywords, plus 120 random others
(random.Random(20261030) over the id-sorted list). Packet: parliament, level, type, date, title, long title (300), text
excerpt (300), the topic sentence; no model output; blind Claude subagents A (shuffled) and B (reverse order), Y/N; a third
subagent C on A≠B. Outcomes per topic and pooled: precision of flags (Wilson 95%), weighted recall (stratified bootstrap
2,000), paired differences variant − shipped in precision and recall (same bootstrap). Points truncated, intervals outward.
Product rule: the variant goes into the product only if the pooled precision difference interval lies above 0 and no
recall-difference interval (pooled or per topic) lies below 0; otherwise the product stays as it is. Reported as measured.

## 2026-10-16 11:33 CEST — S33 the S25 held-out affairs read from the French text (before any S33 call)
Why: production reads federal affairs from the German text, so the held-out S25 (927 APS-labelled federal affairs, 926 read
in German) says nothing about French; S22 measured Italian on the design set (S9) with D1. S33 measures French held out.
Items and gold: the 927 S25 affairs (`eval/s25/items.jsonl`, ids `eval/s25/ids.txt`), gold = the APS editors' chapter.
French input (`eval/s33/run.py build`, data only, run before this entry; no call): from OPD's bulk export `../data/opd-new`,
`title_fr` and `title_long_fr` (cleaned as `data.py`), and the French text of the affair's own OPD text row in production's
federal order (`data.CHE_ORDER`, «Texte déposé» first), first 1,500 characters, used only where it differs from the German
text of the same row; else French title + long title only; no attached documents. Counts: 580 with French text, 347 title
only (291 of them were read in S25 with a German document text, 56 had no text in German either); no affair has a French long
title (none has a German one); all 580 French texts differ from the German. One affair (153932) is French in production
already; its S33 input is identical to the S25 one and it is kept. Other fields as the production input row; lang = "fr".
Design: what production runs for a FRENCH federal affair today. `engine.ch1_prompt` shows the five APS-labelled examples
only for federal affairs with lang = "de", so a French affair gets D1 read-back WITHOUT examples: `prompts.chapter_prompt(a,
perm)` in the French frame (lang "fr"; chapter names French, subtopic names German as published), identity order; the S1
permutation as second reading only when the first reading's top p < 0.9 (`engine.need_ch2`; S22 asked both orders always);
one subtopic request over the top 2–3 chapters (`prompts.subtopic_prompt`, French frame); the chapter read back
(`compose.chapter_decision`), composed by `compose.decide` as the export composes it.
Run: the batch runner (`eval/s33/run.py run` = `querschnitt.batch run --inputs eval/s33/inputs_fr.jsonl.gz --out runs/s33
--ids eval/s25/ids.txt --steps ch sub --topics --conc 2 --max-rate 0.6 --cap 0.5`), model `swiss-ai/apertus-v1.5-8b`, never
a system message; the lock in `runs/s33/state.json` is written before the first call to build
vllm-0.23.1rc1.dev1029+ga601a9d99-tp8-pp2-dd237840, so a call on any other build stops the run and no row of another build is
used. Budget ≤ USD 0.5 list price.
Primary: (1) French top-1 vs APS editors (Wilson 95%); (2) the paired difference French − German on the same affairs, German =
the shipped S25 decisions (`eval/s25/decisions.jsonl`, D4: five examples on the German text), paired bootstrap 2,000 over
affairs, random.Random(2026), percentile 2.5/97.5.
Secondary: (a) French vs German with the SAME design. The full German D1 read-back cannot be composed without new calls:
`runs/s25` holds the subtopic request for the D1 chapter set (from the no-example readings) for 171 of the 927 affairs only
(716 missing; coverage counted before this entry, no accuracy computed), so it is skipped. Instead, same design at the level of
the chapter readings (no read-back): top of the geometric mean of the readings production asks for a no-example affair
(identity order; S1 order where the first top p < 0.9; else the first reading) in both languages — German from the identity-order
no-example reading `eval/s25b/raw.jsonl` and the S1-order rows of `runs/s25` (the 40 affairs whose document text the 16 Oct
inputs rebuild trims are matched with their S25-time input, the untrimmed document head, verified by prompt id); French from
`runs/s33`; paired bootstrap as the primary. (b) top-3, French and German shipped. (c) lanes: readings agree / disagree (one
reading with top p ≥ 0.9 counts as agree) with share and accuracy each; also production's pass / please-check lane (calibration
map fitted on S16). (d) French with text (580) vs title only (347), German shipped on the same affairs.
Points truncated, intervals rounded outward. Reported as measured.

## 2026-10-16 14:03 CEST — S34 a trained classifier on the shipped design's 1,654 APS labels vs the shipped design on the 927 held-out (before any S34 fit)
Why: the held-out S25 compares the shipped design with keywords and with list prompting, never with a classifier trained on
APS labels. The shipped design already holds APS-labelled affairs (the example pool `data/eval/aps_pool.jsonl`, 1,654
affairs: S9 1,357 + S5 297, none in S25; counted before this entry). S34 asks whether a standard trained text classifier,
given those same 1,654 labels, beats the shipped design on the 927 held-out affairs. No model calls.
Train: the 1,654 pool affairs, label = the pool's APS chapter (24 chapters). Test: the 927 S25 affairs (`eval/s25/ids.txt`),
gold = the APS editors' chapter (`eval/s25/items.jsonl`). Input text for both: title + long title + text from the production
inputs `../data/inputs.jsonl.gz` (the fields the model sees; 16 Oct rebuild), joined with newlines; no other field.
Classifier (fixed now, nothing tuned on S25): scikit-learn, TF-IDF (word 1–2-grams, sublinear tf, min_df 2) concatenated with
TF-IDF (char_wb 2–5-grams, sublinear tf, min_df 2), then LogisticRegression (multinomial, lbfgs, max_iter 3000,
class_weight None); C chosen from {0.3, 1, 3, 10, 30, 100} by 5-fold stratified CV accuracy on the pool only
(StratifiedKFold shuffle, random_state 2026); refit on the full pool with that C.
Primary: (1) trained top-1 vs APS editors on the 927, Wilson 95%; (2) paired difference shipped − trained on the same 927,
shipped = the frozen S25 decisions `eval/s25/decisions.jsonl`, paired bootstrap 2,000 over affairs, random.Random(2026),
percentile 2.5/97.5.
Secondary: (a) top-3 trained vs shipped; (b) trained top-1 on the shipped pass lane and on the please-check lane; (c) learning
curve: trained top-1 on the 927 when trained on 25 % and 50 % of the pool (stratified subsample, random_state 2026, same C);
(d) agreement: share of the 927 where trained and shipped give the same chapter, and shipped top-1 on that share.
Points truncated, intervals rounded outward. Reported as measured, whichever way it goes.
