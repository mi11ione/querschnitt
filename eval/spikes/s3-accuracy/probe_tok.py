import sys, json
sys.path.insert(0, '/Users/mi11ion/Desktop/hackapertus/bern/ideation/spikes/s1-runtime')
from s1lib import call
out = open('raw/probe_tok.jsonl', 'a')
for cand in ["Ä", "Ö", "Ü", "a", "1", "AA", "AB", "ZZ", "Z1"]:
    msgs = [{"role": "user", "content": "Antworte nur mit einem Code als JSON."},
            {"role": "assistant", "content": '{"thema": "' + cand + '"}'}]
    ch, meta, rec = call(msgs, 'bern-s3-probe', max_tokens=1, continue_final_message=True, add_generation_prompt=False, prompt_logprobs=1)
    pl = meta['resp'].get('prompt_logprobs') or ch.get('prompt_logprobs')
    toks = []
    for e in pl[-6:]:
        if e is None: continue
        v = list(e.values()); act = v[0] if len(v) == 1 else next((x for x in v if x.get('rank') != 1), v[0])
        toks.append(act['decoded_token'])
    print(cand, toks, rec['model'], rec['fp'])
    out.write(json.dumps(dict(cand=cand, toks=toks, rec=rec), ensure_ascii=False) + '\n')
