# Demo runbook (keys and fallbacks; rehearse against the timings in docs/PITCH.md)

Setup on the laptop: `make demo` (API + app at http://127.0.0.1:8000 on its own store, live mode: Pult decisions and Neues
Thema work; it prints the link of each beat below and needs no network, see Offline);
the static copy https://querschnitt.mi11ion.io is the fallback (read-only, decisions stay in the browser). Endpoint for
Neues Thema: the event's CSCS endpoint if the hour-1 probe passed (`QS_BASE_URL` …), else Public AI. Browser at `1440 px`,
zoom 110 %, DE first. Close every other tab.

Keys: `a` Überblick · `m` Karte · `n` Neues Thema · `b` Prüfstand · `t` topic picker · `/` search · `j`/`k` next/previous
affair · `1` übernehmen · `2` verwerfen (then a digit picks the correction) · `0` überspringen · `u` undo · `l` Liste ↔ Pult ·
`[` `]` previous/next week in the Pult · `x` Karte ↔ Querschnitt-Matrix · `e` CSV · `d`/`f` Deutsch/Français · `Esc` close.

## Gate 1 (5 min)
| Beat | Keys / clicks | If it fails |
|---|---|---|
| Diese Woche (finals opener) | the landing view (`w`); read the sentence; point at three examples in three languages; `f` for French | static site, same view |
| Atlas | `a`; let it stand 3 s; point at Digitalisierung, then a dark map (Umweltschutz) | static site, same view |
| Digitalisierung → affair | click the Digitalisierung map → `/` type `strebt digital` → Enter → `j` → «Der Kanton Bern strebt digitale Souveränität an» (`338697`: DE/FR readings disagree → bitte prüfen; quote from the draft law) | `t` → type `Digi` → Enter |
| Why this label | point at the two reading bars and the highlighted sentence | — |
| Decide | `1` (name preset to «Demo») → state line shows who/when | static: "stored in this browser" is fine |
| Neues Thema | open `#neu?limit=25` (or pick «höchstens 25 Geschäfte» beside the period) to cap the run at the 25 newest affairs (roughly 20–80 s; uncapped, the recorded run read 98 affairs in about five minutes); `n` → Christian's sentence → Enter; while it streams, go on talking | endpoint down or silent: the run line says «Der Modell-Endpunkt antwortet nicht» (or counts the seconds without a decision) and offers `[Aufzeichnung abspielen]`: one click plays the recorded real run, labelled as a recording; say so. Or open a saved topic (`t` → «Wolf») and say it was defined in one sentence yesterday |
| Prüfstand | `b`; point at the held-out row (0.696, 927 fresh affairs), then the lane split bar | — |
| Integration | the Anbindung view: the `topics` migration, the Hop loader, a `GET /changes` page, last night's log — no live terminal on stage; the commands (`psql … 0001_topics.up.sql`, `./hop-run.sh …`, `curl ':8000/changes?after=0&limit=3'`) are in `upstream/hop/README.md` for the deep dive | screenshots in docs/img |
| make eval | terminal: `make eval GOLD=their.csv` or the Basel view (`m`, empty the search field: it stays across topics; `t` → «Basel-Stadt») | `make eval GOLD=data/eval/gold_aps_s9.csv` |

## Finals (5 min)
Atlas (`a`) → Digitalisierung map → timeline brush on Feb–Sep 2026 → a Ticino affair (`/` `sovranit` Enter `j`) → `f` (French) →
`d` → Prüfstand one row → Neues Thema with a juror's topic → Bern view (`t` «Bern») → an affair with DE/FR disagreement → `2`
then the right directorate → ops terminal (`cat runs/nightly/last.json`) → end on the repo URL.

## Offline
The demo runs with Wi-Fi off once the data is on the laptop.
- `make data` once while online. After that `make demo` uses only local files: it loads the shipped data into its own store
  `runs/demo/querschnitt.sqlite` on the first start (decisions from a rehearsal stay there and out of the `make run` store),
  checks the model endpoint, prints one link per beat and serves on `127.0.0.1`. `make demo FRESH=1` reloads the store, so
  the demo affair starts undecided again. A link pasted into the address bar opens as a fresh load.
- Fonts, scripts and styles all come from `app/`; `make preflight` checks that nothing loads from a CDN.
- Neues Thema without the model endpoint: when no connection opens (`QS_ADHOC_PROBE_S=3`), Enter answers with «Der
  Modell-Endpunkt antwortet nicht» within seconds; when the endpoint accepts but stays silent, the topic request gives up
  (`QS_ADHOC_GEN_S=20`) and the run line offers the recording once no decision has come (`SLOW_S` in `app/js/neu.js`).
  `[Aufzeichnung abspielen]` plays the recorded real run (`app/data/neu_replay.json`) through the same screen, with the line
  «Aufzeichnung eines echten Laufs vom …, keine Live-Antwort»; «zurück zur Eingabe» returns to the live field. `#neu?rec=1`
  opens the recording directly.
- Offline nothing else changes on screen except the source links in an affair (they open the parliament's site) and the
  deployed copy https://querschnitt.mi11ion.io.
- Rehearse with the endpoint blocked, against a second store:
  `QS_BASE_URL=http://10.255.255.1/v1 make demo PORT=8010 DEMO_DB=$PWD/runs/demo-rehearsal/querschnitt.sqlite`, then
  `LIVE=http://127.0.0.1:8010/ node app/dev/shoot.mjs - rehearsal` walks the Gate 1 beats in one browser session and writes
  `app/dev/shots/rehearsal-*.png`; look at each one.
