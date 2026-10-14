"""S7 scoring (no LLM calls). Reads raw/{dvs,aps}.jsonl (Qwen), the S4/S6 Claude annotations and keys.
Writes ../score.json and prints tables. Usage: python3 -I score.py"""
import json, re, sys, collections, pathlib
SP = pathlib.Path('/Users/mi11ion/Desktop/hackapertus/bern/ideation/spikes')
S4, S6, S7 = SP / 's4-blindcheck', SP / 's6-cantonal', SP / 's7-crossfamily'
sys.path.insert(0, str(S6 / 'scripts'))
from score import read_ann as read_aps_ann, kappa, wilson, acc     # reuse S6 logic (code normalisation, kappa, Wilson)
sys.path.insert(0, str(S7 / 'scripts'))
from run import dvs_items

def qwen(name):
    R = [json.loads(l) for l in open(S7 / f'raw/{name}.jsonl')]
    bad = [r['id'] for r in R if not r['model_ok']]
    fail = [r['id'] for r in R if r['parse_fail']]
    return {r['id']: r['answer'] for r in R if r['model_ok'] and not r['parse_fail']}, dict(
        n=len(R), served_model_mismatch=bad, parse_fail=fail, reasked=sum(r['reasked'] for r in R))

out = {}
# ------------------------------------------------------------------ set 1: DVS digitalisation
def read_yn(p):
    return {a: b for a, b, *_ in (l.rstrip('\n').split('\t') + [''] for l in open(p) if l.strip())}
A, B = read_yn(S4 / 'ann_A.tsv'), read_yn(S4 / 'ann_B.tsv')
key = {json.loads(l)['pid']: json.loads(l) for l in open(S4 / 'key.jsonl')}
Q, qmeta = qwen('dvs')
kwd = json.load(open(S4 / 'keyword_baseline.json'))
KW = re.compile(kwd['kw'], re.I)
text = {}
for iid, t in dvs_items():                       # keyword input = title + long title (fields after id|parl|type)
    text[iid] = ' | '.join(t.split(' | ')[3:])
ids = sorted(set(A) & set(B) & set(Q) & set(key))
y = lambda v: v == 'Y'                            # '?' counts as not-Y (as in S4)
ap = {i for i in ids if key[i]['p_yes'] >= 0.5}
kw = {i for i in ids if KW.search(text[i])}
def bin_agree(X, Y):
    xs, ys = [y(X[i]) for i in ids], [y(Y[i]) for i in ids]
    return dict(raw=round(sum(a == b for a, b in zip(xs, ys)) / len(ids), 3), k=sum(a == b for a, b in zip(xs, ys)),
                kappa=kappa(xs, ys), n=len(ids))
golds = {
    'Claude both Y (S4 gold)': {i for i in ids if y(A[i]) and y(B[i])},
    'Claude either Y': {i for i in ids if y(A[i]) or y(B[i])},
    'Majority of 3 (A,B,Qwen)': {i for i in ids if y(A[i]) + y(B[i]) + y(Q[i]) >= 2},
    'All 3 Y': {i for i in ids if y(A[i]) and y(B[i]) and y(Q[i])},
    'Qwen alone': {i for i in ids if y(Q[i])},
}
def pr(flags, gold):
    tp = len(flags & gold)
    return dict(flags=len(flags), gold=len(gold), tp=tp, precision=round(tp / len(flags), 3) if flags else None,
                recall=round(tp / len(gold), 3) if gold else None, p_ci=wilson(tp, len(flags)), r_ci=wilson(tp, len(gold)))
s1 = dict(qwen=qmeta, n=len(ids), qwen_Y=sum(y(Q[i]) for i in ids), A_Y=sum(y(A[i]) for i in ids), B_Y=sum(y(B[i]) for i in ids),
          agree=dict(Q_vs_A=bin_agree(Q, A), Q_vs_B=bin_agree(Q, B), A_vs_B=bin_agree(A, B)),
          kw_check=dict(flags=len(kw), tp_vs_both=len(kw & golds['Claude both Y (S4 gold)']), stored=dict(flags=kwd['flags'], tp=kwd['tp'])),
          gold={g: dict(apertus=pr(ap, G), keyword=pr(kw, G)) for g, G in golds.items()},
          qwen_only_Y=sorted(i for i in ids if y(Q[i]) and not (y(A[i]) or y(B[i]))),
          qwen_missed_both=sorted(i for i in ids if not y(Q[i]) and y(A[i]) and y(B[i])),
          maj_vs_both_changes=sorted(golds['Majority of 3 (A,B,Qwen)'] ^ golds['Claude both Y (S4 gold)']))
out['dvs'] = s1
print('## Set 1 DVS', json.dumps({k: v for k, v in s1.items() if k != 'gold'}, default=list))
for g, d in s1['gold'].items():
    print(f"{g:28s} gold {d['apertus']['gold']:3d} | Apertus P {d['apertus']['precision']} R {d['apertus']['recall']} (tp {d['apertus']['tp']}/{d['apertus']['flags']}) | KW P {d['keyword']['precision']} R {d['keyword']['recall']} (tp {d['keyword']['tp']}/{d['keyword']['flags']})")

# ------------------------------------------------------------------ set 2: cantonal APS chapters
A2, B2 = read_aps_ann(S6 / 'ann_A.tsv'), read_aps_ann(S6 / 'ann_B.tsv')
key2 = {json.loads(l)['oid']: json.loads(l) for l in open(S6 / 'key.jsonl')}
Q2, qmeta2 = qwen('aps')
ids2 = sorted(set(A2) & set(B2) & set(Q2) & set(key2))
rows = []
for o in ids2:
    k = key2[o]; a1, b1, q1 = A2[o][0], B2[o][0], Q2[o][0]
    c = collections.Counter([a1, b1, q1]).most_common(1)[0]
    rows.append(dict(id=o, level=k['level'], ap=k['apertus_final'], a1=a1, b1=b1, q1=q1,
                     sa={x for x in A2[o] if x}, sb={x for x in B2[o] if x}, sq={x for x in Q2[o] if x},
                     strict=a1 if a1 == b1 else None, maj=c[0] if c[1] >= 2 else None))
for r in rows: r['lenient'] = (r['sa'] & r['sb']) or None
def agr(rs, f1, f2):
    return dict(n=len(rs), raw=round(sum(f1(r) == f2(r) for r in rs) / len(rs), 3) if rs else None,
                kappa=kappa([f1(r) for r in rs], [f2(r) for r in rs]))
strict = [r for r in rows if r['strict']]
s2 = dict(qwen=qmeta2, n=len(rows),
          agree=dict(Q_vs_A=agr(rows, lambda r: r['q1'], lambda r: r['a1']), Q_vs_B=agr(rows, lambda r: r['q1'], lambda r: r['b1']),
                     A_vs_B=agr(rows, lambda r: r['a1'], lambda r: r['b1']),
                     Q_vs_Claude_strict=agr(strict, lambda r: r['q1'], lambda r: r['strict']),
                     Q_in_Claude_lenient=acc([r for r in rows if r['lenient']], lambda r: r['q1'] in r['lenient']),
                     Q_vs_Apertus=agr(rows, lambda r: r['q1'], lambda r: r['ap'])),
          gold_sizes=dict(strict=len(strict), lenient=sum(1 for r in rows if r['lenient']), majority3=sum(1 for r in rows if r['maj']),
                          all3=sum(1 for r in rows if r['a1'] == r['b1'] == r['q1'])))
variants = {
    '(a) Claude strict (A1=B1)': (lambda r: r['strict'], lambda r: r['ap'] == r['strict']),
    '(a\') Claude lenient (sets overlap)': (lambda r: r['lenient'], lambda r: r['ap'] in r['lenient']),
    '(b) Qwen first choice': (lambda r: True, lambda r: r['ap'] == r['q1']),
    '(b\') Qwen set (1st or 2nd)': (lambda r: True, lambda r: r['ap'] in r['sq']),
    '(c) majority of 3 first choices': (lambda r: r['maj'], lambda r: r['ap'] == r['maj']),
    '(d) all 3 agree': (lambda r: r['a1'] == r['b1'] == r['q1'], lambda r: r['ap'] == r['a1']),
}
s2['apertus'] = {}
for vn, (has, hit) in variants.items():
    s2['apertus'][vn] = {lv: acc([r for r in rows if has(r) and (lv == 'all' or r['level'] == lv)], hit)
                         for lv in ('all', 'cantonal', 'communal')}
s2['qwen_vs_strict_confusions'] = [[g, q, n] for (g, q), n in collections.Counter(
    (r['strict'], r['q1']) for r in strict if r['q1'] != r['strict']).most_common(8)]
out['aps'] = s2
print('\n## Set 2 APS', json.dumps({k: v for k, v in s2.items() if k != 'apertus'}, default=list))
for vn, d in s2['apertus'].items():
    print(f"{vn:36s} " + ' | '.join(f"{lv} {d[lv]['acc']} ({d[lv]['k']}/{d[lv]['n']}) {d[lv]['ci']}" for lv in d))
json.dump(out, open(S7 / 'score.json', 'w'), indent=1, default=list)
