"""S25 step 1: fresh Wayback CDX listings of APS process pages (all URL forms). Network: web.archive.org CDX only, via
ideation-1 polite.py (RFC 9309 robots, one UA, >=1.2 s/host, fail closed on 429/5xx). Resumable (skips existing files)."""
import json, os, sys, urllib.parse
sys.path.insert(0, "/Users/mi11ion/Desktop/hackapertus/bern/ideation/spikes/s2-oracles/scripts")
import polite  # noqa: E402
HERE = os.path.dirname(os.path.abspath(__file__))
polite.LOG = f"{HERE}/robots_log.jsonl"
# prefix queries; CDX canonicalises www. and scheme away, so each covers http/https/www variants
Q = {"de_prozesse": "anneepolitique.swiss/prozesse/", "fr_prozesse": "anneepolitique.swiss/fr/prozesse/",
     "de2_prozesse": "anneepolitique.swiss/de/prozesse/", "it_prozesse": "anneepolitique.swiss/it/prozesse/",
     "en_prozesse": "anneepolitique.swiss/en/prozesse/", "fr_processus": "anneepolitique.swiss/fr/processus/",
     "articles": "anneepolitique.swiss/articles/", "fr_articles": "anneepolitique.swiss/fr/articles/"}
for name, url in Q.items():
    out = f"{HERE}/cdx/{name}.json"
    if os.path.exists(out):
        continue
    q = urllib.parse.urlencode({"url": url, "matchType": "prefix", "output": "json",
                                "fl": "original,timestamp,statuscode,mimetype,length"})
    st, body = polite.get(f"https://web.archive.org/cdx/search/cdx?{q}", timeout=300, retries=3)
    if st != 200:
        print(name, "HTTP", st, body[:200]); continue
    rows = json.loads(body) if body.strip() else []
    json.dump(rows, open(out, "w"))
    print(name, len(rows), flush=True)
