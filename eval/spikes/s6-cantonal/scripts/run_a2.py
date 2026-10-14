"""S6 A2: Bern directorates as a scheme swap. 200 Grand Council affairs (begin >= 2015 by geschaeft_nr year, DE + FR titles,
lead directorate in the 8 directorates; GR / blank / JL excluded). M1 (9 codes A-I, one fixed order) on the DE title and,
separately, on the FR title with a FR prompt.
Usage: python3 -I run_a2.py sample | run [workers<=8]   -> ../a2_sample.json, ../raw/a2.jsonl"""
import csv, json, os, sys, random
from multiprocessing import Pool
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from s6lib import *  # noqa
import be_scheme as B

CSV = '/Users/mi11ion/Desktop/hackapertus/gegenprobe/track_2a/.work/be_ogd/geschaeft.csv'
SAMPLEF = f'{S6}/a2_sample.json'; OUTF = f'{RAW6}/a2.jsonl'


def eligible():
    rows = list(csv.DictReader(open(CSV, encoding='utf-8-sig')))
    out = []
    for r in rows:
        yr = (r['geschaeft_vorstoss_eingereicht_datum'] or '')[:4] or r['geschaeft_nr'][:4]
        if yr < '2015': continue
        d = r['geschaeft_federfuehrung_kuerzel_deutsch']
        if d not in B.DIRS: continue
        de, fr = r['geschaeft_titel_deutsch'].strip(), r['geschaeft_titel_franz'].strip()
        if not de or not fr: continue
        out.append(dict(uid=r['geschaeft_uid'], nr=r['geschaeft_nr'], year=yr, lead=d, type=r['geschaeft_typ_deutsch'],
                        title_de=de, title_fr=fr))
    return out


def build():
    el = eligible(); el.sort(key=lambda x: x['uid'])
    rng = random.Random(20261013 + 62)
    smp = rng.sample(el, 200)
    import collections
    prior = [d for d, _ in collections.Counter(x['lead'] for x in el).most_common()]
    json.dump(dict(n_eligible=len(el), prior=prior, items=smp), open(SAMPLEF, 'w'), ensure_ascii=False, indent=0)
    print(len(el), prior, collections.Counter(x['lead'] for x in smp), collections.Counter(x['type'] for x in smp).most_common(8))


_N = 0
def run(t):
    global _N
    _N += 1
    if _N % 40 == 1 and spent_s6() > S6_CAP - 0.10: raise RuntimeError('S6 cap')
    it, lang = t
    try:
        u, pf = B.prompt(it[f'title_{lang}'], lang)
        d, _, rec = m1_6(u, pf, f'bern-s6-a2{lang}', B.CODES)
        p = to_probs(d, B.CODES, 9)
        s1lib.log(OUTF, dict(key=f"{it['uid']}-{lang}", uid=it['uid'], lang=lang, lead=it['lead'], p=p, codes=d,
                             pred=(B.DIRS + ['none'])[max(range(9), key=lambda i: p[i])],
                             mass=round(sum(math.exp(v) for v in d.values()), 5), rec=rec))
        return t[0]['uid'], 'ok'
    except Exception as e:
        s1lib.log(f'{RAW6}/errors.jsonl', dict(phase='a2', uid=it['uid'], lang=lang, err=repr(e)[:500]))
        return it['uid'], repr(e)[:200]


if __name__ == '__main__':
    if sys.argv[1] == 'sample': build(); sys.exit()
    workers = int(sys.argv[2]) if len(sys.argv) > 2 else 4
    assert workers <= 8
    items = json.load(open(SAMPLEF))['items']
    done = {json.loads(l)['key'] for l in open(OUTF)} if os.path.exists(OUTF) else set()
    ts = [(it, L) for it in items for L in ('de', 'fr') if f"{it['uid']}-{L}" not in done]
    if len(sys.argv) > 3: ts = ts[:int(sys.argv[3])]
    print('a2 todo', len(ts), flush=True)
    with Pool(workers) as pool:
        for i, (k, st) in enumerate(pool.imap_unordered(run, ts)):
            if st != 'ok' or i % 50 == 0: print(i, k, st, flush=True)
            if 'BUILD CHANGED' in st: pool.terminate(); break
    print('spent bern-s6-*:', round(spent_s6(), 4), flush=True)
