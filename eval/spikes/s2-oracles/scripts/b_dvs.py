"""Task B: parse the DVS 'politische Geschäfte' page (fetched once) and match items to OPD affairs."""
import difflib
import gzip
import html as H
import json
import re
import sys
import urllib.parse

D = "/Users/mi11ion/Desktop/hackapertus/bern/ideation/spikes/s2-oracles/data"
AFF = "/Users/mi11ion/Desktop/hackapertus/spikes/data/raw/opd/affairs.ndjson.gz"
BODY = {"Kanton Bern": "BE", "Nationalrat": "CHE", "Ständerat": "CHE", "Bund": "CHE", "Kanton Zug": "ZG",
        "Kanton Obwalden": "OW", "Kanton Basel-Stadt": "BS", "Kanton Zürich": "ZH", "Kanton Thurgau": "TG",
        "Kanton Aargau": "AG", "Kanton Basel-Landschaft": "BL", "Kanton Luzern": "LU", "Kanton St. Gallen": "SG",
        "Kanton Solothurn": "SO", "Kanton Graubünden": "GR", "Kanton Wallis": "VS", "Kanton Freiburg": "FR"}

txt = open(f"{D}/raw_dvs/politische-geschaefte_de.html", encoding="utf-8").read()
items = []
for m in re.finditer(r'<a href="([^"]+)"[^>]*class="list-item[^"]*">(.*?)</a>', txt, re.S):
    link, inner = m.group(1), m.group(2)
    g = lambda cls: H.unescape(re.sub(r"<[^>]+>", " ", (re.search(rf'<div class="{cls}[^"]*">(.*?)</div>', inner, re.S) or [None, ""])[1]))
    date = " ".join(g("date").split())
    title = " ".join(g("title").split())
    desc = re.sub(r"\[https?://[^\]]*\]", "", " ".join(g("description small").split())).strip()
    dm = re.match(r"(?P<body>[^,]+), Geschäftsnummer: (?P<nr>\S+) (?P<type>.+?) von (?P<author>.+?)\. Status: (?P<status>.*)$", desc)
    it = {"date": date, "title": title, "description": desc, "link": H.unescape(link)}
    if dm:
        it.update({k: dm.group(k).strip() for k in ("body", "nr", "type", "author", "status")})
    else:
        it.update({"body": None, "nr": None, "type": None, "author": None, "status": None})
    it["body_key"] = BODY.get(it["body"]) if it["body"] else None
    items.append(it)

# OPD affairs index per body
want = {i["body_key"] for i in items if i["body_key"]}
by_body, by_url, by_id_all = {}, {}, {}
for line in gzip.open(AFF, "rt"):
    a = json.loads(line)
    by_id_all[a["id"]] = {k: a[k] for k in ("body_key", "number", "type_harmonized_en")}
    for k in ("url_external_de", "url_external_fr", "url_external_it"):
        if a.get(k):
            by_url[a[k].rstrip("/")] = a
    if a["body_key"] in want or not want:
        by_body.setdefault(a["body_key"], []).append(a)


def norm(s):
    return re.sub(r"\W+", " ", (s or "").lower()).strip()


def link_ids(u):
    p = urllib.parse.urlsplit(u)
    q = urllib.parse.parse_qs(p.query)
    ids = {v for vs in q.values() for v in vs}
    ids |= set(re.findall(r"[0-9a-fA-F]{32}|\d{5,}", p.path))
    return {i.lower() for i in ids}


nm = 0
for it in items:
    it["opd_affair_id"], it["match_by"] = None, None
    a = by_url.get(it["link"].rstrip("/"))
    if a:
        it["opd_affair_id"], it["match_by"] = a["id"], "url"
    cands = by_body.get(it["body_key"], []) if it["body_key"] else []
    if not it["opd_affair_id"] and it["nr"]:
        hits = [a for a in cands if (a["number"] or "").strip() == it["nr"]]
        if len(hits) == 1:
            it["opd_affair_id"], it["match_by"] = hits[0]["id"], "number"
    if not it["opd_affair_id"]:
        ids = link_ids(it["link"])
        hits = [a for a in cands if str(a.get("external_id") or "").lower() in ids]
        if len(hits) == 1:
            it["opd_affair_id"], it["match_by"] = hits[0]["id"], "external_id_in_link"
    if not it["opd_affair_id"] and cands:
        t = norm(it["title"])
        best = max(cands, key=lambda a: difflib.SequenceMatcher(None, t, norm(a["title_de"] or a["title_fr"])).quick_ratio())
        r = difflib.SequenceMatcher(None, t, norm(best["title_de"] or best["title_fr"])).ratio()
        it["best_title_ratio"] = round(r, 3)
        if r >= 0.85:
            it["opd_affair_id"], it["match_by"] = best["id"], f"title({r:.2f})"
    if it["opd_affair_id"]:
        nm += 1
        a = by_id_all.get(it["opd_affair_id"])
        if a:
            it["opd_body_key"], it["opd_number"], it["opd_type_en"] = a["body_key"], a["number"], a["type_harmonized_en"]
json.dump(items, open(f"{D}/dvs_items.json", "w"), ensure_ascii=False, indent=1)
print("items", len(items), "matched", nm)
for it in items:
    print(it["date"], it.get("opd_body_key"), it.get("opd_number"), it.get("opd_type_en"), it["body_key"], it["nr"], (it["type"] or "")[:20], "->", it["opd_affair_id"], it["match_by"],
          it.get("best_title_ratio"), "|", it["title"][:60])
