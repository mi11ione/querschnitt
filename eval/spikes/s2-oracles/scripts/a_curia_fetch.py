"""Task A: fetch Curia Vista Business rows (DE/FR/IT, submitted >= 2000-01-01) in half-year windows + Tags entity."""
import gzip
import json
import os
import sys
import time
import urllib.parse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import polite  # noqa: E402

D = "/Users/mi11ion/Desktop/hackapertus/bern/ideation/spikes/s2-oracles/data"
B = "https://ws.parlament.ch/odata.svc/"
SEL = "ID,BusinessShortNumber,Language,Title,Tags,TagNames,BusinessTypeAbbreviation,SubmissionDate,ResponsibleDepartmentAbbreviation"


def windows():
    for y in range(2000, 2027):
        for a, b in (("01-01", "04-01"), ("04-01", "07-01"), ("07-01", "10-01"), ("10-01", None)):
            end = f"{y}-{b}" if b else f"{y + 1}-01-01"
            yield f"{y}-{a}", end


def _one(lang, a, b):
    f = (f"Language eq '{lang}' and SubmissionDate ge datetime'{a}T00:00:00' "
         f"and SubmissionDate lt datetime'{b}T00:00:00'")
    url = B + "Business?$format=json&$orderby=ID&$select=" + SEL + "&$filter=" + urllib.parse.quote(f)
    rows = []
    while url:
        d = polite.get_json(url, timeout=180)["d"]
        res = d["results"] if isinstance(d, dict) else d
        for r in res:
            r.pop("__metadata", None)
            rows.append(r)
        url = d.get("__next") if isinstance(d, dict) else None
    return rows


def _months(a, b):
    import datetime as dt
    x = dt.date.fromisoformat(a)
    e = dt.date.fromisoformat(b)
    while x < e:
        nx = dt.date(x.year + (x.month == 12), x.month % 12 + 1, 1)
        yield x.isoformat(), min(nx, e).isoformat()
        x = nx


def fetch_window(lang, a, b):
    for attempt in range(2):
        try:
            return _one(lang, a, b)
        except (ValueError, RuntimeError) as e:  # empty/truncated body or non-200
            print("window error", lang, a, b, repr(e)[:200], flush=True)
            time.sleep(15)
    rows = []
    for ma, mb in _months(a, b):
        for attempt in range(3):
            try:
                rows += _one(lang, ma, mb)
                break
            except (ValueError, RuntimeError) as e:
                print("month error", lang, ma, mb, repr(e)[:200], flush=True)
                time.sleep(20 * (attempt + 1))
        else:
            raise RuntimeError(f"month {ma} failed 3x")
    return rows


def fetch_lang(lang):
    out = f"{D}/curia_business_{lang.lower()}.jsonl.gz"
    done_path = out + ".windows"
    done = set(open(done_path).read().split()) if os.path.exists(done_path) else set()
    with gzip.open(out, "at") as fo, open(done_path, "a") as fd:
        for a, b in windows():
            key = f"{a}_{b}"
            if key in done:
                continue
            rows = fetch_window(lang, a, b)
            n = 0
            for r in rows:
                fo.write(json.dumps(r, ensure_ascii=False) + "\n")
                n += 1
            fo.flush()
            fd.write(key + "\n")
            fd.flush()
            print(lang, key, n, flush=True)


def main():
    tags = {}
    for lang in ("DE", "FR", "IT"):
        d = polite.get_json(B + f"Tags?$format=json&$filter=Language%20eq%20'{lang}'")["d"]
        res = d["results"] if isinstance(d, dict) else d
        for r in res:
            r.pop("__metadata", None)
        tags[lang] = res
    json.dump(tags, open(f"{D}/curia_tags.json", "w"), ensure_ascii=False, indent=1)
    print("tags", {k: len(v) for k, v in tags.items()}, flush=True)
    for lang in sys.argv[1:] or ("DE", "FR", "IT"):
        fetch_lang(lang)
    print("DONE", time.strftime("%H:%M:%S"), flush=True)


if __name__ == "__main__":
    main()
