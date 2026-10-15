# Annotation guide

Each line of `items.tsv` is one Swiss parliamentary affair: id, parliament, level, type, date, title, long title, and the
start of its text where one exists (any of German, French, Italian). Judge only from this text; look nothing up. The topic
was defined by a user in one sentence:

**«Drohnen: ihr Einsatz durch Polizei, Armee und Behörden, Regeln für private Drohnen und die Abwehr von Drohnen»**

Question for every affair: **Does this affair concern the topic defined by this sentence?** Answer `Y` (yes) or `N` (no). If
you cannot decide, answer the more likely one and add `?` in a third column. Copy `ann_TEMPLATE.tsv` to your output file (one
line per id: `<id>\tY|N[\t?]`). Work alone; do not open any file outside this folder.
