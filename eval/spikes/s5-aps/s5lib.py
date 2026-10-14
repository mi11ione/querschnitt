"""S5 shared code. Reuses S3 (s3lib: Curia labels, descriptions, prompts, readers, metrics) and S1 (APS scheme,
instrumented gw call). Tags must start with bern-s5-; no system messages; model -8b only (enforced in s1lib.call)."""
import json, os, sys, math, random
S3 = '/Users/mi11ion/Desktop/hackapertus/bern/ideation/spikes/s3-accuracy'
sys.path.insert(0, S3)
from s3lib import *  # noqa  (also imports s1lib, gw, MODEL, wilson)
import s3lib, s1lib

OUT5 = os.path.dirname(os.path.abspath(__file__))
RAW5 = os.path.join(OUT5, 'raw')
S5_CAP = 2.00
BUILD_S3 = 'vllm-0.23.1rc1.dev1029+ga601a9d99-tp8-pp2-dd237840'
APS_CODES = ['1.1.1.', '1.1.2.', '1.1.3.', '1.1.4.', '1.1.5.', '1.2.', '1.3.', '1.4.1.', '1.4.2.', '1.4.3.', '1.5.', '1.6.1.',
             '1.6.2.', '1.6.3.', '1.6.4.', '1.7.1.', '1.7.2.', '1.7.3.', '1.7.4.', '1.8.1.', '1.8.2.', '1.8.3.', '2.0.1.', '2.0.2.']
S1PERM = list(range(25)); random.Random(7).shuffle(S1PERM)   # S1/S3 E5 permuted order
SUBS = s1lib.SUBS   # chapter index -> DE subtopic names (190); no FR subtopic names on disk (R1 parsed FR chapter names only)
CODES_EXT = [chr(ord('A') + i) for i in range(26)] + ['a', 'b', 'c', 'd', 'e']   # overflow codes (S3 e1x2: a/b/c least bad)


def spent_s5():
    return sum(v for k, v in gw.spent_summary().items() if k.startswith('bern-s5-'))


def call5(messages, tag, **kw):
    assert tag.startswith('bern-s5-')
    assert not any(m['role'] == 'system' for m in messages)
    return s1lib.call(messages, tag, **kw)


def m1_5(user, prefill, tag, codes):
    ch, meta, rec = call5([{"role": "user", "content": user}, {"role": "assistant", "content": prefill}], tag,
                          max_tokens=1, continue_final_message=True, add_generation_prompt=False, logprobs=True, top_logprobs=20)
    d, raw = read_codes(ch, codes)
    return d, raw, rec


# ---------------------------------------------------------------- Q1: APS chapters with subtopic descriptions
def q1_prompt(a, perm, desc=True):
    """S1 m1_prompt (codes A-Y, 25 options) with each chapter followed by its APS subtopic names (DE)."""
    t = s1lib.T['de']; names = s1lib.CHAPTERS['de']
    def nm(ci):
        s = names[ci]
        if desc and ci < 24: s += f" ({'; '.join(SUBS[ci])})"
        return s
    themes = "\n".join(f"{s1lib.CODES[i]} = {nm(perm[i])}" for i in range(25))
    user = f"{t['ask']}\n\n{t['themes']}:\n{themes}\n\n{t['item']}:\n{s1lib.affair_block(a, 'de')}\n\n{t['fmt_code']}"
    return user, '{"' + t['key'] + '": "'


# ---------------------------------------------------------------- Q2: joint L2 over the subtopics of top-k chapters
Q2_NONE = "Keines dieser Unterthemen passt"
def q2_options(chs):
    """chs: chapter indices in display order -> list of (chapter, subtopic) + none."""
    return [(c, s) for c in chs for s in SUBS[c]]

def q2_prompt(a, chs):
    opts = q2_options(chs); codes = CODES_EXT[:len(opts) + 1]
    names = s1lib.CHAPTERS['de']
    lines, k = [], 0
    for c in chs:
        lines.append(f"Thema «{names[c]}»:")
        for s in SUBS[c]:
            lines.append(f"{codes[k]} = {s}"); k += 1
    lines.append(f"{codes[k]} = {Q2_NONE}")
    ths = ", ".join(f"«{names[c]}»" for c in chs)
    user = (f"Das folgende parlamentarische Geschäft gehört zu einem der Themen {ths} der Année Politique Suisse. "
            f"Ordne es genau einem Unterthema zu.\n\nUnterthemen:\n" + "\n".join(lines) +
            f"\n\nGeschäft:\n{s1lib.affair_block(a, 'de')}\n\n"
            "Antworte nur mit dem Buchstaben des Unterthemas als JSON: {\"unterthema\": \"<Buchstabe>\"}")
    return user, '{"unterthema": "', opts, codes


# ---------------------------------------------------------------- Q4: per-candidate yes/no verification (Curia 28)
Q4_Q = "Betrifft dieses Geschäft der Schweizer Bundesversammlung das Thema «{name}» ({desc})?"
Q4_YES = "Ja, das Geschäft betrifft dieses Thema"
Q4_NO = "Nein, das Geschäft betrifft dieses Thema nicht"
def q4_prompt(x, tag_id, yes_first):
    q = Q4_Q.format(name=lname(tag_id, 'de'), desc=DESC['de'][tag_id])
    opts = [("A", Q4_YES), ("B", Q4_NO)] if yes_first else [("A", Q4_NO), ("B", Q4_YES)]
    u = (f"{q}\n\n" + "\n".join(f"{c} = {s}" for c, s in opts) + f"\n\nGeschäft:\n{item_block(x, 'de')}\n\n"
         "Antworte nur mit dem Buchstaben als JSON: {\"antwort\": \"<Buchstabe>\"}")
    return u, '{"antwort": "'
