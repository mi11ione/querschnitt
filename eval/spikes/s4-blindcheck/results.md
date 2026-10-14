# S4: blind check of the Apertus "Digitalisierung" flags (13 Oct 2026; no LLM spend)

Items: the 300 random affairs of S3 E6 (10 per DVS positive, same body and begin year; BE 120, CHE 50, ZG 30, OW 30, TG 20, BS 20, ZH 10, AG 10, BL 10), shuffled (seed 20261013), opaque ids T001–T300, one line each (parliament | type | title | long title ≤300 chars). Key with Apertus p(yes) (mean of the two answer orders, S3 e6a/e6b) kept in key.jsonl, never shown to annotators.
Annotators: two blind Claude agents, each reading only packet/GUIDE.md (DVS-scope definition) and packet/items.txt; A forward order, B reverse order. Outputs ann_A.tsv, ann_B.tsv; scoring in summary.json.

- Agreement 296/300, Cohen κ 0.904. A: 20 Y / 279 N / 1 ?; B: 22 Y / 276 N / 2 ?.
- Consensus gold (both Y): 20 of 300 = 6.7 % digitalisation affairs.
- Apertus flags (p ≥ 0.5): 18. **Precision 17/18 = 0.94** (the 18th, T107 "re-election of the data protection officer", is a split call: A N, B Y). **Recall 17/20 = 0.85** on the consensus gold (misses: T007 social networks and youth mental health, T116, T188 vehicle-owner data register — all p ≈ 0).
- With "either annotator Y" as gold (22): precision 18/18, recall 18/22.
- Combined with S3: recall 27/30 on the public DVS list items (titles only).
- Caveat: n is small (20 positives in the random set); inputs were titles + long titles only; annotators are agents from one model family (no cross-family check yet).

## Keyword baseline (what users do today), same inputs (titles + long titles, de/fr/it), keyword_baseline.json
Regex of 29 de/fr/it stems (digital, numéri, informati, ICT, cyber, e-government, eID, KI/IA/intelligenza artificiale, online, internet, elektronisch, software, Daten/données/dati, cloud, Plattform…), written by the lead after seeing S3's top-10 flagged titles (so it is, if anything, favoured).
- DVS public list recall: **21/30** (Apertus 27/30).
- 300 random affairs: 21 flags, 16 correct → precision **0.76**, recall **16/20** (Apertus 0.94, 17/20).

## Correction (lead, after S7)
The keyword numbers above were computed on titles in all available languages, a broader input than Apertus saw. On Apertus's exact input (title + long title in the affair's prompt language) the same regex gives: DVS list 21/30 (unchanged); 300 random affairs 18 flags → precision 15/18 = 0.83, recall 15/20 = 0.75 on the Claude-both gold (S7 reproduces this). Use these. With the majority-of-3 gold (Claude A, Claude B, Qwen-SEA-LION; S7): Apertus 18/18 precision, 18/21 recall; keyword 16/18, 16/21.
