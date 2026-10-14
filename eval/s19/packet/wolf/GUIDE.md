# Annotation guide — topic «Wolf und Grossraubtiere»

Each line of `items.tsv` is one Swiss parliamentary affair: id, parliament, level, type, date, title, long title (any of
German, French, Italian). Judge only from this text; look nothing up. Question for every affair:

**Betrifft das folgende parlamentarische Geschäft das Thema «Wolf und Grossraubtiere» (Wolf, Bär, Luchs, Goldschakal, Regulierung und Abschuss, Herdenschutz, Schäden an Nutztieren, Jagd- und Schutzstatus)?**

Answer `Y` (yes, the affair concerns this topic) or `N` (no). If you cannot decide, answer the more likely one and add `?`
in a third column. Copy `ann_TEMPLATE.tsv` to your output file (one line per id: `<id>\tY|N[\t?]`). Work alone; do not
open any file outside this folder.
