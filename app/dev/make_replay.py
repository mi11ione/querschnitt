"""Neues Thema on the static site: a recorded real run, replayed in the browser with the live stream's event shapes.

Source (read-only): runs/adhoc/<slug>/{topic.json,decisions.jsonl,summary.json}, written by src/querschnitt/adhoc.py
during a real run against Public AI (no model calls here). Writes app/data/neu_replay.json (+ data-fixture/):
- `post`: what POST /adhoc answered (slug, topic, empty terms, period, estimate), after `post_lat` seconds (the recorded
  topic generation latency);
- `events`: the SSE log in the order the server emits it (`topic`, `terms`, `progress`, then `decision` + `progress` per
  affair at its recorded `t`, then `done` with the summary). Decisions keep only the fields the UI reads;
- provenance: model, build fingerprint, endpoint, the run's date (topic.json mtime, local time, unless --date) and totals.
Terms are the generated ones (deduplicated per language as verify_terms does); their corpus hit counts were not recorded.

Usage: python3 app/dev/make_replay.py [slug] [--date YYYY-MM-DD]"""
from __future__ import annotations

import datetime as dt
import json
import sys
from pathlib import Path

APP = Path(__file__).resolve().parents[1]
REPO = APP.parent
KEEP = ("id", "t", "p", "flag", "verified", "lane", "sample", "title", "body", "parl", "level", "lang", "date")


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    slug = args[0] if args else "klimawandel-stadt"
    run = REPO / "runs" / "adhoc" / slug
    tj = json.loads((run / "topic.json").read_text())
    sm = json.loads((run / "summary.json").read_text())
    rows = [json.loads(l) for l in (run / "decisions.jsonl").read_text().splitlines() if l.strip()]
    rows.sort(key=lambda r: r["t"])
    date = next((a.split("=", 1)[1] for a in sys.argv[1:] if a.startswith("--date=")), None)
    started = dt.datetime.fromtimestamp((run / "topic.json").stat().st_mtime).astimezone()
    date = date or started.date().isoformat()

    topic, gen = tj["topic"], tj.get("generation") or {}
    models = {r.get("model") for r in rows} | {gen.get("model")}
    builds = {r.get("build") for r in rows} | {gen.get("fp")}
    models.discard(None); builds.discard(None)
    assert len(models) == 1 and len(builds) == 1, (models, builds)  # one model, one build, or it is not one recording
    model, build = models.pop(), builds.pop()

    # the generated terms, deduplicated per language (verify_terms also drops terms without corpus hits; not recorded)
    raw = json.loads((sm.get("terms_generation") or {}).get("raw") or "{}").get("terms") or {}
    terms = {}
    for l in ("de", "fr", "it"):
        seen, kept = set(), []
        for x in raw.get(l) or []:
            x = str(x).strip("* ").strip()
            if x and x.lower() not in seen:
                seen.add(x.lower()); kept.append(x)
        terms[l] = kept

    period = sm.get("period") or tj.get("period")
    total = sm.get("total") or sm.get("in_period") or len(rows)
    ui_topic = {k: topic[k] for k in ("id", "names", "scope", "cutoff", "sentence", "lang") if k in topic}
    events = [dict(t=0.0, event="topic", data=dict(slug=slug, topic=ui_topic, period=period)),
              dict(t=0.0, event="terms", data=dict(terms=terms, error=None)),     # ready before the job existed (lat < post_lat)
              dict(t=0.0, event="progress", data=dict(read=0, flagged=0, total=total, seconds=0.0))]
    flagged = 0
    for k, r in enumerate(rows, 1):
        flagged += bool(r["flag"])
        events.append(dict(t=r["t"], event="decision", data={f: r.get(f) for f in KEEP}))
        events.append(dict(t=r["t"], event="progress", data=dict(read=k, flagged=flagged, total=total, seconds=r["t"])))
    usd = sum(r.get("usd") or 0 for r in rows) + (gen.get("usd") or 0) + ((sm.get("terms_generation") or {}).get("usd") or 0)
    summary = dict(read=sm["read"], flagged=sm["flagged"], seconds=sm["seconds"], in_period=sm.get("in_period"), total=total,
                   calls=sm.get("calls"), stop=sm.get("stop"), period=period, period_name=sm.get("period_name"), usd=round(usd, 6))
    assert summary["read"] == len(rows) and summary["flagged"] == flagged, (summary, len(rows), flagged)
    events.append(dict(t=sm["seconds"], event="done", data=dict(summary, done=True)))

    out = dict(kind="replay", slug=slug, recorded=date, recorded_at=started.isoformat(timespec="minutes"),
               sentence=topic.get("sentence"), lang=topic.get("lang"), model=model, build=build, fingerprint=build,
               build_short=build[-8:], endpoint=gen.get("endpoint"), post_lat=gen.get("lat") or gen.get("wall"),
               post=dict(slug=slug, topic=ui_topic, terms={l: [] for l in ("de", "fr", "it")}, terms_pending=True, period=period,
                         period_name=sm.get("period_name"), estimate=sm.get("estimate"), stream=f"/adhoc/{slug}/stream"),
               summary=summary, source=f"runs/adhoc/{slug}/", events=events)
    s = json.dumps(out, ensure_ascii=False, separators=(",", ":"))
    for d in (APP / "data", APP / "data-fixture"):
        (d / "neu_replay.json").write_text(s)
    print(f"{slug}: {len(rows)} decisions, {flagged} flagged, {sm['seconds']} s, {model} {build[-8:]}, {date}, {len(s)} bytes")


if __name__ == "__main__":
    main()
