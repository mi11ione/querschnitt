# Demo runbook (keys and fallbacks; rehearse against the timings in docs/PITCH.md)

Setup on the laptop: `make run` (API + app at http://127.0.0.1:8000, live mode: Pult decisions and Neues Thema work);
the static copy https://querschnitt.mi11ion.io is the fallback (read-only, decisions stay in the browser). Endpoint for
Neues Thema: the event's CSCS endpoint if the hour-1 probe passed (`QS_BASE_URL` …), else Public AI. Browser at `1440 px`,
zoom 110 %, DE first. Close every other tab.

Keys: `a` Überblick · `m` Karte · `n` Neues Thema · `b` Prüfstand · `t` topic picker · `/` search · `j`/`k` next/previous
affair · `1` übernehmen · `2` verwerfen (then a digit picks the correction) · `0` überspringen · `u` undo · `l` Liste ↔ Pult ·
`[` `]` previous/next week in the Pult · `x` Karte ↔ Querschnitt-Matrix · `e` CSV · `d`/`f` Deutsch/Français · `Esc` close.

## Gate 1 (5 min)
| Beat | Keys / clicks | If it fails |
|---|---|---|
| Atlas | `a`; let it stand 3 s; point at Digitalisierung, then a dark map (Umweltschutz) | static site, same view |
| Digitalisierung → affair | click the Digitalisierung map → `/` type `souveränität` → Enter → `j` → «Der Kanton Bern strebt digitale Souveränität an» (`338697`: DE/FR readings disagree → bitte prüfen; quote from the draft law) | `t` → type `Digi` → Enter |
| Why this label | point at the two reading bars and the highlighted sentence | — |
| Decide | `1` (name preset to «Demo») → state line shows who/when | static: "stored in this browser" is fine |
| Neues Thema | open `#neu?limit=25` (or pick «höchstens 25 Geschäfte» beside the period) to cap the run at the 25 newest affairs (roughly 20–80 s; uncapped, the recorded run read 98 affairs in about five minutes); `n` → Christian's sentence → Enter; while it streams, go on talking | if slower than 30 s to first rows: open a saved topic (`t` → «Wolf») and say it was defined in one sentence yesterday |
| Prüfstand | `b`; point at the held-out row (0.696, 927 fresh affairs), then the lane split bar | — |
| Integration | the Anbindung view: the `topics` migration, the Hop loader, a `GET /changes` page, last night's log — no live terminal on stage; the commands (`psql … 0001_topics.up.sql`, `./hop-run.sh …`, `curl ':8000/changes?after=0&limit=3'`) are in `upstream/hop/README.md` for the deep dive | screenshots in docs/img |
| make eval | terminal: `make eval GOLD=their.csv` or the Basel view (`t` → «Basel-Stadt») | `make eval GOLD=data/eval/gold_aps_s9.csv` |

## Finals (5 min)
Atlas (`a`) → Digitalisierung map → timeline brush on Feb–Sep 2026 → a Ticino affair (`/` `sovranit` Enter `j`) → `f` (French) →
`d` → Prüfstand one row → Neues Thema with a juror's topic → Bern view (`t` «Bern») → an affair with DE/FR disagreement → `2`
then the right directorate → ops terminal (`cat runs/nightly/last.json`) → end on the repo URL.
