"""Fixed task order after the lead's 18:23 UTC change (seed 20261015). Writes order.json (never rewritten once it exists)."""
import json, os, random, sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from common import HERE
assert not os.path.exists(f'{HERE}/order.json'), 'order.json exists - frozen'
I = [x for x in json.load(open(f'{HERE}/items_cache.json')) if x['title']]
A = {json.loads(l)['id'] for l in open(f'{HERE}/raw/a.jsonl')}
CENSUS_FROM = '2026-09-30'   # 30 Sep partially scored at the switch (82/150) -> completed so census days are whole
census_rest = sorted(x['id'] for x in I if x['in_window'] and x['date'] >= CENSUS_FROM and x['id'] not in A)
dvs = sorted(x['id'] for x in I if x['on_dvs_list'] and x['id'] not in A and x['id'] not in census_rest)
srs_pop = sorted(x['id'] for x in I if x['in_window'] and x['date'] < CENSUS_FROM)
rnd = list(srs_pop); random.Random(20261015).shuffle(rnd)
json.dump(dict(census_from=CENSUS_FROM, scored_before_switch=len(A), census_rest=census_rest, dvs=dvs, srs=rnd,
               note='run order: B for already-scored, census_rest, dvs (for P8.2 only), srs in this seeded random order'), open(f'{HERE}/order.json', 'w'))
print(len(A), len(census_rest), len(dvs), len(srs_pop))
