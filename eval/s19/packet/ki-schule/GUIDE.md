# Annotation guide — topic «Künstliche Intelligenz an Schulen»

Each line of `items.tsv` is one Swiss parliamentary affair: id, parliament, level, type, date, title, long title (any of
German, French, Italian). Judge only from this text; look nothing up. Question for every affair:

**Betrifft das folgende parlamentarische Geschäft das Thema «Künstliche Intelligenz an Schulen» (KI im Unterricht, KI-Werkzeuge wie ChatGPT für Schülerinnen, Schüler und Lehrpersonen, Prüfungen und Plagiate mit KI, KI-Kompetenzen im Lehrplan, Datenschutz beim KI-Einsatz in der Bildung)?**

Answer `Y` (yes, the affair concerns this topic) or `N` (no). If you cannot decide, answer the more likely one and add `?`
in a third column. Copy `ann_TEMPLATE.tsv` to your output file (one line per id: `<id>\tY|N[\t?]`). Work alone; do not
open any file outside this folder.
