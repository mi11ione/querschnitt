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
