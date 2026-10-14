"""S10 step 4: weekly OPD affair volume for BE, FR, VS, 2025-01-01 .. 2026-10-04 (last full ISO week before the 6 Oct 2026
export; 92 weeks incl. zero weeks), by begin_date. Two counts: all affairs, and the S10 frame (both titles non-empty, de != fr,
no personnel-regex hit). No network, no model calls. Usage: python3 -I volume.py -> ../volume.json"""
import gzip, json, os, sys, datetime as dt, statistics as st, collections
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sample import EXCL, clean, OPD, CANTONS

OUT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
START, END = dt.date(2024, 12, 30), dt.date(2026, 10, 4)   # Monday of ISO week 2025-W01 .. Sunday of 2026-W40


def pct(xs, q):
    xs = sorted(xs); k = (len(xs) - 1) * q; f = int(k); c = min(f + 1, len(xs) - 1)
    return xs[f] + (xs[c] - xs[f]) * (k - f)


def main():
    weeks = [START + dt.timedelta(days=7 * i) for i in range((END - START).days // 7 + 1)]
    cnt = {(kind, bk): collections.Counter() for kind in ('all', 'frame') for bk in CANTONS + ('ALL3',)}
    for l in gzip.open(f'{OPD}/affairs.ndjson.gz', 'rt'):
        a = json.loads(l); bk = a.get('body_key'); d = (a.get('begin_date') or '')[:10]
        if bk not in CANTONS or not d or d < '2025-01-01': continue
        day = dt.date.fromisoformat(d)
        if day > END: continue
        wk = day - dt.timedelta(days=day.weekday())
        td, tf = clean(a.get('title_de')), clean(a.get('title_fr'))
        frame = bool(td and tf and td != tf and not EXCL.search(td) and not EXCL.search(tf))
        for b in (bk, 'ALL3'):
            cnt[('all', b)][wk] += 1
            if frame: cnt[('frame', b)][wk] += 1
    out = dict(window=f'{START}..{END}', n_weeks=len(weeks), note='begin_date; zero weeks included', series={})
    for (kind, b), c in cnt.items():
        xs = [c[w] for w in weeks]
        out['series'][f'{kind}:{b}'] = dict(total=sum(xs), median=st.median(xs), mean=round(st.mean(xs), 2), p75=pct(xs, .75),
                                            p90=pct(xs, .9), max=max(xs), zero_weeks=sum(x == 0 for x in xs),
                                            median_nonzero=st.median([x for x in xs if x]) if any(xs) else 0)
    json.dump(out, open(f'{OUT}/volume.json', 'w'), indent=1)
    for k, v in out['series'].items(): print(f'{k:12s}', v)


if __name__ == '__main__':
    main()
