"""S7: cross-family re-annotation of the S4 (DVS digitalisation) and S6 (cantonal APS chapter) packets with
aisingapore/Qwen-SEA-LION-v4-32B-IT via the budget gateway. Reads ONLY the packet files.
Usage: python3 -I run.py dvs|aps [limit]
Writes raw/<set>.jsonl (one row per item, appended as results arrive; rerun resumes, cached calls are free)."""
import sys, re, json, time, pathlib, threading
from concurrent.futures import ThreadPoolExecutor, as_completed
sys.path.insert(0, '/Users/mi11ion/Desktop/hackapertus/gateway')
from gw import chat

MODEL = 'aisingapore/Qwen-SEA-LION-v4-32B-IT'
SP = pathlib.Path('/Users/mi11ion/Desktop/hackapertus/bern/ideation/spikes')
OUT = SP / 's7-crossfamily/raw'
CAPS = {'dvs': 0.30, 'aps': 0.60}            # per-tag caps; sum <= USD 0.90 (< 1.00 incl. probe)
CODES = ['1.1.1.', '1.1.2.', '1.1.3.', '1.1.4.', '1.1.5.', '1.2.', '1.3.', '1.4.1.', '1.4.2.', '1.4.3.', '1.5.',
         '1.6.1.', '1.6.2.', '1.6.3.', '1.6.4.', '1.7.1.', '1.7.2.', '1.7.3.', '1.7.4.', '1.8.1.', '1.8.2.', '1.8.3.',
         '2.0.1.', '2.0.2.', '0']

# ---------- items ----------
def dvs_items():
    items, cur = [], None
    for line in (SP / 's4-blindcheck/packet/items.txt').read_text().splitlines():
        if re.match(r'^T\d{3} \|', line):
            cur = [line.split(' |')[0], line.rstrip()]; items.append(cur)
        elif line.strip():
            cur[1] += '\n' + line.rstrip()           # continuation line belongs to the previous id
    return [(i, t) for i, t in items]

def aps_items():
    txt = (SP / 's6-cantonal/packet/items.txt').read_text()
    parts = re.split(r'^=== (C\d{3}) ===\s*$', txt, flags=re.M)
    return [(parts[k], parts[k + 1].strip()) for k in range(1, len(parts), 2)]

# ---------- prompts ----------
DVS_GUIDE = (SP / 's4-blindcheck/packet/GUIDE.md').read_text()
def dvs_prompt(iid, text):
    guide = DVS_GUIDE.split('Answer per line:')[0].strip()   # drop the batch-file answer format; definition kept verbatim
    return (f"{guide}\nJudge from the given text only. Do not look anything up.\n\n"
            f"Affair:\n{text}\n\n"
            "Answer with exactly one character: Y (belongs on the list) or N (does not). No other text.")

APS_GUIDE = (SP / 's6-cantonal/packet/GUIDE.md').read_text()
def aps_guide():
    g = APS_GUIDE
    g = re.sub(r'## Output.*?(?=## Rules)', '', g, flags=re.S)          # drop annotator file instructions
    g = g.replace('You get 160 parliamentary affairs', 'You get one parliamentary affair')
    g = g.replace('For each affair, choose', 'Choose')
    g = re.sub(r'## Input\n.*?(?=## Rules)', '## Input\nOne affair: the parliament, the affair type and the text: title, long title (if any), and for most affairs the first\n1,500 characters of a document (often the executive\'s reply, which usually restates the question). Some affairs are\ntitle-only. Judge only from this text; do not look anything up.\n\n', g, flags=re.S)
    assert all(f'`{c}`' in g for c in CODES), 'chapter table incomplete'
    return g.strip()
APS_G = aps_guide()
def aps_prompt(iid, text):
    return (f"{APS_G}\n\n## Affair\n{text}\n\n## Answer format\n"
            "Answer with the chapter code exactly as in the table (including the trailing dot), or 0. If the affair clearly "
            "also belongs to a second chapter, add it after one space. No other text.\n"
            "Examples of valid answers: `1.6.2.` or `1.4.1. 1.6.3.` or `0`")

REMIND = {'dvs': "Your previous answer did not follow the format. Answer with exactly one character, Y or N, and nothing else.",
          'aps': "Your previous answer did not follow the format. Answer with only the chapter code(s) exactly as in the table "
                 "(e.g. `1.6.2.` or `1.4.1. 1.6.3.`) or `0`, and nothing else."}

# ---------- strict parsers ----------
def parse_dvs(s):
    s = s.strip().strip('`').strip()
    return s if s in ('Y', 'N') else None

CODE_RE = '|'.join(re.escape(c) for c in sorted(CODES, key=len, reverse=True))
def parse_aps(s):
    s = s.strip().strip('`').strip()
    m = re.fullmatch(rf'({CODE_RE})(?:[ \t]+`?({CODE_RE})`?)?', s)
    if not m: return None
    a, b = m.group(1), m.group(2)
    if a == '0' and b: return None
    if b == a or b == '0': b = None
    return [a, b]

# ---------- runner ----------
def call(msgs, tag, max_tokens):
    for k in range(6):
        try:
            return chat(msgs, model=MODEL, max_tokens=max_tokens, temperature=0.0, tag=tag, tag_cap_usd=CAPS[tag.split('-')[-1]], full=True)
        except RuntimeError: raise                    # budget refusal: stop
        except Exception as e:
            if '429' in str(e) or 'Too Many' in str(e) or 'timed out' in str(e) or 'HTTP Error 5' in str(e):
                time.sleep(10 * (k + 1)); continue
            raise
    raise RuntimeError('retries exhausted')

def one(setname, iid, text):
    tag = f'bern-s7-{setname}'
    prompt = (dvs_prompt if setname == 'dvs' else aps_prompt)(iid, text)
    parse = parse_dvs if setname == 'dvs' else parse_aps
    mt = 5 if setname == 'dvs' else 16
    msgs = [{'role': 'user', 'content': prompt}]
    ch, meta = call(msgs, tag, mt)
    raw1 = ch['message']['content'] or ''
    served = [meta.get('resp', {}).get('model')]
    usd = meta['usd'] if not meta.get('cached') else 0.0
    ans, reasked = parse(raw1), False
    raw2 = None
    if ans is None:
        reasked = True
        msgs2 = msgs + [{'role': 'assistant', 'content': raw1}, {'role': 'user', 'content': REMIND[setname]}]
        ch2, meta2 = call(msgs2, tag, mt)
        raw2 = ch2['message']['content'] or ''
        served.append(meta2.get('resp', {}).get('model'))
        usd += meta2['usd'] if not meta2.get('cached') else 0.0
        ans = parse(raw2)
    model_ok = all(s == MODEL for s in served)
    return dict(id=iid, answer=ans, parse_fail=ans is None, reasked=reasked, raw1=raw1, raw2=raw2, served_models=served,
                model_ok=model_ok, usd=usd, cached=bool(meta.get('cached')), resp_id=meta.get('resp', {}).get('id'))

def main():
    setname = sys.argv[1]; limit = int(sys.argv[2]) if len(sys.argv) > 2 else None
    items = dvs_items() if setname == 'dvs' else aps_items()
    assert len(items) == (300 if setname == 'dvs' else 160), len(items)
    if limit: items = items[:limit]
    out = OUT / f'{setname}.jsonl'
    done = set()
    if out.exists():
        done = {json.loads(l)['id'] for l in out.read_text().splitlines() if l.strip()}
    todo = [it for it in items if it[0] not in done]
    lock = threading.Lock(); n = 0
    with ThreadPoolExecutor(max_workers=6) as ex, open(out, 'a') as f:
        futs = {ex.submit(one, setname, i, t): i for i, t in todo}
        for fu in as_completed(futs):
            r = fu.result()
            with lock:
                f.write(json.dumps(r, ensure_ascii=False) + '\n'); f.flush(); n += 1
                if n % 25 == 0: print(setname, n, '/', len(todo), flush=True)
    print('done', setname, n)

if __name__ == '__main__':
    main()
