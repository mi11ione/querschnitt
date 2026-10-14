# Pitch scripts (Wed 14 Oct — re-time against the real demo; numbers from eval/claims.tsv only)

Rules: the screen shows what has actually run (scored share, last night's log); every spoken number is in the Prüfstand;
wherever a number comes from the AI judge, the sentence says so. Three numbers carry each pitch. Check with
`python3 tools/claims_check.py docs/PITCH.md`.

## Gate 1 — 5 min live demo + 3 min Q&A (Christian Gutknecht, OpenParlData)

| Time | On screen | Said (gist) |
|---|---|---|
| 0:00–1:30 | Überblick (the atlas) → Digitalisierung → Karte → «Rechenzentren im Kanton Bern» → decision graphic and quote → Pult, `[1]` | "OpenParlData has no topic field. This is every affair of 2026 from your exports — one map per topic, same scale. Each label is a choice from a closed list, read twice; this sentence supports it. `[1]` — confirmed, with who and when, next to the inferred row." |
| 1:30–2:10 | Neues Thema: Christian names a topic | Terms appear, decisions stream in for last week. "No training. It is now a file in the nightly job." |
| 2:10–3:00 | Prüfstand, human labels first | "1,357 federal affairs labelled by APS editors, tested as registered in advance: the shipped chapter is right in 0.740, plain list prompting 0.655. Two thirds pass without a check and are right in 0.864; the rest go to a person." |
| 3:00–3:40 | One prepared integration screen (no live terminal): the `topics` migration in OPD naming, the Hop pipeline that loads the bulk file, a `GET /changes?after=` page, last night's log line | "These are the merge-request files. Inferred and confirmed rows stay apart; every row names the build that made it. Model cost at list price: USD 0.333 per 1,000 affairs." |
| 3:40–5:00 | `make eval GOLD=…` live on a POLITmonitor/DVS export if one came at the deep dive; otherwise Basel-Stadt | "Basel-Stadt tags its motions by hand with 46 own themes. Loaded as a file, no training: 0.498 of 2,437; with five of their own labelled affairs as examples, 0.526. Hand us your labels — they become examples." |

Q&A cards: APS licence (chapters in the public feed; subtopics internal until APS agrees) · another scheme (`bs-themen.yaml`,
`be-directorates.yaml`: a file) · where it runs (`lite` on the current VPS; lanes need no log-probabilities) · build changes
(refit + quality gate + `GET /changes`) · recall of ad-hoc topics (judge-based 0.659 on titles; examples lift it) · who the
judge is (Claude runs + Qwen; matches APS editors on 0.790 of chapters; says yes to 27 of the 30 DVS items) · new narrow topics (one sentence casts a wide net — wolves 0.225 precision of flags; a second "is it central?" question and the
please-check lane narrow it: S19/S27) · the DVS 27/30
is not held out (the question was written with those items in view) · Romansh (German prompt; not measured).

## Finals — 5 min, jurors who did not read the case (plain words)

| Time | Beat |
|---|---|
| 0:00–0:20 | (German, then French) "About 90 Swiss parliaments, about 50 new affairs a day — and no topic field. 'What are parliaments doing about digitalisation?' means guessing keywords in every language." |
| 0:20–1:10 | The atlas: one Switzerland per topic; Digitalisierung → the map and the timeline by level: digital sovereignty in Stadtrat Bern, the Federal Assembly and Kanton Bern; a Ticino affair, its sentence highlighted; French with one key. |
| 1:10–1:50 | One table: "Against 1,357 federal affairs labelled by the editors of Année Politique Suisse, registered in advance, it picks the right chapter in 0.740. Where its two readings disagree it says so, and a person decides." |
| 1:50–2:30 | Neues Thema, live: a juror's topic in one sentence → last week across Switzerland; rows arrive while the pitch goes on. |
| 2:30–3:20 | Reused, not retrained: Kanton Bern's eight directorates as a file — 0.651 from German titles, 0.650 from French ones against the Grand Council's own field; Basel-Stadt's 46 themes — and with their own examples it gets better. |
| 3:20–4:20 | Ops: last night's log — affairs scored, wall time, USD at list price, rows pending after the endpoint was cut, minutes to drain; `docker compose` footprint from CI. |
| 4:20–5:00 | The open trail: repo, topics file, Prüfstand with raw logs and the blind annotations; QR code. |

TO UPDATE when measured: S19 (three new ad-hoc topics vs the judge), the nightly numbers, Neues Thema timing on the event
endpoint.
