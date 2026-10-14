"""S8q: cross-family (Qwen-SEA-LION) pass on the S8 blind packet (reads ONLY packet/GUIDE.md + packet/items.txt).
Prompt = S7 DVS prompt (S4 GUIDE definition verbatim, one item, Y/N). Usage: python3 -I run.py  -> raw.jsonl, ann_Q.tsv"""
import sys, json, time, pathlib, threading
from concurrent.futures import ThreadPoolExecutor, as_completed
sys.path.insert(0, '/Users/mi11ion/Desktop/hackapertus/bern/ideation2/lib')
import pai

MODEL = 'aisingapore/Qwen-SEA-LION-v4-32B-IT'
P = pathlib.Path('/Users/mi11ion/Desktop/hackapertus/bern/ideation2/spikes/s8-dvs/packet')
OUT = pathlib.Path(__file__).resolve().parent
GUIDE = (P / 'GUIDE.md').read_text().split('Answer per line:')[0].strip()
REMIND = "Your previous answer did not follow the format. Answer with exactly one character, Y or N, and nothing else."

def items():
    out = []
    for line in (P / 'items.txt').read_text().splitlines():
        if line.startswith('D') and '\t' in line:
            iid = line.split('\t')[0]
            out.append((iid, ' | '.join(x for x in line.split('\t')[1:] if x)))
    return out

def prompt(text):
    return (f"{GUIDE}\nJudge from the given text only. Do not look anything up.\n\nAffair:\n{text}\n\n"
            "Answer with exactly one character: Y (belongs on the list) or N (does not). No other text.")

def parse(s):
    s = (s or '').strip().strip('`').strip()
    return s if s in ('Y', 'N') else None

def one(iid, text):
    msgs = [{'role': 'user', 'content': prompt(text)}]
    ch, meta = pai.chat(msgs, model=MODEL, max_tokens=5, tag='bern2-s8q', tag_cap_usd=0.40)
    raw1 = ch['message']['content']; ans = parse(raw1); served = [meta['resp'].get('model')]
    if ans is None:
        msgs += [{'role': 'assistant', 'content': raw1 or ''}, {'role': 'user', 'content': REMIND}]
        ch, meta2 = pai.chat(msgs, model=MODEL, max_tokens=5, tag='bern2-s8q', tag_cap_usd=0.40)
        ans = parse(ch['message']['content']); served.append(meta2['resp'].get('model'))
    return dict(id=iid, answer=ans, raw=raw1, served=served, fp=meta['resp'].get('system_fingerprint'))

if __name__ == '__main__':
    its = items(); print('items', len(its), flush=True)
    out = OUT / 'raw.jsonl'
    done = {json.loads(l)['id'] for l in out.read_text().splitlines()} if out.exists() else set()
    lock = threading.Lock()
    with ThreadPoolExecutor(max_workers=3) as ex, open(out, 'a') as f:
        for fu in as_completed([ex.submit(one, i, t) for i, t in its if i not in done]):
            r = fu.result()
            with lock: f.write(json.dumps(r, ensure_ascii=False) + '\n'); f.flush()
    rows = [json.loads(l) for l in out.read_text().splitlines()]
    with open(OUT / 'ann_Q.tsv', 'w') as f:
        for r in sorted(rows, key=lambda r: r['id']): f.write(f"{r['id']}\t{r['answer'] or '?'}\n")
    print('done', len(rows), 'parse_fail', sum(r['answer'] is None for r in rows), 'served_ok', all(s == MODEL for r in rows for s in r['served']))
