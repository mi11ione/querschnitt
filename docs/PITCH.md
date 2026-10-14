# Pitch scripts (draft, Wed 14 Oct — re-time against the real demo; numbers from eval/claims.tsv only)

Rules: the screen shows what has actually run (scored share, last night's log); every spoken number is in the Prüfstand;
wherever a number comes from the AI judge, the sentence says so. Check this file with `python3 tools/claims_check.py docs/PITCH.md`.

## Gate 1 — 5 min live demo + 3 min Q&A (Christian Gutknecht, OpenParlData)

| Time | On screen | Said (gist) |
|---|---|---|
| 0:00–1:30 | Karte, "Digitalisierung", 2026 → list → «Rechenzentren im Kanton Bern» → timeline for data centres → Pult, `[1]` on one affair | "Your deck's real use case is DVS, which curates its list by hand. Of the 30 affairs on DVS's public page, Querschnitt recognises 27; keyword search 21. In our AI-judge-checked sample there are seven data-centre affairs — Vaud, Geneva, Schaffhausen, Vaud again, Bern, then twice the Federal Assembly; Querschnitt flags all seven, the keyword list two. `[1]` — confirmed, with who and when, next to the inferred row." |
| 1:30–2:10 | Neues Thema: Christian names a topic | Terms appear, decisions stream in for last week. "No training. It is now a file in the nightly job." |
| 2:10–2:50 | Prüfstand, human labels first | "1,357 held-out federal affairs labelled by APS editors, pre-registered: the shipped chapter is right in 0.748 — plain list prompting 0.655, keywords 0.192. No measurable language or party difference in chapter accuracy. The AI-judge rows for 2026 are marked as judge agreement. On the Federal Parliament's own Curia tags the trained BFH model is ahead (0.687 vs 0.654, not significant)." |
| 2:50–4:00 | Integration, a full minute: `upstream/opd/` migration in Postgres, the Hop pipeline loading the bulk file (`hop-run`), `lite` profile, `GET /changes`, last night's `/metrics` line | "These are the merge-request files. Inferred and confirmed rows stay apart; every row names the build that made it." |
| 4:00–5:00 | `make eval GOLD=…` live on a POLITmonitor/DVS export if one came at the deep dive, otherwise on `data/eval/gold_aps_s9.csv` | "Hand us your labels: precision, recall, the misses listed per level — and the labels become examples." |

Q&A cards: APS licence (public feed with chapters; subtopics internal until APS agrees) · POLITmonitor scheme as a file
(`be-directorates.yaml` shape) · where it runs (`lite` / `full`; lanes need no log-probabilities) · build changes (refit +
quality gate + `GET /changes`) · recall (titles: judge-based 0.654; editor examples lift it; text makes it stricter) · who
the judge is (Claude runs + Qwen; DVS items 27/30; APS chapters 0.790) · private subscriptions · Romansh (German prompt; not
measured).

## Finals — 5 min, jurors who did not read the case (plain words)

| Time | Beat |
|---|---|
| 0:00–0:20 | (German, then French) "OpenParlData collects about 90 parliaments, four languages, about 50 new affairs a day — and no topic field. 'What are parliaments doing about digitalisation?' means guessing keywords in every language." |
| 0:20–1:15 | Karte: "Digitalisierung" → Switzerland fills canton by canton, communes as points; the timeline by level: digital sovereignty in Stadtrat Bern, the Federal Assembly and Kanton Bern; a Ticino affair, its sentence highlighted; the interface switches to French with one key. |
| 1:15–1:55 | One table (shipped 0.748 · plain prompting 0.655 · keywords 0.192 · subtopic 0.521): "Against 1,357 federal affairs labelled by the editors of Année Politique Suisse, tested as registered in advance, it picks the right chapter in nearly three of four. Where its two readings disagree, it says so and a person decides." |
| 1:55–2:30 | Data centres on the timeline — seven affairs, Vaud to the Federal Assembly; Querschnitt flags all seven, the keyword list two. "Across this year, an AI judge checked by an open model estimates about 900 affairs on digitalisation; the judge agrees with nine in ten of our flags, and with three in four keyword hits." |
| 2:30–3:10 | Neues Thema, live: a juror's topic in one sentence → last week across Switzerland; rows arrive while the pitch goes on. |
| 3:10–3:50 | Bern, reused: Kanton Bern's own scheme — its eight directorates — loaded from a file; Grand Council affairs routed in German and in French; an affair where German and French disagree: a clerk decides, the confirmed row shows name and date. |
| 3:50–4:30 | One ops screen from the last logged night: affairs scored, wall time, list-price USD, rows pending after the endpoint was cut, minutes to drain. |
| 4:30–5:00 | The open trail with links and a QR code: repo, topics file, Prüfstand with raw logs and the blind annotations. |

TO UPDATE when measured: S17 (communal slice on the production run), S18 (Bern directorates vs the Grand Council's own
field on 2025–26), S8 on the full 2026 census (exact flag counts), nightly numbers, Neues Thema timing on the event endpoint.
