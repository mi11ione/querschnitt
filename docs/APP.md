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
  name in the UI language, p, and the Grand Council's own field (`be.gold`). Since 16 Oct: where that field names a
  directorate (`be.field`), the field is the value («aus dem Feld des Grossen Rates»), Apertus's reading stands under it
  («Apertus las: … · gleich / anders»), the row never goes to please-check, and no inferred topic row is published over it. Pult lane for this scheme = `bi` (DE/FR readings
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
  cantons without scored affairs hatched; click = Karte on that topic with the Überblick panel. «Diese Woche»: the newest
  week with complete data (same rule as the «Diese Woche» view, see «Juror round 6»), per-level bars and up to 5 notable
  affairs (one chapter on ≥ 2 levels, then highest p).
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
  only when a person is needed (since round 6 in words: «aber unsicher», p on hover). No label equates lane and reading agreement; CSV lane =
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
- Neues Thema live cap: `#neu?limit=25` or the select beside the period sends `limit` with `POST /adhoc`; a capped
  run reads candidates first (term and subtopic hits, then the newest rest; SERVICE.md «Neues Thema») and the run line
  then adds «Kandidaten zuerst (Begriffe, Unterthemen)»; default no cap; hidden in static mode.

## Diese Woche (15 Oct)
- New first view and default route «Diese Woche» / «Cette semaine» (`#woche`, `#woche?d=<Monday ISO>` for an older
  week, key `w`; `js/woche.js`). Überblick stays at `#ueber` (key `a`). Default week = the newest week with complete
  data (rule in «Juror round 6»); `‹ ›`, `[`/`]` or ←/→ step from `meta.since` up to the newest calendar-complete week
  (Sunday ≤ `meta.until`).
- One computed sentence (`«Woche 40: 758 Geschäfte aus 36 Parlamenten. Am meisten: …»` = the 3 largest topics), the week
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
- Detail buckets (`1000` ids each, ≈ 2–2.5 MB for the newest ids): only the buckets holding ≥ 10 % of the week's candidates (at least the largest)
  are fetched, more only while a topic lacks two examples (≤ 3 rounds of ≤ 2 buckets).
- Shots: `woche-1440`, `woche-fr-1440`, `woche-375`, `woche-prev-1440`, `woche-open-1440` in `dev/shoot.mjs`.

## Juror round 6 (15 Oct)
- **Newest week with complete data.** OPD's export lags: KW 41 held `111` affairs against `809 / 622 / 758` in KW 38–40 (15 Oct export).
  A week counts as complete in the data when it holds ≥ 50 % of the median of the 8 weeks before it (`data.js`
  `weekFull`, `FULL_SHARE = 0.5`; fewer prior weeks at the start of the period, none = complete). «Diese Woche» opens on
  the newest such week, searched back at most 4 weeks from the newest calendar-complete week (else that week), labelled
  «neueste Woche mit vollständigen Daten» / «dernière semaine aux données complètes»; with the export of 15 Oct that is
  KW 40 (`758 ≥ 0.5 × 450`). `›` still reaches the later calendar-complete weeks, which carry a quiet grey line «Daten
  dieser Woche noch unvollständig (Export-Verzug)» (counts and median on hover). Holiday weeks further back are not
  judged. The Überblick's «Diese Woche» box uses the same week (it used «≥ 20 affairs»). `#woche` without `d=` = the
  default week. Shots `woche-lag-1440`, `woche-lag-fr-375`.
- **Examples from the pass lane.** Per topic, the example picker runs its diversity tiers over pass-lane rows first; a
  please-check row (red tick) only fills a slot no pass-lane row can. (KW 40 Umweltschutz no longer opens with a
  misfiled Ticino school e-mail affair.)
- **Sicherheit in Worten** (`util.js` `confWord`, `CONF_LO = 0.7`, `CONF_HI = 0.9`). The detail shows the probability
  of the answer as a word: < 0.7 «unsicher» / «incertain» (exactly the please-check cut-off: that row goes to a person),
  0.7–0.9 «ziemlich sicher» / «plutôt sûr», ≥ 0.9 «sicher» / «sûr». For yes/no topics the answer's probability is p
  for «ja» and 1 − p for «nein» (so «unsicher» ⇔ 0.3 ≤ p < 0.7, the yes/no lane). Used on the shipped chapter, the
  first subtopic, Digitalisierung, saved and live topics and Bern's directorates; the sentence says «aber unsicher» /
  «trotzdem ziemlich sicher». Every raw p (calibrated, raw, per reading) stays in the tooltip. A bilingual
  DE/FR-disagree row can read «ziemlich sicher» and still go to a person: the sentence above says why.
- Readings: the visible graphic no longer labels «Reihenfolge 1/2» (or «mit/ohne Beispiele», DE/FR); the sentence above
  says how Apertus was asked, the tooltip names each reading with its p. The column head reads «Sicherheit».
- **Unrelated ad-hoc «nein»**: Digitalisierung shows its full graphic only when it is the topic in view or its answer is
  «ja». Otherwise (an APS chapter, a parliament's scheme or a new topic in view) it is one line at the end of the facts
  («Digitalisierung nein · sicher [+]»), the graphic behind `[+]`. An affair link without a topic (`#karte?a=96375`)
  opens on the affair's own topic (Digitalisierung when flagged, else its APS chapter), as from the Überblick. Shot
  `why-collapse-1440`.
- Map legend: hatching reads «wenig Daten» / «peu de données»; the definition (under 25 % scored or ≥ 50 % title only)
  is on hover.
- Überblick: «≈ M pro Parlament und Woche» / «≈ M par parlement et par semaine» after «≈ N pro Woche» = please-check
  rows ÷ weeks ÷ parliaments with affairs in the period (15 Oct export: `15,812 / 94 / 89 ≈ 1.8`, truncated to one
  decimal; the three counts on hover).
- Footer, detail provenance and the Neues Thema recording say «Route swiss-ai/apertus-v1.5-8b»: it is Public AI's route
  name and does not fix the model size (APERTUS-NOTES).
- Anbindung: the `/changes` rows with `adhoc%2Fdigitalisierung%3Ayes` came from `dev/mock_api.py`, which stored the
  app's percent-encoded path segment as the code (the real API decodes it). The mock now decodes paths, answers
  `POST /adhoc/{slug}/stop` and has a larger accept queue; `make_integration.py` re-run (Hop path now 14 steps, sample
  total `246,341` rows).
- Loading: the landing view fetches `affairs.json` (`11.2 MB` raw; gzip `1.9 MB`, brotli `1.3 MB`), one detail bucket for
  KW 40 (`detail/340.json`, `2.3 MB` raw, gzip `0.58 MB`) and `≈ 0.4 MB` of small files (bodies, scheme, geo, Prüfstand,
  fonts, modules) = `14.1 MB` raw (`firstload` shot prints it). Detail buckets were already lazy; `topics.jsonl.gz`
  (6 MB) is a download for loaders, never fetched by the app. The boot files now load in one parallel round (the two
  Prüfstand files used to follow). Served compressed, first open is ≈ 2.5 MB; the deployed worker currently sends
  `/data/` uncompressed (see the site's worker).

## Juror round 7 (15 Oct)
- **What the page is, first.** The landing view (`#woche`, view id unchanged) opens with one line under the bar:
  «Apertus ordnet die Geschäfte einem von 24 Themen der Année Politique Suisse zu, wo vorhanden mit dem Satz, der es
  belegt; ▌ rot: eine Person prüft.» (FR equivalent). It replaces the key beside the language line; the bottom note now
  only says how examples are chosen (title-only evidence reads «Beleg: der Titel») and what a click does.
- **Tab name.** «Neueste Woche» / «Dernière semaine» (the view shows the newest week with complete data, not the
  calendar week); the Überblick box uses the same name.
- **Ranking = APS chapters only.** The 6 ranked rows, the headline's «Am meisten» and «Weitere Kapitel» are APS
  chapters. Digitalisierung follows in its own section «Querschnittsthemen» / «Thèmes transversaux» (a row with
  examples, not numbered); saved ad-hoc topics are one line of names and counts under it. One bar scale for both.
- **Liechtenstein.** `meta.parliaments` (89) includes the Landtag FL. `data.js parlCount()` → [Swiss, FL present];
  labels read «88 Schweizer Parlamente + Landtag FL» (fact line, Überblick), «Geschäfte aus 88 Schweizer Parlamenten
  und dem Landtag FL» (lede), «… aus 35 Parlamenten und dem Landtag FL» (week headline). The per-parliament load on the
  Überblick still divides by all parliaments with affairs (FL included; the tooltip says «Parlamente», not «Schweizer»).
- **Bar.** No counts beside tab names. The static-mode word «statisch» is now «Stand 15.10.2026» / «état au …» (the
  export date); what static means (decisions stay in this browser, Neues Thema needs the live service) is the `title`.
- **Read-back in the «why» sentence.** The shipped chapter is the chapter of the best subtopic (compose.py
  `chapter_decision`, subtopic p × chapter mean p), so it can differ from both readings' first choices. When it does
  and `aps.subs[0]` belongs to the shipped chapter (`scheme_aps.json subtopics[].ch`), the sentence says so: «verschiedene
  Antworten («Öffentliche Finanzen» / «Gesundheit, Sozialhilfe, Sport»), Vorschlag aus dem passendsten Unterthema:
  «Allgemeiner Umweltschutz» (Kapitel «Umweltschutz»), aber unsicher → eine Person prüft.» (`#karte?a=96375`, shot
  `why-1440`). Subtopic names exist in German only, so the FR sentence quotes the German subtopic name.

## Stage fixes (16 Oct, querschnitt-review/timing.md 7, 8, 10, 13)
- **Anbindung, first screen.** «letzte Nacht» (incl. the 15 Oct endpoint-cut sentence) now heads the right column, with
  one line under it: «USD 0.333 pro 1'000 Geschäfte (Kapitel, Unterthema, ein Ad-hoc-Thema; Listenpreis Public AI) ·
  eval/cost/results.json» (FR equivalent). The number is `integration.json cost.usd_per_1000_affairs`, which
  `make_integration.py` copies from `eval/cost/results.json usd_per_1000_affairs_all_steps`; shown truncated to 0.001.
  Hop, `/changes` and the footprint follow.
- **Repository.** Bottom of the left column: repo and site URLs (`integration.json repo`) and a QR code for the repo URL,
  `app/img/qr-repo.svg` (37 × 37 modules incl. the 4-module quiet zone, black on white, shown at 148 px = 4 px a
  module). It is written by `make_integration.py` with `app/dev/qr.py`, a pure-Python encoder (byte mode, level M,
  version 3 here). `python3 app/dev/qr.py --test` checks it against the QR standard's (`ISO 18004`) vectors (generator polynomial, format
  bits, Annex I ECC codewords); the SVG and the rendered page both decode to the URL with OpenCV's QR detector.
- **Neues Thema, static.** The run line shows «…» (and no input affordances) until `neu_replay.json` has loaded; «Braucht
  den Live-Dienst» appears only when there is no recording. `#neu?limit=25` now applies to the recording too: its first
  25 decisions in recorded order (`clipRec`), progress out of 25, done at the 25th decision's time (≈ 20 s at ×4); the
  run line reads `«gelesen 25 / 25 · markiert 4 · 76 s · Aufzeichnung, gekürzt auf 25 · ×4»`. Shot
  `neu-replay-limit-1440`.

## Juror round 8 (16 Oct, querschnitt-review/r8 J3, J4)
- **«letzte Nacht», honest.** The endpoint-outage sentence appears only when the night record carries `cut_reason` (a
  real outage). An even-day cut without it is the scheduled test cut (ops/nightly.sh): «geplanter Unterbruch: der erste
  Durchgang läuft jeden zweiten Tag ohne Modell, als Test.» / «interruption planifiée : …». A hand-written `note`
  (`{de, fr, en}` or a string) in `runs/nightly/last.json` replaces the queue/drain/USD figures it corrects; the export
  copies the record whole (`meta.nightly`, incl. `note`). The 16 Oct record carries one: the model pass was stopped by
  hand after 105 affairs, because the `9,645` queued were letterhead-trimmed inputs a parallel re-score was already
  scoring; the queue then fell to `1,179` because that re-score filled the store (log `runs/nightly/2026-10-16.log`).
  `cli.write_last` starts a fresh record on the next date, so the note does not carry over.
- **The outage stays visible.** The export writes `meta.nightly_outage` from the newest `eval/nightly/<date>.json` with
  `cut_reason` (date, queue before/after, drain minutes, USD, reason, file). The panel shows it on its own line under
  «letzte Nacht»: «Ausfall 15.10.2026: Warteschlange 49 → 0 · abgebaut in 9.6 min · USD 0.0215» (FR «Panne du …»),
  then the outage sentence with the reason on hover. Minutes and USD truncated (0.1 / 0.0001), never rounded up.
- **Überblick: saved topics apart.** The saved narrow topics (Hitzeschutz, Wolf, KI an Schulen) leave the APS grid and
  follow it in a quieter row «Gespeicherte Themen (gemessen gegen KI-Richter)» (heading generic when a row's gold is not
  the judge). Under each map: «eng · Präzision 0.225 (KI-Richter)» — the leading figure of the topic's Prüfstand row
  (`pruefstand.json rows[].topic`, `result` / `result_fr` as written); no row → «eng · nicht gemessen», never a number.
- **Procedural quotes (Neueste Woche).** `woche.js PROC` lists phrases that name the instrument, not the subject:
  DE «Der Bundesrat/Regierungsrat/Gemeinderat … wird beauftragt/gebeten/ersucht (, zu prüfen und Bericht zu erstatten)
  (, folgende Fragen zu beantworten)», «bitte ich den … um die Beantwortung der folgenden Fragen», «… haben
  Ratsmitglieder, Kommissionen und Fraktionen das Recht, Interpellationen einzureichen», «gestützt auf Art./§ …»,
  «Der Grosse Rat … wolle beschliessen», «Antwort des Regierungsrates», form labels (Eingereicht von:, Erst-/
  Mitunterzeichnende:, Einreichedatum:, Geschäftstyp:, Urheber/in:, Zuständig:, Signatur:, Dringlichkeit:);
  FR «Le Conseil fédéral/d'État/communal … est chargé/prié/invité de (répondre aux questions suivantes)», «en vertu/
  conformément à l'art. …», «Le Grand Conseil décrète/arrête», «Réponse du Conseil d'État», form labels (Signataire:,
  Cosignataires:, Date de dépôt:, Réception au SGC:, Département(s):, Numéro:, Heure:); IT «Il Consiglio federale/di
  Stato/comunale, Il Municipio è incaricato/invitato di (rispondere alle seguenti domande)», «ai sensi dell'art. …»,
  «chiediamo al Municipio di rispondere alle seguenti domande / quanto segue», «Lodevole Municipio». A quote is
  procedural when it contains one of these and, with them removed, fewer than 4 content words (≥ 4 letters, not in the
  small DE/FR/IT stop list) remain or none shares a 7-letter stem with the topic. The topic's stems come from its
  names and aliases, a chapter's APS subtopics (`scheme_aps.json subtopics[].ch`, German names) and a saved topic's
  bracketed question text. A procedural quote is never shown: the row counts as title evidence («Beleg: der Titel» /
  «Extrait : le titre») and, like other title evidence, only fills a slot no clean quote can. Among clean quotes, one
  that shares a stem with the topic ranks first (+0.75). The bottom note says so.

## First screen (17 Oct)
- The export also writes `affairs_head.json`: the affairs of the last 13 weeks, same columns (about 15 % of
  `affairs.json`). The app renders Neueste Woche from it and loads `affairs.json` in the background (`D.partial`,
  `D.full`); every other view waits for the full data. Woche's links carry the affair id, the topic id and the week's
  Monday, so they hold once the full data has replaced the slice.
