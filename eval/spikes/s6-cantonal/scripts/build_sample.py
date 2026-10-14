"""S6 A1: stratified sample of 160 non-federal OPD affairs (begin_date >= 2015): cantonal 100, communal 60.
Text items: on-disk extracted PDF text (first non-answer document). Title-only items: affairs with neither a substantive
texts row nor an ok document in the OPD census (flagged text_src='title-only'). Excludes the S1 sample. No network.
Usage: python3 -I build_sample.py  -> ../sample.json"""
import json, os, random, re, sys, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from opdtext import *  # noqa

OUT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
S1 = '/Users/mi11ion/Desktop/hackapertus/bern/ideation/spikes/s1-runtime'
rng = random.Random(20261013 + 6)

# (level, body, lang, kind, n)
QUOTA = [
    # cantonal, with text (82)
    ('cantonal', 'SG', 'de', 'text', 9), ('cantonal', 'SO', 'de', 'text', 7), ('cantonal', 'ZH', 'de', 'text', 7),
    ('cantonal', 'LU', 'de', 'text', 5), ('cantonal', 'TG', 'de', 'text', 3), ('cantonal', 'VS', 'de', 'text', 3),
    ('cantonal', 'JU', 'fr', 'text', 18), ('cantonal', 'VS', 'fr', 'text', 6), ('cantonal', 'FR', 'fr', 'text', 2),
    ('cantonal', 'TI', 'it', 'text', 22),
    # cantonal, title-only (18)
    ('cantonal', 'BS', 'de', 'title', 2), ('cantonal', 'AG', 'de', 'title', 2), ('cantonal', 'BL', 'de', 'title', 2),
    ('cantonal', 'BE', 'de', 'title', 1), ('cantonal', 'ZG', 'de', 'title', 1), ('cantonal', 'GR', 'de', 'title', 1),
    ('cantonal', 'SZ', 'de', 'title', 1),
    ('cantonal', 'GE', 'fr', 'title', 3), ('cantonal', 'VD', 'fr', 'title', 3), ('cantonal', 'NE', 'fr', 'title', 2),
    # communal, with text (48)
    ('communal', '4001', 'de', 'text', 8), ('communal', '131', 'de', 'text', 5), ('communal', '581', 'de', 'text', 3),
    ('communal', '2831', 'de', 'text', 3), ('communal', '4289', 'de', 'text', 2), ('communal', '4566', 'de', 'text', 2),
    ('communal', '4671', 'de', 'text', 1),
    ('communal', '5586', 'fr', 'text', 7),   # all 7 usable Lausanne texts (overlap with S1 allowed here)
    ('communal', '5002', 'it', 'text', 7), ('communal', '5113', 'it', 'text', 7),
    # communal, title-only (12)
    ('communal', '261', 'de', 'title', 1), ('communal', '351', 'de', 'title', 1), ('communal', '230', 'de', 'title', 1),
    ('communal', '3203', 'de', 'title', 1),
    ('communal', '6621', 'fr', 'title', 2), ('communal', '2196', 'fr', 'title', 1), ('communal', '6643', 'fr', 'title', 1),
    ('communal', '6458', 'fr', 'title', 1), ('communal', '2125', 'fr', 'title', 1), ('communal', '6248', 'fr', 'title', 1),
    ('communal', '6421', 'fr', 'title', 1),
    ('communal', '5192', 'it', 'title', 2), ('communal', '5254', 'it', 'title', 1),
]

STOP = {'de': ' der die und das nicht ist mit für den von zu auf des ein eine wird werden im ',
        'fr': ' le la les et des du une un est pour dans que qui par sur au aux pas ',
        'it': ' il la le di che e per una un del della dei non sono con nel alla gli '}
STOP = {k: set(v.split()) for k, v in STOP.items()}


def text_lang(t):
    w = re.findall(r"[a-zàâäéèêëïîôöùûüç]+", t.lower())
    sc = {k: sum(x in s for x in w) for k, s in STOP.items()}
    return max(sc, key=sc.get)


def main():
    A = load_affairs(); ht, hd = census_sets(); sp, ad = doc_map()
    s1ids = {s['id'] for s in json.load(open(f'{S1}/sample.json'))}
    used = set(s1ids)
    sample, log = [], collections.Counter()
    for lev, bk, lang, kind, n in QUOTA:
        excl = used - s1ids if bk == '5586' else used
        pool = [a for a in A.values() if a['body_key'] == bk and (a['begin_date'] or '') >= '2015' and a.get(f'title_{lang}')
                and a['id'] not in excl]
        if kind == 'text': pool = [a for a in pool if a['id'] in ad]
        else: pool = [a for a in pool if a['id'] not in ht and a['id'] not in hd]
        pool.sort(key=lambda a: a['id']); rng.shuffle(pool)
        got = 0
        for a in pool:
            if got >= n: break
            if kind == 'text':
                t, src, tk, sk = pdf_text(a['id'], sp, ad, title=clean(a.get(f'title_{lang}')))
                log['answer_docs_skipped'] += sk
                if not t: log['no_nonanswer_doc'] += 1; continue
                if text_lang(t) != lang: log['text_lang_mismatch'] += 1; continue
            else:
                t, src, tk = '', 'title-only', 'title-only'
            used.add(a['id']); got += 1
            sample.append(dict(id=a['id'], body=bk, body_name=body_name(bk), level=lev, lang=lang,
                               title=clean(a.get(f'title_{lang}')), title_long=clean(a.get(f'title_long_{lang}')),
                               type=a.get(f'type_name_{lang}') or a.get('type_harmonized_de') or a.get('type_name_de') or '',
                               begin_date=(a['begin_date'] or '')[:10], number=a.get('number'), text=t, text_src=src, text_kind=tk,
                               title_only=(kind == 'title'), in_s1=a['id'] in s1ids))
        if got < n: log[f'short:{bk}/{lang}/{kind}'] = n - got
    for i, s in enumerate(sample): s['sid'] = i
    json.dump(sample, open(f'{OUT}/sample.json', 'w'), ensure_ascii=False, indent=0)
    C = collections.Counter
    print(len(sample), dict(log))
    print(C(s['level'] for s in sample), C((s['level'], s['lang']) for s in sample))
    print('title-only', C((s['level'], s['title_only']) for s in sample))
    print('bodies', {lv: len({s['body'] for s in sample if s['level'] == lv}) for lv in ('cantonal', 'communal')})
    print('text_kind', C(s['text_kind'] for s in sample))
    print('types', C(s['type'] for s in sample).most_common(15))


if __name__ == '__main__':
    main()
