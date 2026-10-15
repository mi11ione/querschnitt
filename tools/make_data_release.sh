#!/bin/sh
# Build the data release asset `querschnitt-data.tar.gz` that `make data` unpacks at the repo root:
#   app/data/...              the static export (querschnitt export --topics-file), as is
#   data/inputs.jsonl.gz      slim inputs: exactly the export's affairs (affairs.json ids = the slice), text cut to 1,500
#   data/topics.jsonl.gz      the export's topic rows (CONTRACT §1)
# It only builds the file; publishing it is a separate, manual step.
#   tools/make_data_release.sh                      (defaults below; override with APP_DATA, INPUTS, OUT)
set -eu
cd "$(dirname "$0")/.."
APP_DATA=${APP_DATA:-app/data}
INPUTS=${INPUTS:-${QS_INPUTS:-../data/inputs.jsonl.gz}}
OUT=${OUT:-dist/querschnitt-data.tar.gz}
PY=${PY:-$( [ -x .venv/bin/python ] && echo .venv/bin/python || echo python3 )}
for f in "$APP_DATA/affairs.json" "$APP_DATA/meta.json" "$APP_DATA/topics.jsonl.gz" "$INPUTS"; do
  [ -f "$f" ] || { echo "missing $f (run: querschnitt export --topics-file)" >&2; exit 2; }
done
STAGE=$(mktemp -d "${TMPDIR:-/tmp}/qsdata.XXXXXX")
trap 'rm -rf "$STAGE"' EXIT
mkdir -p "$STAGE/app" "$STAGE/data" "$(dirname "$OUT")"
cp -R "$APP_DATA" "$STAGE/app/data"
cp "$APP_DATA/topics.jsonl.gz" "$STAGE/data/topics.jsonl.gz"
"$PY" - "$APP_DATA" "$INPUTS" "$STAGE/data/inputs.jsonl.gz" <<'PYEOF'
import gzip, json, sys
app, src, dst = sys.argv[1:4]
ids = set(json.load(open(f"{app}/affairs.json"))["cols"]["id"])
meta = json.load(open(f"{app}/meta.json"))
n = 0
with gzip.open(src, "rt") as f, gzip.open(dst, "wt") as o:
    for line in f:
        x = json.loads(line)
        if x["id"] in ids:
            x["text"] = (x.get("text") or "")[:1500]
            o.write(json.dumps(x, ensure_ascii=False) + "\n"); n += 1
cols = json.load(open(f"{app}/affairs.json"))["cols"]
ch = {i for i, c in zip(cols["id"], cols["ch"]) if c is not None}
aps = set()
with gzip.open(f"{app}/topics.jsonl.gz", "rt") as f:
    for line in f:
        r = json.loads(line)
        if r["scheme"] == "aps" and r["level"] == 1:
            aps.add(r["affair_id"])
if ch != aps:
    sys.exit(f"topics.jsonl.gz is not from the export that wrote affairs.json ({len(ch - aps)} chapters without rows, "
             f"{len(aps - ch)} rows without a chapter); rerun: querschnitt export --topics-file")
if n != len(ids) or n != meta["affairs"] + (meta.get("extra") or {}).get("affairs", 0):   # slice + extra ranges (--extra)
    sys.exit(f"inputs hold {n} of the export's {len(ids)} affairs (meta: {meta['affairs']}); rebuild the export from these inputs")
print(f"affairs {n} (= meta.json) · build {meta.get('build_short') or meta.get('build')} · generated {meta.get('generated_at')}")
PYEOF
COPYFILE_DISABLE=1 tar -C "$STAGE" -czf "$OUT" app data          # no macOS ._ metadata files
SHA=$(shasum -a 256 "$OUT" 2>/dev/null | cut -d' ' -f1 || sha256sum "$OUT" | cut -d' ' -f1)
echo "$OUT · $(du -h "$OUT" | cut -f1) · sha256 $SHA"
