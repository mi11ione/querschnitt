# Annotation guide: does the quoted sentence support the proposed topic?

You get 200 parliamentary affairs from Swiss parliaments (federal, cantonal and municipal; begun in 2026), in German, French
or Italian. Each block in `items.txt` shows:

- an opaque id (`E001` …; the ids are shuffled and say nothing about the affair),
- the parliament and the affair type,
- the affair text: title, long title (if any, first 400 characters) and the first 1,500 characters of the text (some affairs
  have a title only),
- a **proposed topic**: either one chapter of the Année Politique Suisse (APS) scheme (e.g. «Landwirtschaft»,
  «Sozialversicherungen») or the topic «Digitalisierung» (digitalisation),
- a **quoted sentence** taken from the affair (title, long title or text).

## Task
For each affair, answer **Y** if the quoted sentence, read on its own, gives a reason to say that the affair concerns the
proposed topic. Answer **N** otherwise.

Judge the sentence, not the topic. The question is not "is this the best topic for the affair?" but "does this sentence, by
itself, point to this topic?". Use the affair text only to understand what the sentence refers to (e.g. what "diese
Massnahme" means).

- **Y**: the sentence names or clearly describes subject matter that belongs to the proposed topic (e.g. a sentence about
  nitrogen losses from farming for «Landwirtschaft»; a sentence asking for changes to the Criminal Code for «Rechtsordnung»;
  a sentence about an online portal or electronic records for «Digitalisierung»).
- **N**: the sentence is generic or procedural and would fit almost any affair ("Der Bundesrat wird beauftragt, einen
  Bericht vorzulegen.", "Il Municipio è invitato a rispondere alle seguenti domande."), or it is about a different subject
  than the proposed topic, or it is a fragment (letterhead, names, dates, addresses) that carries no topical content.
- If the proposed topic looks wrong for the affair but the quoted sentence nevertheless points to it, answer Y. If the topic
  looks right but the sentence gives no reason for it, answer N.
- When in doubt, ask: would a reader who sees only this sentence and the topic name find the sentence a reason for the
  topic? If not clearly, answer N.

Judge only from the text shown; do not look anything up.

## Output
Copy `ann_TEMPLATE.tsv` to `ann_A.tsv` (first annotator), `ann_B.tsv` (second annotator) or `ann_C.tsv` (tie-break
annotator, only the ids listed in `ann_C_TEMPLATE.tsv`) and save it in the folder you are told to use, one line per id,
tab-separated:

```
E001	Y
E002	N
```

Exactly `Y` or `N` in the second column, one line per id, every id answered. Work independently: do not compare answers
with other annotators, and do not open `key.jsonl` or any file outside `packet/`.
