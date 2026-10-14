"""Measured cost and wall time of the corpus run (list price, Public AI): per step, per affair, per 1,000 affairs, and the
projection for all OPD affairs. Source: the run's step rows (usd and prompt tokens per request) and ledger timestamps.
Rows seeded from S8 carry no usd; yes/no cost uses the mean of the rows that do."""
import collections, json, statistics, time
from pathlib import Path
HERE = Path(__file__).resolve().parent; ROOT = HERE.parents[1]
rows = [json.loads(l) for p in (ROOT / "runs/main/dd237840-20261014").glob("*.jsonl") for l in open(p)]
c = collections.Counter(); usd = collections.defaultdict(list); aff = collections.defaultdict(set)
for r in rows:
    st = r["step"].split(":")[0]; c[st] += 1; aff[st].add(r["aid"])
    if r["meta"].get("usd") is not None: usd[st].append(r["meta"]["usd"])
mean = {k: statistics.mean(v) for k, v in usd.items()}
n_aff = len(aff["ch1"])
per_aff = {k: c[k] / n_aff for k in c}          # requests per affair (identical prompts are sent once)
usd_aff = sum(per_aff[k] * mean[k] for k in c)
L = [json.loads(l) for l in open(ROOT / "runs/main/ledger.jsonl")]
ts = sorted(r["ts"] for r in L); hours = (ts[-1] - ts[0]) / 3600
rate = len(L) / (ts[-1] - ts[0])                  # this job's own sustained requests/s on the shared key
chap = per_aff["ch1"] + per_aff["ch2"] + per_aff["sub"]
R = dict(generated=time.strftime("%Y-%m-%dT%H:%M:%S%z"), requests=dict(c), affairs_with_chapter_reading=n_aff,
         requests_per_affair={k: round(v, 3) for k, v in per_aff.items()}, usd_per_request_mean={k: round(v, 7) for k, v in mean.items()},
         usd_per_1000_affairs_all_steps=round(1000 * usd_aff, 3), usd_per_1000_affairs_chapter_only=round(1000 * sum(per_aff[k] * mean[k] for k in ("ch1", "ch2", "sub")), 3),
         wall_hours_so_far=round(hours, 2), job_rate_req_per_s=round(rate, 3),
         minutes_per_1000_affairs_all_steps_at_job_rate=round(1000 * sum(per_aff.values()) / rate / 60, 1),
         projection_all_326123_affairs_chapter_step=dict(requests=round(326123 * chap), usd=round(326123 * sum(per_aff[k] * mean[k] for k in ("ch1", "ch2", "sub")), 2),
                                                         hours_at_job_rate=round(326123 * chap / rate / 3600, 1), note="projection, not run"))
(HERE / "results.json").write_text(json.dumps(R, indent=1)); print(json.dumps(R, indent=1))
