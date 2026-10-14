"""Build S9 items from what is on disk now (re-runnable while fetching continues). No network, no model.
Item fields mirror ideation-1 s3-accuracy/build_data.py (APS part): title = Curia Title or oracle title or OPD title;
title_long = OPD title_long if different; text = clean(SubmittedText or InitialSituation or Description) + ReasonText.
Same for FR (fr block). Gold = chapter_code (24 APS chapters), main subtopic name if among the 190 DE names.
Output data/items.json (only items with a chapter and a Curia DE record or title)."""
import gzip, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from s9lib import DATA, S2D, S3, APS_CODES, SUBS, clean

def opd_titles(need):
    p = f"{DATA}/opd_che_titles.json"
    if os.path.exists(p):
        return {int(k): v for k, v in json.load(open(p)).items()}
    out = {}
    for l in gzip.open('/Users/mi11ion/Desktop/hackapertus/spikes/data/raw/opd/affairs.ndjson.gz', 'rt'):
        if '"body_key":"CHE"' not in l: continue
        r = json.loads(l)
        if int(r['id']) in need:
            out[int(r['id'])] = {k: r.get(k) for k in ('number', 'title_de', 'title_fr', 'title_long_de', 'title_long_fr', 'begin_date')}
    json.dump(out, open(p, 'w'), ensure_ascii=False)
    return out

def oracle():
    o = {}
    for l in gzip.open(f'{S2D}/oracle_curia.jsonl.gz', 'rt'):
        r = json.loads(l); o[r['opd_affair_id']] = r
    return o

def texts(path):
    at = {}
    if os.path.exists(path):
        op = gzip.open if path.endswith('.gz') else open
        for l in op(path, 'rt'):
            r = json.loads(l)
            body = clean(r.get('SubmittedText')) or clean(r.get('InitialSituation')) or clean(r.get('Description'))
            at[r['ID']] = dict(title=clean(r.get('Title')), text=" ".join(x for x in (body, clean(r.get('ReasonText'))) if x))
    return at

def derive(num):
    yy, n = num.split("."); return int(("19" if int(yy) >= 90 else "20") + yy) * 10000 + int(n)

def make(a, O, opd, tde, tfr):
    """a: APS record (opd_affair_id, curia_number). Mirrors build_data.py for DE; FR analogous."""
    o = O.get(a['opd_affair_id']); r = opd.get(a['opd_affair_id'], {})
    cid = o['curia_id'] if o else derive(a['curia_number'])
    out = {}
    for lang, at in (('de', tde), ('fr', tfr)):
        tx = at.get(cid)
        title = (tx or {}).get('title') or (o or {}).get('titles', {}).get(lang) or r.get(f'title_{lang}') or ''
        tl = r.get(f'title_long_{lang}') or ''
        out[lang] = dict(title=title, title_long=tl if tl and tl != title else '', text=(tx or {}).get('text') or '',
                         has_curia=bool(tx))
    return cid, out

if __name__ == '__main__':
    joined = json.load(open(f"{S2D}/raw_cdx/overlap.json"))["proc_joined"]
    old = [json.loads(l) for l in open(f"{S2D}/aps_gold_sample.jsonl")]
    need = {v[1] for v in joined.values()} | {x['opd_affair_id'] for x in old}
    opd = opd_titles(need); O = oracle()
    tde, tfr = texts(f'{DATA}/curia_texts_de.jsonl'), texts(f'{DATA}/curia_texts_fr.jsonl')
    old_a = {x['opd_affair_id'] for x in old}
    items, seen = [], set()
    ext = []
    if os.path.exists(f'{DATA}/aps_ext.jsonl'):
        for l in open(f'{DATA}/aps_ext.jsonl'):
            try: ext.append(json.loads(l))
            except ValueError: pass   # line being written by the fetcher
    for a in ext:
        if a['opd_affair_id'] in seen or a['opd_affair_id'] in old_a or a.get('chapter_code') not in APS_CODES: continue
        seen.add(a['opd_affair_id'])
        cid, L = make(a, O, opd, tde, tfr)
        if not L['de']['title']: continue
        ch = APS_CODES.index(a['chapter_code'])
        yy = int(a['curia_number'][:2]); year = (1900 if yy >= 90 else 2000) + yy
        items.append(dict(oid=a['opd_affair_id'], cid=cid, curia_number=a['curia_number'], year=year,
                          period='pre-2010' if year < 2010 else '2010-19' if year < 2020 else '2020+',
                          chapter=ch, chapter_code=a['chapter_code'], subtopic_name=a.get('subtopic_name'),
                          sub_gold=a.get('subtopic_name') in SUBS[ch], join_quality=a['join_quality'],
                          keyword_chapters=a.get('keyword_chapters'), de=L['de'], fr=L['fr'],
                          curia_fetched=L['de']['has_curia'] or L['fr']['has_curia']))
    # ideation-1 298 for the D3 memory pool (DE titles), built the same way from S3's Curia DE texts
    t3 = texts(f'{S3}/data/aps_curia_texts_de.jsonl.gz')
    mem_old, seen_o = [], set()
    for a in old:
        if a['opd_affair_id'] in seen_o or a.get('chapter_code') not in APS_CODES: continue
        seen_o.add(a['opd_affair_id'])
        _, L = make(a, O, opd, t3, {})
        mem_old.append(dict(oid=a['opd_affair_id'], title=L['de']['title'], chapter=APS_CODES.index(a['chapter_code'])))
    json.dump(items, open(f'{DATA}/items.json', 'w'), ensure_ascii=False)
    json.dump(mem_old, open(f'{DATA}/mem_ideation1.json', 'w'), ensure_ascii=False)
    print('items', len(items), 'with curia', sum(i['curia_fetched'] for i in items), 'de text', sum(bool(i['de']['text']) for i in items),
          'fr title', sum(bool(i['fr']['title']) for i in items), 'sub_gold', sum(i['sub_gold'] for i in items), 'mem_old', len(mem_old))
