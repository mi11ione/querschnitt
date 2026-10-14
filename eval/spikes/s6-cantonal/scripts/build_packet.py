"""S6 Part B: blind annotation packet for the 160 A1 affairs. No LLM calls.
Writes ../packet/GUIDE.md, ../packet/items.txt (shuffled, opaque ids C001..), ../packet/ann_TEMPLATE.tsv and ../key.jsonl
(OUTSIDE packet/: opaque id -> affair id + Apertus outputs). The item text is the exact input block Apertus saw."""
import json, os, random, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from s6lib import S6, RAW6, APS_CODES, SUBS
import s1lib

SEED = 20261013
CH_DE = s1lib.CH_DE
NONE_CODE = '0'   # "no policy topic"


def main():
    sample = {s['sid']: s for s in json.load(open(f'{S6}/sample.json'))}
    a1 = {json.loads(l)['sid']: json.loads(l) for l in open(f'{RAW6}/a1.jsonl')}
    assert set(a1) == set(sample), (len(a1), len(sample))
    sids = sorted(sample); random.Random(SEED).shuffle(sids)
    code = lambda ci: NONE_CODE if ci == 24 else APS_CODES[ci]
    items, keys = [], []
    for k, sid in enumerate(sids):
        s, r = sample[sid], a1[sid]
        oid = f"C{k + 1:03d}"
        items.append(f"=== {oid} ===\nParlament: {s['body_name']} ({'Kanton' if s['level'] == 'cantonal' else 'Gemeinde/Stadt'})\n"
                     f"Typ: {s['type'] or '-'}\n\n{r['input_block']}\n")
        keys.append(dict(oid=oid, sid=sid, affair_id=s['id'], body=s['body'], level=s['level'], lang=s['lang'],
                         title_only=s['title_only'], text_kind=s['text_kind'],
                         apertus_final=code(r['final']), apertus_l1_top1=code(r['l1_top1']), apertus_l1_top1_p=round(r['l1_top1_p'], 4),
                         apertus_top3=[code(c) for c in r['l1_top3']], apertus_l2_sub=r['l2_sub'],
                         apertus_l2_p=round(r['l2_pick_p'], 4), order_disagree=r['order_disagree'],
                         second_order_run=r['pb'] is not None))
    os.makedirs(f'{S6}/packet', exist_ok=True)
    open(f'{S6}/packet/items.txt', 'w').write("\n".join(items))
    with open(f'{S6}/key.jsonl', 'w') as f:
        for k in keys: f.write(json.dumps(k, ensure_ascii=False) + '\n')
    open(f'{S6}/packet/ann_TEMPLATE.tsv', 'w').write("".join(f"{k['oid']}\t\t\n" for k in keys))
    chap = "\n".join(f"| `{APS_CODES[i]}` | **{CH_DE[i]}** | {'; '.join(SUBS[i])} |" for i in range(24))
    guide = f"""# Annotation guide: APS chapters for cantonal and municipal affairs

You get {len(keys)} parliamentary affairs from Swiss cantonal and municipal parliaments (2015 or later), in German, French or
Italian. For each affair, choose the **single best chapter** of the Année Politique Suisse (APS) scheme below, or
`{NONE_CODE}` for "no policy topic". You may add **one optional second chapter** if the affair clearly also belongs there.

## Input
`items.txt` has one block per affair: an opaque id (`C001` …), the parliament, the affair type and the text, exactly
as the model saw it: title, long title (if any), and for most affairs the first 1,500 characters of a document
(often the executive's reply, which usually restates the question). Some affairs are title-only. Judge only from this
text; do not look anything up. The ids are shuffled and say nothing about the affair.

## Output
Copy `ann_TEMPLATE.tsv` to `ann_A.tsv` (first annotator) or `ann_B.tsv` (second annotator) and save it in the s6 folder
(`.../spikes/s6-cantonal/`), one line per id, tab-separated:

```
<id>\\t<first chapter code>\\t<optional second chapter code>
C001\\t1.6.2.\\t
C002\\t1.4.1.\\t1.6.3.
C003\\t{NONE_CODE}\\t
```

Write the codes exactly as in the table, including the trailing dot. Leave the third column empty if there is no second chapter.
Work independently: do not compare answers with the other annotator, and do not look at `key.jsonl`.

## Rules
1. Code the **policy substance**, not the instrument (motion, question, report) or the institution answering.
2. Local matters map to the national chapter of the same substance: a municipal school building goes to *Bildung und Forschung*
   (`1.8.1.`) if the issue is schooling, to *Raumplanung und Wohnungswesen* (`1.6.3.`) if it is zoning or construction law, and to
   *Öffentliche Finanzen* (`1.5.`) only if the issue is the budget or the credit as such.
3. Cantonal and municipal finance, budgets, taxes and fiscal equalisation go to `1.5.` (subtopic *Finanzhaushalt der Kantone und
   Gemeinden*, *Direkte Steuern*, …).
4. *Föderativer Aufbau* (`1.1.4.`) covers relations between Confederation, cantons and municipalities, mergers of municipalities,
   and municipal autonomy; *Institutionen und Volksrechte* (`1.1.3.`) covers the parliament, government, administration and
   popular rights of the canton or municipality itself.
5. Use `{NONE_CODE}` only for affairs with no policy topic: elections or appointments of persons, naturalisations, resignations,
   pure council procedure.
6. If two chapters fit equally well, put the one the text spends more words on first.

## The 24 APS chapters (with their APS subtopics)
| Code | Chapter | Subtopics |
|---|---|---|
{chap}
| `{NONE_CODE}` | **Kein Sachthema** | Wahl oder Ernennung von Personen, Einbürgerung, Rücktritt, Verfahrensfragen des Rats |
"""
    open(f'{S6}/packet/GUIDE.md', 'w').write(guide)
    print('items', len(items))


if __name__ == '__main__':
    main()
