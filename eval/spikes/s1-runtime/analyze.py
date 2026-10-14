"""S1 analysis: reads raw/*.jsonl, writes analysis.json and prints tables. No network."""
import json, os, sys, math, collections, statistics as st
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from s1lib import wilson, NCH, CHAPTERS, OUT
RAW = os.path.join(OUT, 'raw')
rd = lambda p: [json.loads(l) for l in open(os.path.join(RAW, p))] if os.path.exists(os.path.join(RAW, p)) else []
S = json.load(open(os.path.join(OUT, 'sample.json')))
A = {}

def q(xs, p):
    xs = sorted(xs); return xs[min(len(xs) - 1, int(p * len(xs)))] if xs else None
def lat(rows):
    live = [r['rec'] for r in rows if r.get('rec') and not r['rec']['cached']]
    return dict(n_live=len(live), http_p50=q([x['http'] for x in live], .5), http_p95=q([x['http'] for x in live], .95),
                client_overhead_p50=q([x['wall'] - x['http'] for x in live], .5))
def tok(rows):
    rs = [r['rec'] for r in rows if r.get('rec')]
    return dict(pt_mean=round(st.mean(x['pt'] for x in rs), 1), ct_mean=round(st.mean(x['ct'] for x in rs), 2),
                usd_sum=round(sum(x['usd'] for x in rs), 5), n=len(rs))
def agree(pairs):
    k = sum(1 for a, b in pairs if a == b); n = len(pairs)
    return dict(k=k, n=n, rate=round(k / n, 3) if n else None, ci=wilson(k, n))

allrows = []
m1 = rd('m1.jsonl'); m1d = {r['sid']: r for r in m1}; allrows += m1
pts = [r['rec']['pt'] for r in m1]
A['input'] = dict(pt_min=min(pts), pt_p50=q(pts, .5), pt_mean=round(st.mean(pts), 1), pt_p95=q(pts, .95), pt_max=max(pts),
                  by_text={k: dict(n=len(v), pt_p50=q(v, .5)) for k, v in
                           (('with_text', [r['rec']['pt'] for r in m1 if r['has_text']]),
                            ('title_only', [r['rec']['pt'] for r in m1 if not r['has_text']]))})
A['m1'] = dict(tok(m1), **lat(m1), code_mass_min=min(r['code_mass'] for r in m1),
               gen_equals_top=sum(1 for r in m1 if r['gen'] and r['gen'].strip() in r['codes'] and
                                  max(r['codes'], key=r['codes'].get) == r['gen'].strip()),
               top_dist=collections.Counter(r['top'] for r in m1).most_common(),
               top1_prob_median=round(q([math.exp(max(r['codes'].values())) for r in m1], .5), 3),
               top1_prob_lt_0_5=sum(1 for r in m1 if math.exp(max(r['codes'].values())) < 0.5),
               none_option=sum(1 for r in m1 if r['top'] == 24))

# ---- M4 permutation + contextual calibration
m4 = rd('m4p.jsonl'); allrows += m4
pri = rd('prior.jsonl'); allrows += pri
P = collections.defaultdict(dict)  # (lang, pname) -> chapter -> lp
for r in pri: P[(r['lang'], r['pname'])][r['chapter']] = r['lp']
def norm(d):
    m = max(d.values()); z = m + math.log(sum(math.exp(v - m) for v in d.values()))
    return {k: v - z for k, v in d.items()}
for k in P: P[k] = norm(P[k])
def calib(row, pname):
    pr = P[(row['lang'], pname)]
    ch = {int(c): l - pr[int(c)] for c, l in row['chap'].items()}   # only chapters observed in top-20
    return max(ch, key=ch.get)
pairs_raw, pairs_cal, cal_change_id, cal_change_pm = [], [], 0, 0
for r in m4:
    b = m1d[r['sid']]
    pairs_raw.append((b['top'], r['top']))
    ci, cp = calib(b, 'id'), calib(r, 'perm')
    pairs_cal.append((ci, cp)); cal_change_id += ci != b['top']; cal_change_pm += cp != r['top']
# prior shape: content-free top code and entropy
prior_info = {}
for (L, pn), d in P.items():
    top = max(d, key=d.get)
    prior_info[f'{L}-{pn}'] = dict(top_chapter=CHAPTERS['de'][top][:30], top_p=round(math.exp(d[top]), 3),
                                   entropy_bits=round(-sum(math.exp(v) * v for v in d.values()) / math.log(2), 2))
# position: share of top-1 in first code slot / letter A for identity vs perm
slotA_id = sum(1 for r in m1 if max(r['codes'], key=r['codes'].get) == 'A')
slotA_pm = sum(1 for r in m4 if max(r['codes'], key=r['codes'].get) == 'A')
A['m4'] = dict(tok(m4), **lat(m4), agree_raw=agree(pairs_raw), agree_calibrated=agree(pairs_cal),
               calibration_changes_top1_identity=cal_change_id, calibration_changes_top1_perm=cal_change_pm,
               prior=prior_info, prior_requests=len(pri), slotA_identity=f'{slotA_id}/{len(m1)}', slotA_perm=f'{slotA_pm}/{len(m4)}',
               top1_agree_by_conf=None)
# agreement split by M1 confidence
hi = [(m1d[r['sid']]['top'], r['top']) for r in m4 if math.exp(max(m1d[r['sid']]['codes'].values())) >= 0.9]
lo = [(m1d[r['sid']]['top'], r['top']) for r in m4 if math.exp(max(m1d[r['sid']]['codes'].values())) < 0.9]
A['m4']['top1_agree_by_conf'] = dict(m1_p_ge_0_9=agree(hi), m1_p_lt_0_9=agree(lo))

# ---- M2 exact per-label
m2 = rd('m2.jsonl'); allrows += m2
by = collections.defaultdict(dict); ntok = collections.defaultdict(dict)
for r in m2: by[r['sid']][r['c']] = r['lp']; ntok[r['sid']][r['c']] = r['ntok']
full = [s for s in by if len(by[s]) == NCH]
p_sum = [(m1d[s]['top'], max(by[s], key=by[s].get)) for s in full]
p_mean = [(m1d[s]['top'], max(by[s], key=lambda c: by[s][c] / ntok[s][c])) for s in full]
p_first_in_m1top3 = [1 for s in full if max(by[s], key=by[s].get) in [int(c) for c in sorted(m1d[s]['chap'], key=m1d[s]['chap'].get, reverse=True)[:3]]]
A['m2'] = dict(tok(m2), **lat(m2), affairs=len(full), requests_per_affair=NCH,
               label_tokens_mean=round(st.mean(r['ntok'] for r in m2), 2), straddles=sum(r['straddle'] for r in m2),
               agree_sum_vs_m1=agree(p_sum), agree_meanpertoken_vs_m1=agree(p_mean),
               m2top_in_m1top3=f'{len(p_first_in_m1top3)}/{len(full)}')

# ---- M3 batched
m3 = rd('m3.jsonl'); allrows += m3
pairs = []
for r in m3:
    for k, v in r['per'].items():
        pairs.append((m1d[v['sid']]['top'], v['top']))
n_items = sum(r['n_items'] for r in m3)
A['m3'] = dict(tok(m3), **lat(m3), requests=len(m3), items=n_items, parsed=sum(r['parsed'] for r in m3),
               pt_per_affair=round(sum(r['rec']['pt'] for r in m3) / n_items, 1),
               ct_per_affair=round(sum(r['rec']['ct'] for r in m3) / n_items, 2),
               http_per_affair=round(sum(r['rec']['http'] for r in m3) / n_items, 3),
               usd_per_affair=sum(r['rec']['usd'] for r in m3) / n_items,
               agree_vs_m1=agree(pairs))

hi3 = []; pos = collections.defaultdict(list)
for r in m3:
    for k, v in r['per'].items():
        b = m1d[v['sid']]; pos['first_half' if int(k) <= r['n_items'] // 2 else 'second_half'].append((b['top'], v['top']))
        if math.exp(max(b['codes'].values())) >= 0.9: hi3.append((b['top'], v['top']))
A['m3']['agree_vs_m1_when_m1_p_ge_0_9'] = agree(hi3)
A['m3']['agree_by_batch_position'] = {k: agree(v) for k, v in pos.items()}
A['m3']['agree_vs_m4perm'] = agree([(r['top'], next(v['top'] for x in m3 for kk, v in x['per'].items() if v['sid'] == r['sid'])) for r in m4])
A['m1']['pt_mean_with_text'] = round(st.mean(r['rec']['pt'] for r in m1 if r['has_text']), 1)
A['m1']['pt_mean_title_only'] = round(st.mean(r['rec']['pt'] for r in m1 if not r['has_text']), 1)
A['l2_pt_mean_with_text'] = round(st.mean(r['rec']['pt'] for r in rd('l2.jsonl') if S[r['sid']]['text']), 1)
A['l2_pt_mean_title_only'] = round(st.mean(r['rec']['pt'] for r in rd('l2.jsonl') if not S[r['sid']]['text']), 1)
A['m2']['disagreements'] = [dict(sid=s, m1=CHAPTERS['de'][m1d[s]['top']], m2=CHAPTERS['de'][max(by[s], key=by[s].get)], title=S[s]['title'][:70]) for s in full if m1d[s]['top'] != max(by[s], key=by[s].get)]
# prior over the 24 substantive chapters only (content-free)
for (L, pn), d in P.items():
    sub = {k: v for k, v in d.items() if k < 24}; t = max(sub, key=sub.get)
    A['m4']['prior'][f'{L}-{pn}']['top_substantive'] = CHAPTERS['de'][t]
A['m4']['agree_calibrated_by_conf'] = None
# 429 location
A['n429_by_phase'] = collections.Counter(r['key'].split('-')[0] for r in m1 + m4 + pri + m2 + m3 + rd('l2.jsonl') for s_ in r['rec']['statuses'] if s_ == 429)

# ---- L2
l2 = rd('l2.jsonl'); allrows += l2
A['l2'] = dict(tok(l2), **lat(l2), nsub_mean=round(st.mean(r['nsub'] for r in l2), 1),
               code_mass_min=min(r['code_mass'] for r in l2),
               top1_prob_median=round(q([math.exp(max(r['codes'].values())) for r in l2 if r['codes']], .5), 3))

# ---- throughput
tp = rd('tp.jsonl'); allrows += tp
runs = collections.defaultdict(list)
for r in tp: runs[r['run']].append(r)
T = []
for run, rs in runs.items():
    c = int(run.split('-')[0][1:]); ok = [r for r in rs if r['rec']]
    t0 = min(r['rec']['t_start'] for r in ok); t1 = max(r['rec']['t_start'] + r['rec']['wall'] for r in ok)
    h0 = min(r['rec']['t_http0'] for r in ok); h1 = max(r['rec']['t_http1'] for r in ok)
    http = [r['rec']['http'] for r in ok]
    st_all = collections.Counter(s for r in ok for s in r['rec']['statuses'])
    busy = sum(http)
    T.append(dict(run=run, c=c, n=len(rs), errors=sum(1 for r in rs if r['err']), wall_s=round(t1 - t0, 1),
                  rps_end_to_end=round(len(ok) / (t1 - t0), 2), http_p50=q(http, .5), http_p95=q(http, .95),
                  http_mean=round(st.mean(http), 3), mean_in_flight=round(busy / (h1 - h0), 2),
                  client_overhead_p50=q([r['rec']['wall'] - r['rec']['http'] for r in ok], .5),
                  statuses=dict(st_all), n429=st_all.get(429, 0), pt_mean=round(st.mean(r['rec']['pt'] for r in ok), 1),
                  fps=list({r['rec']['fp'] for r in ok})))
A['throughput'] = sorted(T, key=lambda x: (x['c'], x['run']))

# ---- builds across everything
fps = collections.Counter(); models = collections.Counter(); statuses = collections.Counter()
for r in allrows:
    rec = r.get('rec')
    if rec: fps[rec['fp']] += 1; models[rec['model']] += 1; statuses.update(rec['statuses'])
A['builds'] = dict(fingerprints=dict(fps), models=dict(models), http_statuses=dict(statuses),
                   cached_rows=sum(1 for r in allrows if r.get('rec') and r['rec']['cached']))
json.dump(A, open(os.path.join(OUT, 'analysis.json'), 'w'), indent=1, ensure_ascii=False)
print(json.dumps(A, indent=1, ensure_ascii=False))
