"""S6 shared code. Reuses S1 (APS scheme de/fr/it, T templates, affair_block, instrumented gw call) and S5 (APS codes,
S1 permutation, DE subtopic names). Tags must start with bern-s6-; no system messages; model -8b only (s1lib.call)."""
import json, os, sys, math
sys.path.insert(0, '/Users/mi11ion/Desktop/hackapertus/bern/ideation/spikes/s5-aps')
from s5lib import APS_CODES, S1PERM, SUBS, CODES_EXT, BUILD_S3, read_codes  # noqa: E402
import s1lib  # noqa: E402
from s1lib import gw, MODEL, wilson  # noqa: E402,F401

S6 = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RAW6 = os.path.join(S6, 'raw')
S6_CAP = 1.50
TAU = 0.9   # second L1 order only when the first order's top p < TAU (S5 selective.json)


def spent_s6():
    return sum(v for k, v in gw.spent_summary().items() if k.startswith('bern-s6-'))


def call6(messages, tag, **kw):
    assert tag.startswith('bern-s6-')
    assert not any(m['role'] == 'system' for m in messages)
    return s1lib.call(messages, tag, **kw)


def m1_6(user, prefill, tag, codes):
    ch, meta, rec = call6([{"role": "user", "content": user}, {"role": "assistant", "content": prefill}], tag,
                          max_tokens=1, continue_final_message=True, add_generation_prompt=False, logprobs=True, top_logprobs=20)
    if rec.get('fp') and rec['fp'] != BUILD_S3 and not rec.get('cached'):
        raise RuntimeError(f"BUILD CHANGED: {rec['fp']}")
    d, raw = read_codes(ch, codes)
    return d, raw, rec


def to_probs(d, codes, n, perm=None):
    """code->logprob -> normalised n-vector in option space (perm[i] = option listed under codes[i])."""
    pv = [0.0] * n
    for c, l in d.items():
        i = codes.index(c)
        pv[perm[i] if perm else i] = math.exp(l)
    s = sum(pv) or 1.0
    return [v / s for v in pv]


def geo(x, y):
    g = [math.exp((math.log(max(a, 1e-12)) + math.log(max(b, 1e-12))) / 2) for a, b in zip(x, y)]
    s = sum(g); return [v / s for v in g]


def argsort_desc(p):
    return sorted(range(len(p)), key=lambda i: -p[i])


# ---------------------------------------------------------------- A1 L1: S5 Q1 variant (c), in the affair's language
def block(a):
    return s1lib.affair_block(a, a['lang'])


def l1_prompt(a, perm):
    """S1 M1 prompt (codes A-Y, 25 options) in the affair's language; each chapter followed by its APS subtopic names
    (DE: the only subtopic names on disk). For lang=de this is byte-identical to S5 q1_prompt."""
    lang = a['lang']; t = s1lib.T[lang]; names = s1lib.CHAPTERS[lang]
    def nm(ci):
        s = names[ci]
        if ci < 24: s += f" ({'; '.join(SUBS[ci])})"
        return s
    themes = "\n".join(f"{s1lib.CODES[i]} = {nm(perm[i])}" for i in range(25))
    user = f"{t['ask']}\n\n{t['themes']}:\n{themes}\n\n{t['item']}:\n{block(a)}\n\n{t['fmt_code']}"
    return user, '{"' + t['key'] + '": "'


# ---------------------------------------------------------------- A1 L2: S5 Q2 joint L2, frame in the affair's language
L2T = {
    'de': dict(ask="Das folgende parlamentarische Geschäft gehört zu einem der Themen {ths} der Année Politique Suisse. "
                   "Ordne es genau einem Unterthema zu.", head="Thema «{c}»:", none="Keines dieser Unterthemen passt",
               q="«{c}»"),
    'fr': dict(ask="L'objet parlementaire suivant relève de l'un des thèmes {ths} de l'Année politique suisse. "
                   "Attribue-le à exactement un sous-thème.", head="Thème « {c} » :", none="Aucun de ces sous-thèmes ne convient",
               q="« {c} »"),
    'it': dict(ask="Il seguente oggetto parlamentare rientra in uno dei temi {ths} dell'Année Politique Suisse. "
                   "Assegnalo a esattamente un sottotema.", head="Tema «{c}»:", none="Nessuno di questi sottotemi è adatto",
               q="«{c}»"),
}


def l2_chapters(p):
    """S5 q2_chapters: top-3 chapters (excluding 'none') if their subtopics total <= 26, else top-2; top chapter first."""
    order = [i for i in argsort_desc(p) if i < 24]
    top3 = order[:3]
    return top3 if sum(len(SUBS[c]) for c in top3) <= 26 else order[:2]


def l2_prompt(a, chs):
    lang = a['lang']; t = s1lib.T[lang]; L = L2T[lang]; names = s1lib.CHAPTERS[lang]
    opts = [(c, s) for c in chs for s in SUBS[c]]; codes = CODES_EXT[:len(opts) + 1]
    lines, k = [], 0
    for c in chs:
        lines.append(L['head'].format(c=names[c]))
        for s in SUBS[c]:
            lines.append(f"{codes[k]} = {s}"); k += 1
    lines.append(f"{codes[k]} = {L['none']}")
    ths = ", ".join(L['q'].format(c=names[c]) for c in chs)
    user = (L['ask'].format(ths=ths) + f"\n\n{t['subs']}:\n" + "\n".join(lines) + f"\n\n{t['item']}:\n{block(a)}\n\n{t['fmt_sub']}")
    return user, '{"' + t['subkey'] + '": "', opts, codes
