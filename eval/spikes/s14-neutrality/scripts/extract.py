"""S14 step 1: pull contributor (author/cosign) rows and affair types for every affair id used by S6, S8, S9, S10.
Inputs: OPD 6 Oct export contributors.ndjson.gz (gegenprobe .work copy), affairs.ndjson.gz, bodies.ndjson.gz. Output: data/opd_subset.json"""
import gzip, json, os, collections
H = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
B2 = '/Users/mi11ion/Desktop/hackapertus/bern/ideation2/spikes'; B1 = '/Users/mi11ion/Desktop/hackapertus/bern/ideation/spikes'
OPD = '/Users/mi11ion/Desktop/hackapertus/spikes/data/raw/opd'
ids = set()
ids |= {int(x['oid']) for x in json.load(open(f'{B2}/s9-aps/data/items.json'))}
ids |= {int(json.loads(l)['oid']) for l in open(f'{B2}/s8-dvs/key.jsonl')}
ids |= {int(json.loads(l)['affair_id']) for l in open(f'{B1}/s6-cantonal/key.jsonl')}
ids |= {int(json.loads(l)['affair_id']) for l in open(f'{B2}/s10-bilingual/key.jsonl')}
KEEP = ('id', 'affair_id', 'body_key', 'type', 'role_de', 'role_harmonized', 'fullname', 'person_id', 'group_id', 'party_de',
        'party_harmonized_de', 'position')
contrib = collections.defaultdict(list)
for l in gzip.open('/Users/mi11ion/Desktop/hackapertus/gegenprobe/track_2a/.work/opd/contributors.ndjson.gz', 'rt'):
    r = json.loads(l)
    if r['affair_id'] in ids: contrib[r['affair_id']].append({k: r.get(k) for k in KEEP})
aff = {}
for l in gzip.open(f'{OPD}/affairs.ndjson.gz', 'rt'):
    r = json.loads(l)
    if int(r['id']) in ids: aff[int(r['id'])] = dict(body_key=r['body_key'], type=r.get('type_harmonized_de') or r.get('type_name_de'),
                                                   type_raw=r.get('type_name_de'), number=r.get('number'))
bodies = {}
for l in gzip.open(f'{OPD}/bodies.ndjson.gz', 'rt'):
    r = json.loads(l)
    bodies[r['body_key']] = dict(canton=r['canton_key'], lang=r['lang'], type=r['type'], name=r['name'])
json.dump(dict(ids=len(ids), contributors={str(k): v for k, v in contrib.items()}, affairs={str(k): v for k, v in aff.items()},
               bodies=bodies), open(f'{H}/data/opd_subset.json', 'w'), ensure_ascii=False)
print(len(ids), 'ids;', len(contrib), 'with contributors;', len(aff), 'affairs found')
