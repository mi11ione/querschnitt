"""S10 blind annotation packet. No model calls. Needs ../raw/l1.jsonl complete (210 rows).
packet/GUIDE.md = byte copy of S6 packet/GUIDE.md (unchanged, PREREG). packet/items.txt: opaque ids B001..B210 in an order
shuffled with random.Random(20261014); shown language: per canton a seeded half (35) German, the other half (35) French
(random.Random(20261014 + 1), cantons BE, FR, VS in order). Item text = exactly the block Apertus saw in that language,
plus parliament and type (S6 format). key.jsonl (OUTSIDE packet/): id -> affair, canton, shown language, model outputs.
Usage: python3 -I build_packet.py"""
import json, os, random, shutil, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from s10lib import S10, RAW, code, argsort_desc

SEED = 20261014
S6_GUIDE = '/Users/mi11ion/Desktop/hackapertus/bern/ideation/spikes/s6-cantonal/packet/GUIDE.md'


def main():
    sample = {s['sid']: s for s in json.load(open(f'{S10}/sample.json'))}
    l1 = {json.loads(l)['sid']: json.loads(l) for l in open(f'{RAW}/l1.jsonl')}
    assert set(l1) == set(sample), (len(l1), len(sample))
    rng_lang = random.Random(SEED + 1); shown = {}
    for bk in ('BE', 'FR', 'VS'):
        ids = sorted(k for k, s in sample.items() if s['body'] == bk)
        de = set(rng_lang.sample(ids, len(ids) // 2))
        for k in ids: shown[k] = 'de' if k in de else 'fr'
    sids = sorted(sample); random.Random(SEED).shuffle(sids)
    items, keys = [], []
    for n, sid in enumerate(sids):
        s, r, lg = sample[sid], l1[sid], shown[sid]
        oid = f"B{n + 1:03d}"
        items.append(f"=== {oid} ===\nParlament: {s['body_name']} (Kanton)\nTyp: {s['type_' + lg] or '-'}\n\n{r['input_' + lg]}\n")
        keys.append(dict(oid=oid, sid=sid, affair_id=s['id'], number=s['number'], canton=s['body'], begin_date=s['begin_date'],
                         shown_lang=lg,
                         apertus_de=code(r['top1_de']), apertus_fr=code(r['top1_fr']), apertus_pooled=code(r['top1_pooled']),
                         p_de=round(r['p_de'][r['top1_de']], 4), p_fr=round(r['p_fr'][r['top1_fr']], 4),
                         p_pooled=round(r['p_pooled'][r['top1_pooled']], 4),
                         top3_de=[code(c) for c in argsort_desc(r['p_de'])[:3]], top3_fr=[code(c) for c in argsort_desc(r['p_fr'])[:3]],
                         top3_pooled=[code(c) for c in argsort_desc(r['p_pooled'])[:3]], agree=r['agree']))
    os.makedirs(f'{S10}/packet', exist_ok=True)
    shutil.copyfile(S6_GUIDE, f'{S10}/packet/GUIDE.md')
    open(f'{S10}/packet/items.txt', 'w').write("\n".join(items))
    open(f'{S10}/packet/ann_TEMPLATE.tsv', 'w').write("".join(f"{k['oid']}\t\t\n" for k in keys))
    with open(f'{S10}/key.jsonl', 'w') as f:
        for k in keys: f.write(json.dumps(k, ensure_ascii=False) + '\n')
    print('items', len(items), 'shown de', sum(k['shown_lang'] == 'de' for k in keys))


if __name__ == '__main__':
    main()
