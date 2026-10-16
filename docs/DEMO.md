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
| Atlas | `a`; let it stand 3 s; point at Digitalisierung, then a dark map (Umweltschutz) | static site, same view |
| Digitalisierung → affair | click the Digitalisierung map → `/` type `strebt digital` → Enter → `j` → «Der Kanton Bern strebt digitale Souveränität an» (`338697`: DE/FR readings disagree → bitte prüfen; quote from the draft law) | `t` → type `Digi` → Enter |
| Why this label | point at the two reading bars and the highlighted sentence | — |
| Decide | `1` (set the name «Demo» in «Name für die Entscheidung» before the slot — it stays in the browser; without a name `1` only focuses the field) → state line shows who/when | static: "stored in this browser" is fine |
| Neues Thema | open `#neu?limit=25` (or pick «höchstens 25 Geschäfte» beside the period) to cap the run at the 25 newest affairs (roughly 20–80 s; uncapped, the recorded run read 98 affairs in about five minutes); `n` → Christian's sentence → Enter; while it streams, go on talking | endpoint down or silent: the run line says «Der Modell-Endpunkt antwortet nicht» (or counts the seconds without a decision) and offers `[Aufzeichnung abspielen]`: one click plays the recorded real run, labelled as a recording; say so. Or open a saved topic (`t` → «Wolf») and say it was defined in one sentence yesterday |
| Prüfstand | `b`; point at the held-out row (0.696, 927 fresh affairs), then the lane split bar | — |
| Integration | the Anbindung view: the `topics` migration, the Hop loader, a `GET /changes` page, last night's log — no live terminal on stage; the commands (`psql … 0001_topics.up.sql`, `./hop-run.sh …`, `curl ':8000/changes?after=0&limit=3'`) are in `upstream/hop/README.md` for the deep dive | screenshots in docs/img |
| make eval | terminal: `make eval GOLD=their.csv` or the Basel view (`m`, empty the search field: it stays across topics; `t` → «Basel-Stadt») | `make eval GOLD=data/eval/gold_aps_s9.csv` |

## Finals (5 min)
`w` «Neueste Woche» (loaded before the slot) → read the line under the header and the headline → point at examples in
German and French (Italian where the week has one) → open one: the why-sentence → `t` «Digi» → the map → `b` Prüfstand,
the lead block (69.6%, 81.2%, 18.6%) → the second tab with `#neu?limit=25` (live run, or the recording on the static
site) → `i` Anbindung: «letzte Nacht», the cost line, then the repository block with the QR code → end.

## Stage setup (both slots)
- Load the site before the slot: a cold first load takes 2–3 s, about 8 s on slow Wi-Fi; afterwards every key answers in
  under a second.
- Never paste a `#…` link on stage: it reloads the whole app. Open `#neu?limit=25` in a second tab beforehand.
- Set the decision name once («Demo») in the browser you present from.
- Check the demo affair (`#karte?a=338697`) on the morning of the slot: it must show its chapter, the DE/FR readings and
  the quote; if not, use the fallback affair in the Gate 1 table.

## Backup video
If the venue Wi-Fi fails, play `dist/querschnitt-demo.mp4` (silent, about 1:42; the finals voice runs over it). `make film`
records it from the live site in one command (`~8 min`, needs node, Chrome and ffmpeg): `app/dev/film.mjs` plays the
storyboard below in headless Chrome, one virtual-time step per frame, so a slow network or machine cannot cause stutter or
half-loaded frames (a step that waits for a fetch is not filmed), then encodes `1920×1080`, `30 fps`, H.264 and checks the
file with ffprobe (constant rate, every filmed frame encoded, at most two minutes); beat and caption times go to
`dist/querschnitt-demo.beats.json`. Re-record after the evening export refresh, then watch it once end to end. Preview
without encoding: `node app/dev/film.mjs --frames /tmp/film --every 30`.
The Woche beat adapts to the week: it scrolls to the two ranked rows with the most languages, names the languages in view,
points at a red tick if one is in view (else rests on the rows) and opens a German pass-lane example with a whole quote
(the script prints which). Times below are from the test take of 16 Oct; a red tick in view adds a few seconds to the Woche.

| Time | Screen | Caption (lower third) |
|---|---|---|
| 0:00 | «Neueste Woche»: the sentence, the week by level and language | Last week in Swiss parliaments, by topic |
| 0:05 | scroll through two topic rows, their quoted examples; the cursor on a red tick if one is in view | Quoted sentences in German and French (the languages in view) · Red tick: unsure, so a person checks |
| 0:18 | click an example → Karte: the plain why-sentence, then the case scrolls to the quoted sentence | Why this topic, in one plain sentence · The sentence in the affair that supports it |
| 0:31 | Überblick | One map per topic, same scale |
| 0:37 | click Digitalisierung → its map | Digitalisierung across every parliament · AI judge: flags 0.905 right, keywords 0.756 |
| 0:48 | Prüfstand, the lead block: held-out row, then the lane row | 927 unseen federal affairs: 0.696 match the editors · Two thirds pass unchecked, right in 0.812 |
| 1:02 | Neues Thema: the recorded real run plays, its label in view, decisions stream in | A new topic from one sentence: recorded run |
| 1:24 | Anbindung: the topics table and Hop loader, then last night's run | The topics table and loader for OpenParlData · On Apertus: USD 0.333 per 1,000 affairs |
| 1:34 | the page scrolls on to /changes and the footprint, fade to white | github.com/mi11ione/querschnitt |

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
