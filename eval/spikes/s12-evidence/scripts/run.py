"""S12 evidence support: Apertus picks one numbered sentence as evidence for its D1 chapter; code checks exact substring.
Sample: 120 S9 items with non-empty DE text and a D1 prediction, random.Random(20261014).sample over oid-sorted list.
D1 = S9 analyze.py d1_like(o, PA, PA) (copied verbatim below; analyze.py cannot be imported: it runs and writes S9 results).
Call: pai.chat, user + prefill '{"satz": "', continue_final_message=True, add_generation_prompt=False, max_tokens=3,
logprobs=True, top_logprobs=20, temperature 0. Resumable (raw/s12.jsonl keyed by oid), 3 workers. Stops on off-build fingerprint.
Then builds the blind packet (packet/) and key.jsonl (outside packet)."""
import json, os, random, re, sys, threading
from concurrent.futures import ThreadPoolExecutor
HERE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, "/Users/mi11ion/Desktop/hackapertus/bern/ideation2/spikes/s9-aps/scripts")
from s9lib import DATA as S9DATA, RAW as S9RAW, CH_DE, BUILD, MODEL, load, pai  # noqa: E402

TAG, CAP, SEED, N = "bern2-s12-evidence", 0.50, 20261014, 120
RAWF = f"{HERE}/raw/s12.jsonl"
PREFILL = '{"satz": "'


def order(p): return sorted(range(len(p)), key=lambda i: -p[i])


# ---- S9 analyze.py verbatim (joint_scores, d1_like) with raw passed in
raw = {ph: load(f"{S9RAW}/{ph}.jsonl") for ph in ("d0a", "d0b", "d1")}
def joint_scores(o, prior):
    r = raw['d1'][o]; sc = {}
    for i, (c, s) in enumerate(r['opts']):
        sc[(c, s)] = r['p'][i] * prior[c]
    return sc

def d1_like(o, prior, rank_rest):
    sc = joint_scores(o, prior); tot = sum(sc.values()) or 1
    best = max(sc, key=sc.get)
    chbest = {}
    for (c, s), v in sc.items(): chbest[c] = max(chbest.get(c, 0), v)
    rk = sorted(chbest, key=lambda c: -chbest[c]); rk += [c for c in order(rank_rest) if c not in rk]
    conf = sum(v for (c, s), v in sc.items() if c == best[0]) / tot
    subs_rank = sorted(sc, key=lambda k: -sc[k])
    return dict(ch=best[0], rank=rk, conf=conf, sub=best, subs=subs_rank)


def d1(o):
    a, b = raw['d0a'][o]['p'], raw['d0b'][o]['p']
    PA = [(x + y) / 2 for x, y in zip(a, b)]
    return d1_like(o, PA, PA)


# ---- input text + sentences
def de_of(it):
    d = it['de']
    if isinstance(d, str):
        import ast; d = ast.literal_eval(d)
    return d


def input_parts(d):
    """title, long title (if different, first 400 chars, as s1lib.affair_block), first 1,500 chars of text."""
    parts = [d['title']]
    if d.get('title_long') and d['title_long'] != d['title']:
        parts.append(d['title_long'][:400])
    parts.append(d['text'][:1500])
    return parts


SPLIT = re.compile(r"(?<=[.!?;])\s+")
def sentences(d):
    out = []
    for part in input_parts(d):
        for s in SPLIT.split(part):
            s = s.strip()
            if len(s) >= 25: out.append(s)
    return out[:40]


def prompt(sents, chname):
    num = "\n".join(f"{i}. {s}" for i, s in enumerate(sents, 1))
    return (f"Welcher Satz begründet am besten, dass dieses Geschäft zum Thema «{chname}» gehört? "
            f"Antworte nur mit der Nummer als JSON.\n\nGeschäft (in nummerierten Sätzen):\n{num}\n\n"
            "Antworte nur mit der Nummer des Satzes als JSON: {\"satz\": \"<Nummer>\"}")


def sample():
    items = json.load(open(f"{S9DATA}/items.json"))
    pool = sorted((it for it in items if de_of(it)['text'].strip() and it['oid'] in raw['d1']
                   and it['oid'] in raw['d0a'] and it['oid'] in raw['d0b']), key=lambda it: str(it['oid']))
    return random.Random(SEED).sample(pool, N), len(pool)


_stop = threading.Event()
_lock = threading.Lock()
def work(it, done):
    o = it['oid']
    if o in done or _stop.is_set(): return
    d = de_of(it); sents = sentences(d); x = d1(o); ch = x['ch']
    user = prompt(sents, CH_DE[ch])
    msgs = [{"role": "user", "content": user}, {"role": "assistant", "content": PREFILL}]
    choice, meta = pai.chat(msgs, model=MODEL, max_tokens=3, temperature=0.0, tag=TAG, tag_cap_usd=CAP, logprobs=True,
                            top_logprobs=20, continue_final_message=True, add_generation_prompt=False)
    resp = meta.get("resp") or {}
    gen = (choice.get("message") or {}).get("content") or ""
    if gen.startswith(PREFILL): gen = gen[len(PREFILL):]
    m = re.match(r"\s*(\d+)", gen); k = int(m.group(1)) if m else None
    sent = sents[k - 1] if k and 1 <= k <= len(sents) else None
    full = "\n".join(input_parts(d))
    lp = (choice.get("logprobs") or {}).get("content") or []
    top1 = [dict(t=t["token"], lp=round(t["logprob"], 4)) for t in lp[0]["top_logprobs"]] if lp else []
    gold = int(it['chapter'])
    row = dict(oid=o, gold=gold, gold_name=CH_DE[gold], d1=ch, d1_name=CH_DE[ch], d1_conf=round(x['conf'], 4), correct=ch == gold,
               n_sents=len(sents), gen=gen, num=k, sentence=sent, substring_ok=bool(sent) and sent in full,
               first_tok_top=top1, fp=resp.get("system_fingerprint"), model=resp.get("model"), pt=meta["prompt_tokens"],
               ct=meta["completion_tokens"], usd=meta["usd"], cached=meta.get("cached"), http=meta.get("http"))
    with _lock:
        if row["fp"] != BUILD:
            _stop.set()
            with open(f"{HERE}/raw/offbuild.jsonl", "a") as f: f.write(json.dumps(row, ensure_ascii=False) + "\n")
            return
        with open(RAWF, "a") as f: f.write(json.dumps(row, ensure_ascii=False) + "\n")


def build_packet(samp):
    rows = load(RAWF)
    byo = {it['oid']: it for it in samp}
    valid = [o for o in (it['oid'] for it in samp) if o in rows and rows[o]['sentence']]
    rng = random.Random(SEED + 12); rng.shuffle(valid)
    blocks, key, tmpl = [], [], []
    for i, o in enumerate(valid, 1):
        pid = f"E{i:03d}"; r = rows[o]; d = de_of(byo[o])
        lines = [f"=== {pid} ===", "Parlament: Bundesversammlung (Bund)", "", f"Titel: {d['title']}"]
        if d.get('title_long') and d['title_long'] != d['title']: lines.append(f"Langer Titel: {d['title_long'][:400]}")
        lines += ["", f"Text (Anfang): {d['text'][:1500]}", "", f"Vorgeschlagenes Thema: {r['d1_name']}",
                  f"Zitierter Satz: «{r['sentence']}»", ""]
        blocks.append("\n".join(lines)); tmpl.append(f"{pid}\t")
        key.append(dict(pid=pid, oid=o, d1=r['d1'], d1_name=r['d1_name'], gold=r['gold'], gold_name=r['gold_name'],
                        correct=r['correct'], sentence=r['sentence'], substring_ok=r['substring_ok']))
    open(f"{HERE}/packet/items.txt", "w").write("\n".join(blocks))
    open(f"{HERE}/packet/ann_TEMPLATE.tsv", "w").write("\n".join(tmpl) + "\n")
    with open(f"{HERE}/key.jsonl", "w") as f:
        for k in key: f.write(json.dumps(k, ensure_ascii=False) + "\n")
    return len(valid)


if __name__ == "__main__":
    samp, npool = sample()
    json.dump(dict(seed=SEED, pool=npool, oids=[it['oid'] for it in samp]), open(f"{HERE}/data/sample.json", "w"), indent=0)
    done = set(load(RAWF))
    with ThreadPoolExecutor(3) as ex:
        list(ex.map(lambda it: work(it, done), samp))
    if _stop.is_set():
        print("STOP: off-build fingerprint, see raw/offbuild.jsonl"); sys.exit(2)
    rows = load(RAWF)
    print(f"pool={npool} rows={len(rows)} packet={build_packet(samp)} spent={pai.spent(TAG):.4f}")
