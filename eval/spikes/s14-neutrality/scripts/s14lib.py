"""S14 shared helpers: Wilson, chi-square tail, permutation test, party mapping, submitter, canton/region. No network, no model calls."""
import json, math, os, random, re, collections
H = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OPD = json.load(open(f'{H}/data/opd_subset.json'))
CONTRIB, AFF, BODIES = OPD['contributors'], OPD['affairs'], OPD['bodies']

def wilson(k, n, z=1.96):
    if n == 0: return [None, None]
    p = k / n; d = 1 + z * z / n
    c = (p + z * z / (2 * n)) / d; h = z * math.sqrt(p * (1 - p) / n + z * z / (4 * n * n)) / d
    return [round(c - h, 4), round(c + h, 4)]

def _gser(a, x):
    s = t = 1.0 / a; ap = a
    for _ in range(1000):
        ap += 1; t *= x / ap; s += t
        if abs(t) < abs(s) * 1e-14: break
    return s * math.exp(-x + a * math.log(x) - math.lgamma(a))

def _gcf(a, x):
    b = x + 1 - a; c = 1e300; d = 1 / b; h = d
    for i in range(1, 1000):
        an = -i * (i - a); b += 2; d = an * d + b; d = d if abs(d) > 1e-300 else 1e-300
        c = b + an / c; c = c if abs(c) > 1e-300 else 1e-300; d = 1 / d; de = d * c; h *= de
        if abs(de - 1) < 1e-14: break
    return math.exp(-x + a * math.log(x) - math.lgamma(a)) * h

def chi2_sf(x, df):
    if df <= 0: return None
    if x <= 0: return 1.0
    a, y = df / 2, x / 2
    return 1 - _gser(a, y) if y < a + 1 else _gcf(a, y)

def stat(groups, y, w):
    """weighted between-group chi-square-like statistic: sum_g n_g (p_g - p)^2 / (p (1-p)); p_g, p weighted by w.
    With w == 1 this is exactly Pearson's chi-square for a G x 2 table."""
    sw = collections.defaultdict(float); sy = collections.defaultdict(float); n = collections.Counter()
    for g, yi, wi in zip(groups, y, w): sw[g] += wi; sy[g] += wi * yi; n[g] += 1
    W = sum(sw.values()); p = sum(sy.values()) / W if W else 0
    if p <= 0 or p >= 1: return 0.0
    return sum(n[g] * (sy[g] / sw[g] - p) ** 2 for g in n) / (p * (1 - p))

def perm_test(groups, y, w=None, strata=None, n=5000, seed=14):
    """permutation p-value of `stat`, group labels shuffled within strata (design-preserving for S8)."""
    w = w or [1.0] * len(y); strata = strata or [0] * len(y)
    if len(set(groups)) < 2: return dict(stat=None, p_perm=None, df=0, p_chi2=None)
    s0 = stat(groups, y, w); rng = random.Random(seed)
    idx = collections.defaultdict(list)
    for i, s in enumerate(strata): idx[s].append(i)
    ge = 0
    for _ in range(n):
        g2 = list(groups)
        for s, ii in idx.items():
            lab = [groups[i] for i in ii]; rng.shuffle(lab)
            for i, l in zip(ii, lab): g2[i] = l
        ge += stat(g2, y, w) >= s0 - 1e-12
    df = len(set(groups)) - 1
    return dict(stat=round(s0, 3), df=df, p_perm=round((ge + 1) / (n + 1), 4),
                p_chi2=round(chi2_sf(s0, df), 4) if all(x == 1.0 for x in w) else None)

# ---------------- party mapping
def party_group(s):
    if not s or s.strip() in ('{}', 'None'): return None
    t = s.replace('Ã¼', 'ü').lower()
    if re.search(r'grünliberal|grunliberal|vert.?libéra|\bglp\b|\bpvl\b|verdi liberali', t): return 'GLP'
    if re.search(r'neo - die sozialliberale|mitte links|centre gauche', t): return 'other party'
    if re.search(r'evangelische volkspartei|\bevp\b|\bpev\b', t): return 'other party'
    if re.search(r'die mitte|\bmitte\b|le centre|il centro|\bcvp\b|christlichdemokrat|\bpdc\b|\bppd\b|\bbdp\b|bürgerlich-demokrat|fraktion bd|\bcspo\b|\bcvpo\b', t): return 'Mitte'
    if re.search(r'volkspartei|\bsvp\b|\budc\b|unione democratica di centro|schweizerischen volkspartei', t): return 'SVP'
    if re.search(r'sozialdemokrat|\bsp\b|socialist|\bps\b|partito socialista|sozialdemokratische', t): return 'SP'
    if re.search(r'\bfdp\b|\bplr\b|freisinn|liberal-demokrat|\bldp\b|libéral-radical|liberale radicale|fdp-liberale', t): return 'FDP'
    if re.search(r'grüne|grüne|\bvert|verdi|basels starke alternative|grüne fraktion', t): return 'Grüne'
    return 'other party'

MAIN = ['SVP', 'SP', 'FDP', 'Mitte', 'Grüne', 'GLP']
CO = re.compile(r'mit|regierungsvertreter|beteiligung|cosign|co-sign|cofirmat|cosignat', re.I)

def submitter(aid):
    """-> (category, detail). Federal: author rows with role 'Urheber(-in)'/'Behörde' (not 'Berichterstattung').
    Other bodies: author rows whose raw role is not a co-signer role; first by position."""
    aid = str(aid); a = AFF.get(aid, {}); rows = CONTRIB.get(aid, [])
    fed = a.get('body_key') == 'CHE'
    au = [r for r in rows if r['role_harmonized'] == 'author']
    if fed: au = [r for r in au if (r['role_de'] or '').startswith(('Urheber', 'Behörde'))]
    else: au = [r for r in au if not CO.search(r['role_de'] or '')]
    au.sort(key=lambda r: (r['type'] != 'person', r['position'] if r['position'] is not None else 999))
    if au:
        r = au[0]
        if r['type'] == 'person':
            p = r['party_harmonized_de'] or r['party_de']
            return (party_group(p) or 'party unknown'), p
        nm = r['fullname'] or ''
        if re.search(r'kommission|commission|commissione|büro|bureau', nm, re.I): return 'committee', nm
        if re.search(r'fraktion|groupe|gruppo|partei|parti', nm, re.I): return party_group(nm), nm
        if re.search(r'bundesrat|regierungsrat|conseil d.état|consiglio di stato|gemeinderat|stadtrat|municipal', nm, re.I): return 'government', nm
        if re.search(r'kanton|canton|cantone', nm, re.I): return 'canton', nm
        return 'other group', nm
    t = a.get('type') or ''
    if re.search(r'regierungsgeschäft|bericht|vorlage|botschaft|geschäft des', t, re.I): return 'government', t
    if re.search(r'standesinitiative', t, re.I): return 'canton', t
    return 'unknown', t

# ---------------- canton / region
DE_C = {'ZH', 'LU', 'UR', 'SZ', 'OW', 'NW', 'GL', 'ZG', 'SO', 'BS', 'BL', 'SH', 'AR', 'AI', 'SG', 'AG', 'TG'}
FR_C = {'GE', 'VD', 'NE', 'JU'}; IT_C = {'TI'}; BI_C = {'BE', 'FR', 'VS', 'GR'}

def canton_of(body):
    if body == 'CHE': return 'federal'
    b = BODIES.get(body) or {}
    return b.get('canton') or body

def region_of(body):
    c = canton_of(body)
    if c == 'federal': return 'federal'
    if c in DE_C: return 'Deutschschweiz'
    if c in FR_C: return 'Romandie'
    if c in IT_C: return 'Svizzera italiana'
    if c in BI_C: return 'bilingual cantons (BE FR VS GR)'
    return 'other (' + str(c) + ')'
