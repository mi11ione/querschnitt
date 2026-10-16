# Pitch scripts (Thu 15 Oct — re-time against the real demo; numbers from eval/claims.tsv only)

Rules: the screen shows what has actually run (scored share, last night's log); every spoken number is in the Prüfstand;
wherever a number comes from the AI judge, the sentence says so. Three numbers carry each pitch. Check with
`python3 tools/claims_check.py docs/PITCH.md`.

## Gate 1 — 5 min live demo + 3 min Q&A (Christian Gutknecht, OpenParlData)

| Time | On screen | Said (gist) |
|---|---|---|
| 0:00–1:30 | Überblick (the atlas) → Digitalisierung → Karte → «Der Kanton Bern strebt digitale Souveränität an» → decision graphic and quote → `[1]` (name set before the slot) | "OpenParlData has no topic field. This is every affair since January 2025 from your exports — one map per topic, same scale. Each label is a choice from a closed list. Bern is bilingual, so the chapter is read twice, in German and in French; here they disagree, so it goes to a person — that is the lane working. This sentence from the draft law supports the topic. `[1]` — confirmed, with who and when, next to the inferred row. In a minute I will ask you for a topic you track by hand." |
| 1:30–2:10 | Neues Thema: Christian names a topic | Terms appear, decisions stream in for last week. "No training. It is now a file in the nightly job." |
| 2:10–3:00 | Prüfstand, human labels first | "927 federal affairs labelled by the APS editors that we never looked at while building, registered in advance: the shipped chapter is right in 69.6% across 24 chapters, keywords 18.6%. Two thirds of these pass without a check and are right in 81.2%; the rest go to a person. Cantonal and communal affairs are often title-only — about half of them go to a person; the overview shows that load per week. The trail behind every number is in the repo." |
| 3:00–3:40 | The Anbindung view (one prepared screen, no live terminal): last night's log and the cost line on top, then the `topics` migration in OPD naming, the Hop pipeline that loads the bulk file, a `GET /changes?after=` page | "These are the merge-request files. Inferred and confirmed rows stay apart; every row names the build that made it. Model cost at list price: USD 0.333 per 1,000 affairs." |
| 3:40–5:00 | `make eval GOLD=…` live on a POLITmonitor/DVS export if one came at the deep dive; otherwise back to the held-out row in the Prüfstand | With their file: "Your labels, scored now: here is the number, with its interval, on affairs we never tuned on — and your labels become examples." Without: "One topic field for every parliament: every label from a closed list, with its sentence and its lane; 0.696 on affairs we never saw, two thirds pass without a check. The migration, the loader and the evaluation task are ready as a merge request — we would like to file it with you." |

Q&A cards: an endpoint without prefill (measured on the held-out affairs: 0.705 without, 0.696 with, paired −0.008 [−0.022, +0.004] — the fallback costs nothing measurable; the morning probe picks the mode) · who owns a wrong label (the parliament's editor: inferred rows say they are inferred, a confirmation or rejection is a new row with who and when, nothing is overwritten — CONTRACT §1) · 0.696 vs 0.740 (0.740 is on the 1,357 affairs the design was chosen on; 0.696 is the fresh set, the number we stand behind) · what the examples add (held out: plain list prompting 0.654 on the same affairs, paired +0.041 [+0.016, +0.067]) · hierarchy (held out, computed after the result: subtopic top 1 0.497, hierarchical F1 0.604) · APS licence (chapters in the public feed; subtopics internal until APS agrees) · another scheme (`bs-themen.yaml`,
`be-directorates.yaml`: a file) · where it runs (`lite` on the current VPS next to OPD's Postgres; the model endpoint must return log-probabilities — the hour-1 probe checks it) · build changes
(refit + quality gate + `GET /changes`) · recall of ad-hoc topics (judge-based 0.659 on titles; an editor's examples lifted precision on heat protection, +0.038, not recall) · who the
judge is (Claude runs + Qwen; matches APS editors on 0.790 of chapters; says yes to 27 of the 30 DVS items) · new narrow topics (one sentence casts a wide net — wolves 0.225 precision of flags; a second "is it central?" question and, on
fresh topics, a generated scope raise precision of flags from 0.642 to 0.761 (S30); keyword lists stay more precise there, 0.944) · the DVS 27/30
is not held out (the question was written with those items in view) · Romansh (German prompt; not measured).

## Finals — 5 min, jurors who did not read the case (one user, three numbers)

The user: the person at the Digital Public Services Switzerland (DVS) office who tracks what parliaments do about
digitalisation — today by keyword search, in three languages. Three numbers carry the pitch: on the 2026 census, keyword lists are right
in 0.756 of their hits and Querschnitt's flags in 0.905 (both against a blind AI judge); 0.696 on affairs the system
never saw, with two thirds decided at 0.812; USD 0.333 per 1,000 affairs. Everything else is for questions.

| Time | Beat |
|---|---|
| 0:00–0:25 | (German, then French; no English, or the beat runs over) "About 90 Swiss parliaments, about 50 new affairs a day on average — and no topic field. Someone who tracks digitalisation searches keyword by keyword, in three languages." |
| 0:25–1:15 | «Neueste Woche», the landing view (already loaded before the slot): read the line under the header — «Apertus ordnet die Geschäfte einem von 24 Themen … rot: eine Person prüft» — then the headline (`«Woche 40: 758 Geschäfte …»` on the 15 Oct export). Point at examples from different parliaments in German and French (Italian where the week has one), each with the sentence that supports its topic. "Every topic is a choice from a closed list, with its sentence. Where it is unsure, a person decides — the red tick." Open one: the plain sentence above the readings says why. |
| 1:15–1:55 | Digitalisierung (`t` → «Digi») → the map: every parliament with flagged affairs since January 2025. "In our 2026 census — the Prüfstand has it — 651 affairs in 57 parliaments were flagged. A blind check found 0.905 of the flags right; keyword lists, 0.756 of their hits. That check is an AI judge, not a person; the trail is in the repo." |
| 1:55–2:45 | Prüfstand (`b`), the lead block. "Tested against 927 federal affairs labelled by the editors of Année Politique Suisse and never seen while we built it, registered in advance: across 24 chapters it picks theirs in 69.6% — keywords manage 18.6%. Two thirds it decides on its own, and is right in 81.2% of those; the rest it hands to a person. Across all parliaments about half go to a person — the overview shows fewer than two per parliament a week." |
| 2:45–3:35 | Neues Thema in a second tab opened before the slot (`#neu?limit=25`; on the static site the recording plays). Live: "Name a topic in one sentence." While it works: "Apertus writes search terms in German, French and Italian, then reads last week affair by affair and decides yes or no." Recording: "This is a recording of a real run on 15 Oct" — keep talking through the first 8 s until the first hit. Close: "No training. Saved, it is a file in the nightly job." |
| 3:35–4:25 | Anbindung (`i`): «letzte Nacht» and the cost line at the top. "It runs on Apertus, Switzerland's open model: USD 0.333 per 1,000 affairs at list price. When the endpoint went down on 15 Oct, the new affairs waited in a queue and were scored once the same model build answered again — nothing lost, nothing mixed." |
| 4:25–5:00 | Stay on Anbindung: the repository block with its QR code. "The open trail: repo, topics file, the Prüfstand with raw logs and blind annotations. One topic field for every parliament in OpenParlData — ready to hand over." |

Q&A cards for the finals: own schemes in three languages (Bern's directorates 0.651 German / 0.650 French; Basel's 46
themes; Ticino's departments in Italian 0.647 vs keywords 0.219) · the 15 Oct night in detail (the cut pass and the drain
were started by hand that day — a fetch bug in the scheduled run, since fixed; automatic resume after an outage exists
since then) · why Claude appears at all (annotator in the evaluation only; Apertus makes every decision that ships).

TO UPDATE when measured: Neues Thema timing on the event endpoint (no number is spoken until it is measured; the
recording on the site is a real run of 98 affairs, played at ×4).
