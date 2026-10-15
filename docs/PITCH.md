# Pitch scripts (Thu 15 Oct — re-time against the real demo; numbers from eval/claims.tsv only)

Rules: the screen shows what has actually run (scored share, last night's log); every spoken number is in the Prüfstand;
wherever a number comes from the AI judge, the sentence says so. Three numbers carry each pitch. Check with
`python3 tools/claims_check.py docs/PITCH.md`.

## Gate 1 — 5 min live demo + 3 min Q&A (Christian Gutknecht, OpenParlData)

| Time | On screen | Said (gist) |
|---|---|---|
| 0:00–1:30 | Überblick (the atlas) → Digitalisierung → Karte → «Der Kanton Bern strebt digitale Souveränität an» → decision graphic and quote → Pult, `[1]` | "OpenParlData has no topic field. This is every affair of 2026 from your exports — one map per topic, same scale. Each label is a choice from a closed list. Bern is bilingual, so the chapter is read twice, in German and in French; here they disagree, so it goes to a person — that is the lane working. This sentence from the draft law supports the topic. `[1]` — confirmed, with who and when, next to the inferred row. In a minute I will ask you for a topic you track by hand." |
| 1:30–2:10 | Neues Thema: Christian names a topic | Terms appear, decisions stream in for last week. "No training. It is now a file in the nightly job." |
| 2:10–3:00 | Prüfstand, human labels first | "927 federal affairs labelled by the APS editors that we never looked at while building, registered in advance: the shipped chapter is right in 0.696 of 24 chapters, keywords 0.186. Two thirds of these pass without a check and are right in 0.812; the rest go to a person. Cantonal and communal affairs are often title-only — about half of them go to a person; the overview shows that load per week. The trail behind every number is in the repo." |
| 3:00–3:40 | The Anbindung view (one prepared screen, no live terminal): the `topics` migration in OPD naming, the Hop pipeline that loads the bulk file, a `GET /changes?after=` page, last night's log line | "These are the merge-request files. Inferred and confirmed rows stay apart; every row names the build that made it. Model cost at list price: USD 0.333 per 1,000 affairs." |
| 3:40–5:00 | `make eval GOLD=…` live on a POLITmonitor/DVS export if one came at the deep dive; otherwise back to the held-out row in the Prüfstand | With their file: "Your labels, scored now: here is the number, with its interval, on affairs we never tuned on — and your labels become examples." Without: "One topic field for every parliament: every label from a closed list, with its sentence and its lane; 0.696 on affairs we never saw, two thirds pass without a check. The migration, the loader and the evaluation task are ready as a merge request — we would like to file it with you." |

Q&A cards: who owns a wrong label (the parliament's editor: inferred rows say they are inferred, a confirmation or rejection is a new row with who and when, nothing is overwritten — CONTRACT §1) · 0.696 vs 0.740 (0.740 is on the 1,357 affairs the design was chosen on; 0.696 is the fresh set, the number we stand behind) · what the examples add (held out: plain list prompting 0.654 on the same affairs, paired +0.041 [+0.016, +0.067]) · hierarchy (held out, computed after the result: subtopic top 1 0.497, hierarchical F1 0.604) · APS licence (chapters in the public feed; subtopics internal until APS agrees) · another scheme (`bs-themen.yaml`,
`be-directorates.yaml`: a file) · where it runs (`lite` on the current VPS next to OPD's Postgres; the model endpoint must return log-probabilities — the hour-1 probe checks it) · build changes
(refit + quality gate + `GET /changes`) · recall of ad-hoc topics (judge-based 0.659 on titles; an editor's examples lifted precision on heat protection, +0.038, not recall) · who the
judge is (Claude runs + Qwen; matches APS editors on 0.790 of chapters; says yes to 27 of the 30 DVS items) · new narrow topics (one sentence casts a wide net — wolves 0.225 precision of flags; a second "is it central?" question and the
please-check lane narrow it: S19/S27) · the DVS 27/30
is not held out (the question was written with those items in view) · Romansh (German prompt; not measured).

## Finals — 5 min, jurors who did not read the case (plain words)

| Time | Beat |
|---|---|
| 0:00–0:20 | (German, then French) "About 90 Swiss parliaments, about 50 new affairs a day — and no topic field. 'What are parliaments doing about digitalisation?' means guessing keywords in every language." |
| 0:20–1:10 | The atlas: one Switzerland per topic; Digitalisierung → the map and the timeline by level: digital sovereignty in Stadtrat Bern, the Federal Assembly and Kanton Bern; a Ticino affair, its sentence highlighted; French with one key. |
| 1:10–1:50 | One table: "Two thirds of these affairs it decides on its own, and is right in 0.812 of those; the rest it hands to a person. Tested against 927 federal affairs labelled by the editors of Année Politique Suisse and never seen while we built it, registered in advance: across 24 chapters it picks the editors' one in 0.696 — keywords manage 0.186." |
| 1:50–2:30 | Neues Thema, live: a juror's topic in one sentence → last week across Switzerland; rows arrive while the pitch goes on. |
| 2:30–3:20 | Reused, not retrained: Kanton Bern's eight directorates as a file — 0.651 from German titles, 0.650 from French ones against the Grand Council's own field; Basel-Stadt's 46 themes — and with their own examples it gets better. |
| 3:20–4:20 | Ops: last night's log. "On 15 Oct the model endpoint went down. The nightly's first pass fetched OPD's export and queued the 49 new and changed affairs without a model call; when the same model build answered again, the second pass scored all 49 in 9.6 minutes, for two cents at list price. Nothing was lost, nothing was scored by another build." `docker compose` footprint from CI. |
| 4:20–5:00 | The open trail: repo, topics file, Prüfstand with raw logs and the blind annotations; QR code. |

TO UPDATE when measured: Neues Thema timing on the event endpoint (on the shared key: 98 affairs of last week in
145 s, `runs/adhoc/lehrpersonenmangel/summary.json`; no number is spoken until the event endpoint is measured).
