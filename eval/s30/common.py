"""S30 shared pieces: client on the locked build, the scope generation request, the variant prompts, one closed choice.
Variant prompts live here until one is chosen; the product copy (if any) goes to src/querschnitt/prompts.py."""
import json, math, sys, threading
from pathlib import Path
HERE = Path(__file__).resolve().parent; ROOT = HERE.parents[1]
sys.path.insert(0, str(ROOT / "src"))
from querschnitt import prompts as P  # noqa: E402
from querschnitt.adhoc import parse_json, _clean  # noqa: E402
from querschnitt.client import Client, Endpoint, read_codes  # noqa: E402

BUILD = "vllm-0.23.1rc1.dev1029+ga601a9d99-tp8-pp2-dd237840"
LANGS = ("de", "fr", "it")


def client(ledger: Path, tag: str, cap: float = 2.0) -> Client:
    ep = Endpoint.from_env(); ep.max_rate, ep.conc = 0.5, 2
    assert "-70b" not in ep.model.lower()
    return Client(ep, ledger=str(ledger), cap_usd=cap, expect_build=BUILD, tag=tag)


# ---- (a) scope: one plain generation request per topic, user message only (like adhoc.TOPIC_PROMPT)
SCOPE_PROMPT = (
    "Thema, in einem Satz: «{sentence}»\n\n"
    "Ein Redaktionsteam prüft Titel von parlamentarischen Geschäften der Schweiz auf dieses Thema. Schreibe für jede Sprache "
    "(Deutsch, Französisch, Italienisch):\n"
    "1. include: was dazu gehört, als kurze Liste (höchstens acht Stichworte, durch Kommas getrennt);\n"
    "2. exclude: verwandte, aber andere Themen, die nicht dazu gehören (höchstens sechs Stichworte, durch Kommas getrennt).\n\n"
    "Antworte nur mit JSON in einer Zeile:\n"
    '{{"include": {{"de": "…", "fr": "…", "it": "…"}}, "exclude": {{"de": "…", "fr": "…", "it": "…"}}}}')


def gen_scope(c: Client, sentence: str) -> dict:
    ch, meta = c.chat([{"role": "user", "content": SCOPE_PROMPT.format(sentence=_clean(sentence, 400))}], max_tokens=600, logprobs=None)
    raw = (ch.get("message") or {}).get("content") or ""
    v = parse_json(raw) or {}
    out = {}
    for f in ("include", "exclude"):
        d = v.get(f) if isinstance(v.get(f), dict) else {}
        out[f] = {l: _clean(d.get(l), 300) for l in LANGS}
    return dict(scope=out, raw=raw, fp=meta["fp"], usd=meta["usd"])


# ---- variant frames (closed choice A/B, user message + assistant prefill, item block as yesno_prompt)
FR = {
 "de": dict(incl="Dazu gehört:", excl="Nicht dazu gehört:", untitled="Geschäfte, deren Titel das Thema nicht erkennen lässt",
            ask="Gehört das folgende parlamentarische Geschäft zum Thema «{name}»?",
            central="Ist «{name}» ein zentrales Thema dieses Geschäfts – nicht nur am Rande erwähnt oder bloss ähnlich?",
            yes="Ja, das Geschäft gehört zum Thema «{name}»", no="Nein, anderes Thema", cyes="Ja, zentral", cno="Nein"),
 "fr": dict(incl="En font partie :", excl="N'en font pas partie :", untitled="objets dont le titre ne laisse pas reconnaître le thème",
            ask="L'objet parlementaire suivant relève-t-il du thème « {name} » ?",
            central="« {name} » est-il un thème central de cet objet – et non seulement mentionné en passant ou simplement voisin ?",
            yes="Oui, l'objet relève du thème « {name} »", no="Non, autre thème", cyes="Oui, central", cno="Non"),
 "it": dict(incl="Ne fanno parte:", excl="Non ne fanno parte:", untitled="oggetti il cui titolo non lascia riconoscere il tema",
            ask="Il seguente oggetto parlamentare rientra nel tema «{name}»?",
            central="«{name}» è un tema centrale di questo oggetto – non solo menzionato di passaggio o semplicemente affine?",
            yes="Sì, l'oggetto rientra nel tema «{name}»", no="No, altro tema", cyes="Sì, centrale", cno="No"),
}


def scope_lines(scope: dict, lang: str) -> str:
    f = FR[lang]; inc = scope["include"].get(lang) or scope["include"].get("de") or ""
    exc = scope["exclude"].get(lang) or scope["exclude"].get("de") or ""
    exc = (exc.rstrip(" .;,") + ", " if exc else "") + f["untitled"]
    return (f"{f['incl']} {inc.rstrip(' .')}.\n" if inc else "") + f"{f['excl']} {exc}."


def _item(lang, title, title_long):
    item, ti, tl, _no, fmt, key = P.YN[lang]
    blk = f"{ti}: {title[:400]}" + (f"\n{tl}: {title_long[:400]}" if title_long and title_long != title else "")
    return f"{item}:\n{blk}\n\n{fmt}", '{"' + key + '": "'


def scope_prompt(name: dict, scope: dict, lang, title, title_long, order="a", central=False):
    """central=False: 'does it belong to «name»?' with include/exclude lines (V1 second stage, V3 first stage);
    central=True: the S27 question with the same lines (V2)."""
    f = FR[lang]; nm = name[lang]
    q = (f["central"] if central else f["ask"]).format(name=nm)
    yes, no = (f["cyes"], f["cno"]) if central else (f["yes"].format(name=nm), f["no"])
    opts = [("A", yes), ("B", no)] if order == "a" else [("A", no), ("B", yes)]
    tail, pre = _item(lang, title, title_long)
    u = f"{q}\n{scope_lines(scope, lang)}\n\n" + "\n".join(f"{c} = {s}" for c, s in opts) + f"\n\n{tail}"
    return u, pre


def ask(c: Client, u: str, pre: str, order: str) -> tuple[float, str]:
    ch, meta = c.chat([{"role": "user", "content": u}, {"role": "assistant", "content": pre}], max_tokens=1)
    d = read_codes(ch, ["A", "B"]); pa, pb = math.exp(d.get("A", -50)), math.exp(d.get("B", -50))
    return (pa if order == "a" else pb) / (pa + pb), meta["fp"]


def two(c: Client, build, *args, **kw) -> dict:
    """The shipped two-order rule: order a; order b when 0.1 < p < 0.9; mean."""
    ua, pre = build(*args, order="a", **kw); pa, fp = ask(c, ua, pre, "a")
    pb = None
    if 0.1 < pa < 0.9:
        ub, pre = build(*args, order="b", **kw); pb, _ = ask(c, ub, pre, "b")
    return dict(p_a=pa, p_b=pb, p=(pa + pb) / 2 if pb is not None else pa, fp=fp, prompt_id=P.pid(ua, pre))


# ---- contrast check: the topic against its generated neighbours (the exclude list), "other" and "not recognisable"
CT = {"de": ("Welches Thema behandelt das folgende parlamentarische Geschäft?", "anderes Thema", "Thema aus dem Titel nicht erkennbar"),
      "fr": ("Quel thème l'objet parlementaire suivant traite-t-il ?", "autre thème", "thème non reconnaissable à partir du titre"),
      "it": ("Quale tema tratta il seguente oggetto parlamentare?", "altro tema", "tema non riconoscibile dal titolo")}


def neighbours(scope: dict, lang: str, n: int = 7) -> list[str]:
    exc = scope["exclude"].get(lang) or scope["exclude"].get("de") or ""
    out = []
    for s in exc.split(","):
        s = s.strip(" .;")
        if s and s.lower() not in {o.lower() for o in out}:
            out.append(s)
    return out[:n]


def contrast_prompt(name: dict, scope: dict, lang, title, title_long, order="a"):
    """Order a: the topic is A; order b: the neighbours first, the topic after them. Last two codes: other, not
    recognisable. Returns user, prefill, codes, topic code."""
    q, other, unclear = CT[lang]
    inc = (scope["include"].get(lang) or scope["include"].get("de") or "").rstrip(" .")
    top = f"{name[lang]}" + (f" ({inc})" if inc else "")
    nb = neighbours(scope, lang)
    opts = ([top] + nb) if order == "a" else (nb + [top])
    opts += [other, unclear]
    codes = [chr(ord("A") + i) for i in range(len(opts))]
    tail, pre = _item(lang, title, title_long)
    u = f"{q}\n\n" + "\n".join(f"{c} = {s}" for c, s in zip(codes, opts)) + f"\n\n{tail}"
    return u, pre, codes, codes[0 if order == "a" else len(nb)]


def ask_multi(c: Client, u, pre, codes, tc) -> tuple[float, str]:
    ch, meta = c.chat([{"role": "user", "content": u}, {"role": "assistant", "content": pre}], max_tokens=1)
    d = read_codes(ch, codes); ps = {k: math.exp(d.get(k, -50)) for k in codes}
    return ps[tc] / sum(ps.values()), meta["fp"]


def two_contrast(c: Client, *args) -> dict:
    ua, pre, codes, tc = contrast_prompt(*args, order="a"); pa, fp = ask_multi(c, ua, pre, codes, tc)
    pb = None
    if 0.1 < pa < 0.9:
        ub, pre, codes, tc = contrast_prompt(*args, order="b"); pb, _ = ask_multi(c, ub, pre, codes, tc)
    return dict(p_a=pa, p_b=pb, p=(pa + pb) / 2 if pb is not None else pa, fp=fp, prompt_id=P.pid(ua, pre))
