"""S10 sample (PREREG S10). 70 affairs each from OPD body keys BE, FR, VS (Grand Councils) with title_de and title_fr both
non-empty (after clean()), begin_date >= 2025-01-01, de title != fr title, and neither title matching the frozen
personnel regex EXCL below (elections, appointments, resignations, naturalisations, oaths, pardons, seat successions).
EXCL was written and frozen before any S10 model call; its sha256 is printed and stored in sample_meta.json.
Seed 20261014: per canton (order BE, FR, VS) the eligible pool is sorted by affair id and shuffled with one shared
random.Random(SEED); first 70 taken. No network. Usage: python3 -I sample.py -> ../sample.json, ../sample_meta.json"""
import gzip, json, re, random, hashlib, os, collections

OPD = '/Users/mi11ion/Desktop/hackapertus/spikes/data/raw/opd'
OUT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SEED = 20261014
CANTONS = ('BE', 'FR', 'VS')
N_PER = 70

# ---- FROZEN personnel-affair regex (de + fr), applied to title_de and title_fr; a hit in either excludes the affair
EXCL_SRC = (
    r"\b(ersatz|wieder|bestätigungs|gesamterneuerungs|richterliche\s+)?wahl(en)?\b|wahlen\b|\bgewählt|"
    r"\bernennung|\brücktritt|\bdemission|\beinbürgerung|\bvereidigung|\bamtsgelübde|\binpflichtnahme|"
    r"\bbeisitzer|\bersatzmitglied|\bersatzrichter|\bnachfolger|\bnachrücken|eintritt eines neuen mitglieds|"
    r"\bbegnadigung|\bfriedensrichter|\bstaatsanwält|\bstaatsanwalt\b|\bpräsident/-?in|"
    r"\b(r[ée])?[ée]lections?\b|\b[ée]lue?s?\b|\bnomination|\bd[ée]mission|\bnaturalisation|\bassermentation|"
    r"\bprestation de serment|\bassesseu|\bsuppl[ée]ant|en remplacement de|entr[ée]e d.un nouveau membre|"
    r"\brecours en gr[âa]ce|\bjuge de paix|\bprocureur|\bpr[ée]sident-e|\bvice-pr[ée]sident-e"
)
EXCL = re.compile(EXCL_SRC, re.I)
EXCL_SHA = hashlib.sha256(EXCL_SRC.encode()).hexdigest()

BODY_NAME = {'BE': 'Grosser Rat des Kantons Bern', 'FR': 'Grosser Rat des Kantons Freiburg', 'VS': 'Grosser Rat des Kantons Wallis'}


def clean(s):   # = S6 opdtext.clean
    s = re.sub(r'<[^>]+>', ' ', s or '')
    return re.sub(r'\s+', ' ', s).strip()


def main():
    pool = collections.defaultdict(list); log = collections.Counter()
    for l in gzip.open(f'{OPD}/affairs.ndjson.gz', 'rt'):
        a = json.loads(l); bk = a.get('body_key')
        if bk not in CANTONS or (a.get('begin_date') or '') < '2025-01-01': continue
        td, tf = clean(a.get('title_de')), clean(a.get('title_fr'))
        if not td or not tf: log[f'{bk}:missing_title'] += 1; continue
        if td == tf: log[f'{bk}:identical_titles'] += 1; continue
        if EXCL.search(td) or EXCL.search(tf): log[f'{bk}:excl_regex'] += 1; continue
        log[f'{bk}:eligible'] += 1
        pool[bk].append(dict(
            id=a['id'], body=bk, body_name=BODY_NAME[bk], number=a.get('number'), begin_date=(a.get('begin_date') or '')[:10],
            title_de=td, title_fr=tf, title_long_de=clean(a.get('title_long_de')), title_long_fr=clean(a.get('title_long_fr')),
            type_de=a.get('type_name_de') or a.get('type_harmonized_de') or '',
            type_fr=a.get('type_name_fr') or a.get('type_harmonized_fr') or ''))
    rng = random.Random(SEED); sample = []
    for bk in CANTONS:
        p = sorted(pool[bk], key=lambda x: x['id']); rng.shuffle(p)
        assert len(p) >= N_PER, (bk, len(p))
        sample += p[:N_PER]
    for i, s in enumerate(sample): s['sid'] = i
    json.dump(sample, open(f'{OUT}/sample.json', 'w'), ensure_ascii=False, indent=0)
    meta = dict(seed=SEED, n_per=N_PER, excl_regex=EXCL_SRC, excl_sha256=EXCL_SHA, counts=dict(sorted(log.items())),
                with_long_de=sum(bool(s['title_long_de']) for s in sample), with_long_fr=sum(bool(s['title_long_fr']) for s in sample))
    json.dump(meta, open(f'{OUT}/sample_meta.json', 'w'), ensure_ascii=False, indent=1)
    print(json.dumps(meta, ensure_ascii=False, indent=1))


if __name__ == '__main__':
    main()
