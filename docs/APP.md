# App (workstream F)

Static single-page app in `app/`: vanilla ES modules, no build step, no runtime libraries (the map is pre-projected
at build time), fonts self-hosted. It reads `app/data/*.json` (CONTRACT §3) and uses the live API when one answers.

## Run
```
.venv/bin/python -m querschnitt.export --out app/data     # real export (lead)
python3 app/dev/make_geo.py                               # app/data/geo.json (+ data-fixture/geo.json); re-run if export wipes app/data
cd app && python3 -m http.server 8765                     # http://127.0.0.1:8765/
```
- Live API: same origin, or `?api=http://127.0.0.1:8000` (the API then needs CORS for the app's origin).
- `?lang=fr` or keys `d`/`f` switch the interface; every affair stays in its own language.
- URL hash keeps state: `#karte?t=adhoc/digitalisierung&a=340652&p=BE&w=60-80&m=pult&tab=todo&q=rechenzentr`.
- Dev: `python3 app/dev/mock_api.py 8766` serves `app/` plus a stand-in API (DEV ONLY: its stream is a word match, not
  model output) to exercise Pult POSTs and the Neues Thema stream. `node app/dev/shoot.mjs` drives headless Chrome over
  CDP (no npm deps): console errors, horizontal-overflow check, screenshots into `app/dev/shots/`.
- `app/dev/make_fixture.py` builds `app/data-fixture/` (real S8 rows + OPD inputs, same format as the export, chapters
  empty). The app loads each file from `data/` first, then `data-fixture/`; the bar shows `Fixture` in red when meta comes
  from the fixture. Do not deploy `app/data-fixture/` or `app/dev/`.

## Files
`index.html` · `css/app.css` (tokens from the gleichlaut register shell) · `js/main.js` shell, keys, hash ·
`js/data.js` loading, normalisation, topics, decisions, API · `js/board.js` Karte + Pult + list + export ·
`js/map.js` · `js/timeline.js` · `js/vlist.js` (virtualised list, 52 px rows) · `js/case.js` detail ·
`js/picker.js` · `js/neu.js` Neues Thema · `js/pruef.js` Prüfstand · `fonts/` (Public Sans variable, Fragment Mono;
OFL texts beside them, fontsource 5.2.7 / 5.2.8) · `dev/geo-src/` swiss-maps 4.7.0 `2026/ch-combined.json` + licence.

Geometry: swiss-maps 4.7.0 (Interactive Things, BSD-3-Clause code; geodata BFS GEOSTAT / swisstopo, attributed in the
footer; the package README calls the geodata non-commercial). `make_geo.py` projects WGS84 → LV95 (swisstopo
approximate formulas), simplifies shared arcs (Douglas–Peucker 0.55 units), writes canton paths, lakes, outline and
2,113 commune centroids keyed by BFS number: 160 KB.

## Behaviour (decisions taken)
- Topic accessors: Digitalisierung = `dig_p/dig_flag/dig_lane`; chapter = `ch == i` (rank 1), subtopic = `subs[0] == 1000*i+j`;
  `lane`/`dig_lane` accept 0/1 or strings. Chapter `null` = not yet scored: such rows never count as zero.
- Map: grey class = hits / scored rows of the parliament in the period (quintile breaks of the non-zero shares, legend
  shows min … max). Hatched when no scored row in the period, coverage < 25 %, or `title_only_share` ≥ 50 %. Coverage =
  scored in period / `n_by_month` in period if bodies carry it, else `n_dig` (or `n_scored` for APS) / `n_affairs`.
  Red tick = undecided rows in the lane `please_check` for the topic and period. Click = filter to that parliament.
- Timeline and map follow the list filters (type, status, party, search with `a|b` = or); the timeline ignores its own
  brush, the map ignores the parliament selection.
- Pult tabs: `zu prüfen` = undecided rows that are flagged or in `please_check` (please_check first, then newest);
  `übernommen` = confirmed; `Status geändert` = confirmed rows whose OPD state differs from the state at confirmation;
  `erledigt` = every decided row. Week line = ISO week of `meta.generated_at`. Budget is a per-browser setting.
- Decisions: `[1]` POST `/affairs/{id}/topics/{code}/confirm` (code `adhoc/digitalisierung:yes` or `aps:…`, body
  `{by, scheme}`), `[2]` reject, `[0]` skip (no row), `[u]` undo (local). Static mode stores them in localStorage and says
  so in the state line. Live mode also imports `GET /changes?since=1970…` (array or `{rows}`).
- CSV (`[e]`): Datum, Ebene, Kanton, Parlament, Geschäftsnummer, Titel, Sprache, Typ, Status, Urheber/in, Partei, Link,
  Thema, p, Spur, Entscheid, Entschieden von, Entschieden am, OPD-ID, Build; last line = method line (count, topic,
  period, scored share per parliament with "ab {year}", build, "maschinelle Vorschläge, wahrscheinlich unvollständig").
- Neues Thema: `POST /adhoc {sentence, lang (guessed de/fr/it), period: "last_week", examples?, terms?}`; renders
  `topic.terms` (array or `{lang: [..]}`) as one editable mono line (Enter re-posts with `terms`); SSE accepted shapes:
  default `message` `{id, p, flag?, t}`, event `progress` `{read, total}`, event `done` (or `{done: true}`). Save keeps the
  decisions in this browser and adds the topic to the Karte picker. Static mode: field disabled + one line.
- Prüfstand reads `pruefstand.json` as `{rows: [{test, test_fr, gold: human|judge, design, design_fr, n, result,
  interval, baseline, split, file}], curve: {test, n, points: [[coverage, precision]…], op: {coverage, precision, n,
  label_de, label_fr}, file}}` (a plain array of rows also works). The fixture version transcribes VISION §6.1 and
  recomputes the S9 D3 curve from raw rows; op = the `readings_agree` lane (coverage 0.6102, precision 0.8128, n 828).
- Numbers: shares and p are truncated, never rounded up; de-CH / fr-CH grouping.

## Requests to the export (lead)
1. `pruefstand.json` in the export (format above); until then the app falls back to the fixture file and says so.
2. `bodies[].n_by_month` (`{"2026-01": n}`, all affairs) so coverage and hatching follow the brushed period; today 88 of
   89 bodies are below 50 % on the since-2025 denominator because Digitalisierung covers 2026.
3. CHE `name_de` is "Schweiz": please emit `Bundesversammlung` / `Assemblée fédérale` (app overrides for now).
4. `meta.nightly.new_rows` (or `/metrics.rows_last_night`) for "letzte Nacht" in the fact line.
5. A `type` column (own-language type name) where `type_h` is empty (many VD/GE rows), and optional `type_h_fr`.
6. 24 `party` values arrive double-encoded (`Die GrÃ¼ne`); fix at source if possible.
7. Evidence: app accepts `{field: title|title_long|text, start|char_start, end|char_end, quote}` in `detail.dig` / `detail.aps`
   and falls back to searching the quote if offsets do not match the shown text.
8. `app/data/geo.json` is written by `app/dev/make_geo.py`; the export must not delete it (or call the script).

## Polish round (14 Oct)
- Bern scheme swap: picker group «Schemata» → «Kanton Bern: Direktionen» (topic `be-directorates`, scope BE). List sorted by
  directorate (abbr in the p column), Direktion filter, summary table per directorate (click filters), detail shows abbr +
  name in the UI language, p, and the Grand Council's own field (`be.gold`). Pult lane for this scheme = `bi` (DE/FR readings
  disagree). Decisions POST code `be:<CODE>`, scheme `be-directorates`.
- Every affair with `aps.bilingual` shows `DE <chapter> · FR <chapter> → <lane>` (red only for please_check).
- Evidence: `{field, start, end, quote}` per `detail.dig|aps|be.evidence`; title highlight sits in the heading; long title is
  shown whenever it carries the evidence; a text with evidence is never collapsed.
- Fact line: «letzte Nacht» only when `meta.nightly` (or `/metrics`) has it; renders new rows, else date, plus `wall_min`.
- CSV headers, level names, topic and method line follow the UI language. Prüfstand uses `*_fr` fields when present
  (some rows still carry German baseline/split only); the first row of the first human table is set in bold.
- Coverage now uses `n_by_month`; `covered_from` years before 1800 (OPD body 616: "0209") are dropped.

## Juror round 1 (14 Oct)
- Identical affairs (same parliament, date, title) collapse into one list line with `×n`; the detail lists ids and
  submitters; `[1]`/`[2]` decide every affair of the group (state line says "gilt für n Geschäfte"); rejected mark is `[–]`.
- Period ends at `meta.until`; future-dated affairs stay in the list but not on the timeline.
- «zu prüfen» = undecided rows in the topic's please_check lane (Bern scheme: `bi`), the same number in subtitle, Pult tab,
  week line and map ticks; the fact line shows the export's global count, labelled «alle Themen (Export)».
- Prüfstand bolds row 1 of the first human table (now D4, shipped); op label from `curve.op`; no fixed coverage in the app.

## Dogfood round 1 (14 Oct)
- Pult tabs: «neu diese Woche» (every undecided hit begun in the Pult week, please_check first; `[‹] [›]` or `[`/`]`
  step the week; default = newest week up to `meta.until` with a hit; the brush does not apply) · «zu prüfen» · übernommen
  · Status geändert · erledigt. A key that would change an existing decision asks first (same key again = overwrite).
- Server decisions: `syncDecisions()` reads `GET /changes?kind=decisions&since=…` (follows `next`/`cursor`; on a server
  without `kind` it skips past the machine load time and pages by offset), on start, after each decision and every 60 s;
  the newest row per (topic, affair) wins, a closed newest row counts as undone. `u` undoes the selected row's decision,
  else the last decision of this session: `POST /affairs/{id}/topics/{code}/undo {by, scheme}`; without that endpoint the
  state line says the undo is local only.
- APS chapter queues hold only that chapter's affairs (`check` = hit ∧ lane). After `2` on a chapter or Bern row, the
  state line offers the alternatives on 1–9 (APS: ranked chapters from `detail.aps.rank`; Bern: the other directorates),
  0 = no correction; the pick POSTs `confirm` of the corrected code. Bern queue = `be_lane`.
- FR: `detail.title_alt`/`title_long_alt` shown when `alt_lang` = UI language, original beside it; parliament names
  from bodies.json (no "Name Place" doubling; English placeholders fall back to German); CSV lane/decision values and
  method line (parliament names, coverage in the period) in the UI language; decision times in local time.
- Neues Thema: period choice (letzte Woche = server default, letzter Monat = from/to, 2025–26), «liest {from} – {to}» from
  the API, the map/brush follow it; a run that ends early (error, cap, read < total) says «gestoppt bei r / n (why)» and
  offers no [speichern].
- Esc never resets the period; click on a week = that week, click again = all; «Auswahl» re-renders on every change.
- Picker «alle Geschäfte»: every affair, search across all; share = matches / all affairs of the parliament; no Pult.

## Graphics round (14 Oct)
- Detail «Thema»: yes/no gauge (p on 0–1 with the cut-off hairline, the two readings as thin bars beneath); APS
  chapter graphic: up to 5 chapters (rank ∪ `aps.reads`), main bar = p_raw (black for the shipped chapter), two thin bars
  per chapter for the readings (`aps.bilingual.reads` DE/FR preferred, else `aps.reads` «Lesart 1/2»), each reading's own
  top chapter in black, red tick where the readings point to different chapters; then the top-3 subtopics. Hover/focus = exact p.
- Überblick (nothing selected): ranked parliaments (share bar, hatched when coverage < 25 %, red tick = rows to check;
  click = filter) and up to 5 notable affairs (newest week with hits on ≥ 2 levels, then the newest p ≥ 0.99 hits).
  The weekly per-level chart was cut: the please-check share now sits as a red base segment in the main timeline.
- Querschnitt matrix (`[x]` or the «Querschnitt» toggle above the map; `#karte?v=matrix`): APS chapters × Bund, cantons
  de | fr | it, communes aggregated, FL; cell = share of the parliament's scored affairs in the chapter (period + filters),
  quintile grey ramp, hatched where coverage < 25 %; click a cell = that chapter and parliament on the map; phones get
  Bund / de / fr / it / Gemeinden / FL.
- List rows: 40 px hairline confidence bar under p; red tick for please-check (no `[!]`).
- «Ähnliche Geschäfte»: a strip per level on the main timeline's weeks above the titles.
- Prüfstand: lanes as one split bar (width = share, dark = precision) and the 25×25 confusion heatmap of the shipped
  design (row share, diagonal outlined), from `app/dev/make_confusion.py` → `app/data/pruef_confusion.json` (top-1
  0.7406, lanes 720/871 and 285/486, identical to eval/s16/results.json).
- `app/dev/serve.py`: dev static server with a larger accept queue (the stock http.server drops connections under the
  headless suite).

## Atlas round (14 Oct)
- New first view «Überblick» (`#ueber`, default route, key `a`): one line of large numbers (affairs scored, parliaments,
  weeks, rows waiting in red), 26 small Switzerlands (Digitalisierung, the 24 APS chapters by volume, «Kein Sachthema»)
  on one fixed doubling ramp (`< 2.5 / 2.5 / 5 / 10 / ≥ 20 %` of the canton's scored affairs), Federal Assembly as a band,
  cantons without scored affairs hatched; click = Karte on that topic with the Überblick panel. «Diese Woche»: newest
  week with ≥ 20 affairs, per-level bars and up to 5 notable affairs (one chapter on ≥ 2 levels, then highest p).
  Canton paths are defined once and reused (`<use>`), so 26 maps cost one geometry. The fact line is hidden there.
- Detail order: title (date · parliament · type) → decision graphic (the topic in view first) → quoted passage →
  subtopics → identical affairs → metadata + provenance → similar affairs → decision bar.
- Similar affairs: shown only for same first subtopic with ≥ 2 shared content words, or an idf overlap ≥ 15 with ≥ 3
  shared content words (procedural words removed; cut set by eye on 20 cases, `simcal` scenario prints them).
- Fact line kept to one line (items dropped from the end), build only in the footer; list titles on up to two lines
  (rows 70 px); map column wider; the federal band says «Bund» instead of repeating the parliament name.

## Juror round 2 (14 Oct)
- One p per row: list, Pult, CSV and the detail show the calibrated p (`ch_p` / `aps.p[0]`, `dig_p`); the decision
  graphic shows a number only on the shipped chapter, raw values (`p_raw`, readings) only on hover.
- Fact line: «letzte Nacht: N neu · M min» from `meta.nightly.new_rows` / `wall_min` (minutes truncated); dropped when 0.
- Pult opens on the newest week with undecided hits of the topic; a week without any says «keine offenen» in the week
  line and in the list; every empty list says why.
- Prüfstand strings are printed as delivered (result strings verbatim, interval numbers joined, no formatting).

## Own schemes and saved topics (14 Oct)
- Picker groups «Gespeicherte Themen» (scheme_aps.json `topics[]` other than Digitalisierung, column `adhoc` =
  {slug: [p, flag, lane]}, plus topics saved in this browser) and «Eigene Schemata der Parlamente» (Bern directorates;
  every `schemes[]` entry with `kind: "named"`, column `own` = [schemeId, code, lane]).
- Named schemes reuse the Bern view: scoped to the body, list grouped and filtered by theme, Pult lane = `own` lane,
  overview = themes as a ranked bar list (click filters) with «stimmt mit dem Kanton überein: k / n (Thema 1) · k / n
  (Thema 1 oder 2)» from `own_gold`; detail = model theme, lane, the canton's Thema 1/2 with a mono mark ([=], [= 2],
  [≠]; red only for [≠] in the please-check lane) and the CC BY credit. Period = the scheme's own range (2019–24).
- Ticino (S29, 15 Oct) is the second named scheme, with no code of its own in the app: `export.OWN` says per scheme
  where its own labels live (Basel-Stadt: `../data/manual/bs_100086.csv` by number; Ticino: `eval/s29/items.jsonl` by
  OPD id, OPD's lead department) and how the app names it (`names`, `unit`, `group`, `source`, option codes as `abbr`),
  copied into scheme_aps.json `schemes[]`. Without `names` the picker says «<place>: <n> Themen»; with only one own
  label per affair the overview drops «(Thema 1 oder 2)». Ticino: «Tessin: Departemente» / «Tessin : départements»,
  options in Italian as the canton writes them, period 2023-01 – 2026-10 (`--extra TI:2023-01-01:2024-12-31` and
  `runs/s29` are export defaults), detail «Kanton: …» under «Federführung laut OpenParlData (Gran Consiglio Ticino)».
  The scheme in view leads the detail's facts.
- The main slice starts at `meta.since`; affairs before it count only in the scheme views that cover them (atlas,
  matrix, topic counts and every other topic stay on 2025–26).
- Saved topics: the scored period is the weeks where ≥ 50 % of all affairs carry a decision (a `period: [from, to]` in
  the topic entry would override it); the Karte opens brushed to it, the timeline hatches the weeks outside, the subtitle
  says «bewertet dd.mm.–dd.mm.yyyy»; their small maps follow Digitalisierung in the atlas, marked «gespeichert».

## Juror round 3 (14 Oct)
- Lane = `pass` / `please_check` (calibrated p < 0.7, or DE/FR disagree in bilingual parliaments). The decision graphic
  explains the readings («Lesarten einig / uneinig», «DE und FR einig / uneinig») without red, and adds the lane line
  only when a person is needed: «bitte prüfen: p 0.283 < 0.7». No label equates lane and reading agreement; CSV lane =
  «bitte prüfen» / «ohne Prüfung».
- Prüfstand: shipped point = p ≥ 0.7 (0.6684, 0.8644 from eval/lanes/results.json, via make_confusion.py
  `lanes_tau`, used when `curve.op` is still the readings point); the readings-agree point stays as a grey dot; the
  lanes bar shows p ≥ 0.7 (66.8%, 0.864) vs p < 0.7 (0.491).
- Saved topics without a Prüfstand row (`measured` in the topic entry, or a pruefstand row with `topic` = id) are
  marked «nicht gemessen» in the picker and on their atlas maps.
- Überblick: «… % gehen an eine Person» = please-check rows / scored APS rows in 2025–26 (count on hover); weeks
  count the main slice only.
- No «Beleg» block without a quote: the text shows under «Text», and is omitted when there is none.

## Anbindung (14 Oct)
- 5th tab «Anbindung» / «Intégration» (key `i`, `#anb`): the `topics` columns of 0001_topics.up.sql (machine columns
  grey, decision columns black), the Hop main path of load_topics.hpl with its skip branches and the run line of
  upstream/hop/README.md, `GET /changes?after=` live (first 3 rows, total, next) or the stored sample marked «Beispiel»,
  last night's line from meta.nightly, and the compose footprint from eval/ci_footprint.txt with the CI run link.
- Data: `python3 app/dev/make_integration.py` → app/data/integration.json (no runtime fetch of repo files).

## Zählweisen (15 Oct, juror round 5)
One period and one set of counts for every screen (`D.tally` in data.js): affairs dated `meta.since` … export date
(`meta.until`). meta.json's own `affairs` / `scored` / `dig_scored` also hold the 3 future-dated affairs; the app does
not use them for counts. Labels name what they count:
- «Geschäfte» (fact line, Karte tab) = every affair in the period.
- «bewertet (APS-Kapitel)» (fact line) = «Geschäfte bewertet (APS-Kapitel)» (Überblick) = affairs with an APS chapter
  decision. «bewertet (Digitalisierung)» = affairs with a Digitalisierung decision.
- Karte header «N Treffer von M für dieses Thema bewertet» = M = rows scored for the topic in view, in the named period
  (no filter, no brush: the same M as the fact line for Digitalisierung and for any APS chapter).
- «warten auf eine Person (APS-Kapitel)» = APS rows in the please-check lane; the Überblick's «… % ohne Prüfung · aller
  bewerteten Geschäfte, alle Ebenen» and «… % an eine Person» are shares of the same APS-scored affairs.
- Prüfstand pass-lane share = share in the pass lane of the 927 held-out federal affairs (S25), labelled as such; it is a test
  population, not production.
- Periods: every label (Karte header, Überblick panel, timeline, CSV) comes from `Board.perText()`: the brush clamped to
  the domain, never past the export date. A Neues Thema run (live or replayed) shows the period it read until a person
  brushes other weeks. The replay starts by itself once per page load in static mode.
- Detail: one plain sentence above each decision graphic («Zweimal gefragt (mit und ohne Beispiele): beide Male «X» →
  ohne Prüfung.»; DE/FR parliaments «Auf Deutsch und auf Französisch gefragt …»); the bars stay for experts.
- Neues Thema live cap: `#neu?limit=25` or the select beside the period sends `limit` with `POST /adhoc` (newest
  affairs first); default no cap; hidden in static mode.

## Diese Woche (15 Oct)
- New first view and default route «Diese Woche» / «Cette semaine» (`#woche`, `#woche?d=<Monday ISO>` for an older
  week, key `w`; `js/woche.js`). Überblick stays at `#ueber` (key `a`). Default week = the newest complete Monday–Sunday
  week whose Sunday is ≤ `meta.until`; `‹ ›`, `[`/`]` or ←/→ step back to `meta.since`.
- One computed sentence («Woche 41: 111 Geschäfte aus 27 Parlamenten. Am meisten: …» = the 3 largest topics), the week
  by level (hairline bars) and by language, then the 6 topics with the most affairs that week (24 APS chapters without
  «Kein Sachthema», Digitalisierung, saved ad-hoc topics; hit = rank-1 chapter / flag, as in the Karte): count, bars per
  level on one scale across rows, and up to 3 examples (phones: 2).
- Examples: only rows whose detail carries the topic's own evidence (chapter → `aps.evidence`, Digitalisierung →
  `dig.evidence`, saved topic → `adhoc[slug].evidence` once exported). Picked for a new parliament each, then a new
  language and level; clean quoted sentences first (form fields, letterheads and mid-sentence fragments rank below a
  title that is itself the evidence, which is then marked and labelled «Beleg: der Titel»). The quote is the most
  prose-like sentence of the evidence span, cut at a word boundary (≤ 160 chars, «…»). Title in the UI language where
  the parliament publishes it (`title_alt`), else the original with a language tag. Red tick = the topic's please-check
  lane. Click an affair → `#karte?t=<topic>&a=<id>&w=<week>-<week>`; click a topic → its Karte brushed to that week.
- Detail buckets (`1000` ids each, a few MB): only the buckets holding ≥ 10 % of the week's candidates (at least the largest)
  are fetched, more only while a topic lacks two examples (≤ 3 rounds of ≤ 2 buckets).
- Shots: `woche-1440`, `woche-fr-1440`, `woche-375`, `woche-prev-1440`, `woche-open-1440` in `dev/shoot.mjs`.
