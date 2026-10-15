"""Prompt builders. Every string here is byte-identical to the prompts measured in the spikes (S1/S5/S9 chapter and
subtopic steps, S3 E6 / S8 yes/no, S12 evidence); tests/test_prompts.py pins their hashes. Change a prompt and the
prompt id changes, so rows made with it are re-scored, never mixed.

All classification calls end with an assistant prefill that opens a JSON value (`{"kapitel": "`), so the next token is
the code; the engine reads that token's top log-probabilities (or, without them, the generated code).

QS_PREFILL=0 selects the no-prefill mode for endpoints that cannot continue an assistant message: one user message, the
measured prompt plus a line asking the answer to begin with the prefill text (`no_prefill_user`). It is NOT measured; its
prompt ids differ from every measured one (`pid` hashes the message actually sent), so its rows never mix with measured
rows, and compose applies no calibration to them."""
from __future__ import annotations

import hashlib
import random
import re

from .client import prefill_from_env
from .scheme import APS

NO_PREFILL = "no-prefill"


def prefill_on() -> bool:
    """True = the measured prefill design (default); False = the no-prefill mode (QS_PREFILL=0)."""
    return prefill_from_env()


def mode() -> str | None:
    """None for the measured design, "no-prefill" otherwise (stored in row meta, the run lock and export meta)."""
    return None if prefill_on() else NO_PREFILL


NOPRE = {"de": "Beginne deine Antwort genau mit `{pre}` und schreibe nichts davor.",
         "fr": "Commence ta réponse exactement par `{pre}` sans rien écrire avant.",
         "it": "Inizia la risposta esattamente con `{pre}` senza scrivere nulla prima."}


def no_prefill_user(user: str, prefill: str) -> str:
    """The no-prefill mode's single user message: the measured prompt, then one line (in the language of its answer
    format line) asking the answer to begin with the prefill text."""
    last = user.rstrip().rsplit("\n", 1)[-1]
    lang = "fr" if last.startswith("Réponds") else "it" if last.startswith("Rispondi") else "de"
    return user + "\n\n" + NOPRE[lang].format(pre=prefill)

CODES = [chr(ord("A") + i) for i in range(25)]                     # A..Y: 24 chapters + none
CODES_EXT = [chr(ord("A") + i) for i in range(26)] + ["a", "b", "c", "d", "e"]
S1PERM = list(range(25)); random.Random(7).shuffle(S1PERM)         # second reading: the S1/S3 E5 code order

T = {
 "de": dict(key="kapitel", ask="Ordne das folgende parlamentarische Geschäft genau einem Thema der Année Politique Suisse zu.",
            themes="Themen", item="Geschäft", title="Titel", tlong="Langtitel", text="Text (Auszug)",
            fmt_code="Antworte nur mit dem Buchstaben des Themas als JSON: {\"kapitel\": \"<Buchstabe>\"}",
            subkey="unterthema", subs="Unterthemen", fmt_sub="Antworte nur mit dem Buchstaben des Unterthemas als JSON: {\"unterthema\": \"<Buchstabe>\"}"),
 "fr": dict(key="chapitre", ask="Attribue l'objet parlementaire suivant à exactement un thème de l'Année politique suisse.",
            themes="Thèmes", item="Objet", title="Titre", tlong="Titre long", text="Texte (extrait)",
            fmt_code="Réponds uniquement par la lettre du thème en JSON : {\"chapitre\": \"<lettre>\"}",
            subkey="sous_theme", subs="Sous-thèmes", fmt_sub="Réponds uniquement par la lettre du sous-thème en JSON : {\"sous_theme\": \"<lettre>\"}"),
 "it": dict(key="capitolo", ask="Assegna il seguente oggetto parlamentare a esattamente un tema dell'Année Politique Suisse.",
            themes="Temi", item="Oggetto", title="Titolo", tlong="Titolo lungo", text="Testo (estratto)",
            fmt_code="Rispondi solo con la lettera del tema in JSON: {\"capitolo\": \"<lettera>\"}",
            subkey="sottotema", subs="Sottotemi", fmt_sub="Rispondi solo con la lettera del sottotema in JSON: {\"sottotema\": \"<lettera>\"}"),
}


def pid(user: str, prefill: str, prefill_mode: bool | None = None) -> str:
    """Prompt identity: sha256 of the exact messages sent (first 12 hex). In the no-prefill mode (QS_PREFILL=0, or
    `prefill_mode=False`) that is `no_prefill_user(user, prefill)` with no assistant message, so the id can never equal
    a measured one (those always hash a non-empty prefill after the separator)."""
    if not (prefill_on() if prefill_mode is None else prefill_mode):
        user, prefill = no_prefill_user(user, prefill), ""
    return hashlib.sha256((user + "\x00" + prefill).encode()).hexdigest()[:12]


def affair_block(a: dict, lang: str = "de", text_chars: int = 1500) -> str:
    """Title, long title (if different, first 400 chars) and the first 1,500 characters of text, labelled in `lang`."""
    t = T[lang]
    lines = [f"{t['title']}: {a['title']}"]
    if a.get("title_long") and a["title_long"] != a["title"]:
        lines.append(f"{t['tlong']}: {a['title_long'][:400]}")
    if a.get("text"):
        lines.append(f"{t['text']}: {a['text'][:text_chars]}")
    return "\n".join(lines)


def _chapter_line(ci: int, names: list[str]) -> str:
    s = names[ci]
    if ci < 24:
        s += f" ({'; '.join(APS.subs_de[ci])})"
    return s


def chapter_prompt(a: dict, perm: list[int], lang: str | None = None) -> tuple[str, str]:
    """APS chapter step (S5 variant c): every chapter followed by its subtopic names (German: the only subtopic names
    APS publishes). Frame and chapter names in the affair's language (S6/S10; for German byte-identical to S5/S9).
    perm[i] = the chapter listed under code CODES[i]."""
    lang = lang or a.get("lang") or "de"
    t = T[lang]; names = APS.names[lang]
    themes = "\n".join(f"{CODES[i]} = {_chapter_line(perm[i], names)}" for i in range(25))
    user = f"{t['ask']}\n\n{t['themes']}:\n{themes}\n\n{t['item']}:\n{affair_block(a, lang)}\n\n{t['fmt_code']}"
    return user, '{"' + t["key"] + '": "'


EX_HEAD = "Frühere Geschäfte mit ihren Themen (zur Orientierung):"


def chapter_prompt_examples(a: dict, perm: list[int], examples: list[tuple[str, int]]) -> tuple[str, str]:
    """Chapter step with labelled examples (S9 D3): `examples` = [(title, chapter index)], shown between list and item."""
    t = T["de"]; names = APS.chapter_names_de_with_none; inv = {perm[i]: i for i in range(25)}
    themes = "\n".join(f"{CODES[i]} = {_chapter_line(perm[i], names)}" for i in range(25))
    ex = "\n".join(f"- {ti}\n  → Thema: {CODES[inv[c]]} ({names[c]})" for ti, c in examples)
    user = (f"{t['ask']}\n\n{t['themes']}:\n{themes}\n\n{EX_HEAD}\n{ex}\n\n{t['item']}:\n{affair_block(a, 'de')}"
            f"\n\n{t['fmt_code']}")
    return user, '{"' + t["key"] + '": "'


Q2_NONE = "Keines dieser Unterthemen passt"


def subtopic_options(chs: list[int]) -> list[tuple[int, int]]:
    return [(c, j) for c in chs for j in range(len(APS.subs_de[c]))]


L2T = {
    "de": dict(ask="Das folgende parlamentarische Geschäft gehört zu einem der Themen {ths} der Année Politique Suisse. "
                   "Ordne es genau einem Unterthema zu.", head="Thema «{c}»:", none=Q2_NONE, q="«{c}»"),
    "fr": dict(ask="L'objet parlementaire suivant relève de l'un des thèmes {ths} de l'Année politique suisse. "
                   "Attribue-le à exactement un sous-thème.", head="Thème « {c} » :", none="Aucun de ces sous-thèmes ne convient",
               q="« {c} »"),
    "it": dict(ask="Il seguente oggetto parlamentare rientra in uno dei temi {ths} dell'Année Politique Suisse. "
                   "Assegnalo a esattamente un sottotema.", head="Tema «{c}»:", none="Nessuno di questi sottotemi è adatto",
               q="«{c}»"),
}


def subtopic_prompt(a: dict, chs: list[int], lang: str | None = None):
    """One request over the subtopics of the top chapters (S5 joint L2), top chapter first, frame in the affair's language
    (S6). Returns user, prefill, options [(chapter, subtopic index)] and codes (last code = none of these)."""
    lang = lang or a.get("lang") or "de"
    t = T[lang]; L = L2T[lang]; names = APS.names[lang]
    opts = subtopic_options(chs); codes = CODES_EXT[:len(opts) + 1]
    lines, k = [], 0
    for c in chs:
        lines.append(L["head"].format(c=names[c]))
        for s in APS.subs_de[c]:
            lines.append(f"{codes[k]} = {s}"); k += 1
    lines.append(f"{codes[k]} = {L['none']}")
    ths = ", ".join(L["q"].format(c=names[c]) for c in chs)
    user = (L["ask"].format(ths=ths) + f"\n\n{t['subs']}:\n" + "\n".join(lines) + f"\n\n{t['item']}:\n{affair_block(a, lang)}\n\n{t['fmt_sub']}")
    return user, '{"' + t["subkey"] + '": "', opts, codes


def subtopic_chapters(p: list[float]) -> list[int]:
    """Top-3 chapters (none excluded) if their subtopics total <= 26 codes, else top-2 (S9 rule)."""
    order = [i for i in sorted(range(25), key=lambda i: -p[i]) if i < 24]
    top3 = order[:3]
    return top3 if sum(len(APS.subs_de[c]) for c in top3) <= 26 else order[:2]


# ---- ad-hoc yes/no (S3 E6 frame; the topic file supplies question + scope note and the yes answer)
YN = {"de": ("Geschäft", "Titel", "Langtitel", "Nein, anderes Thema", "Antworte nur mit dem Buchstaben als JSON: {\"antwort\": \"<Buchstabe>\"}", "antwort"),
      "fr": ("Objet", "Titre", "Titre long", "Non, autre thème", "Réponds uniquement par la lettre en JSON : {\"reponse\": \"<lettre>\"}", "reponse"),
      "it": ("Oggetto", "Titolo", "Titolo lungo", "No, altro tema", "Rispondi solo con la lettera in JSON: {\"risposta\": \"<lettera>\"}", "risposta")}


EX_YN_HEAD = {"de": "Beispiele, von einer Redaktorin entschieden:", "fr": "Exemples décidés par une rédactrice :",
              "it": "Esempi decisi da una redattrice:"}


def yesno_prompt(topic: dict, lang: str, title: str, title_long: str, order: str = "a",
                 examples: list[tuple[str, bool]] | None = None) -> tuple[str, str]:
    """order 'a': A = yes; order 'b': A = no. Title + long title (first 400 chars each), in the affair's language.
    `examples` (editor decisions, optional) are listed before the item as `- title → A/B`."""
    item, ti, tl, no, fmt, key = YN[lang]
    q, yes = topic["question"][lang], topic["answer_yes"][lang]
    opts = [("A", yes), ("B", no)] if order == "a" else [("A", no), ("B", yes)]
    blk = f"{ti}: {title[:400]}" + (f"\n{tl}: {title_long[:400]}" if title_long and title_long != title else "")
    ex = ""
    if examples:  # P8.5 loop format (S8): the 4 most similar decided affairs, "- Titel: … → A/B"
        yc, nc = ("A", "B") if order == "a" else ("B", "A")
        ex = EX_YN_HEAD[lang] + "\n" + "\n".join(f"- {ti}: {t[:300]} → {yc if y else nc}" for t, y in examples) + "\n\n"
    u = f"{q}\n\n" + "\n".join(f"{c} = {s}" for c, s in opts) + f"\n\n{ex}{item}:\n{blk}\n\n{fmt}"
    return u, '{"' + key + '": "'


# ---- evidence: one closed choice over the affair's numbered sentences (S12)
SPLIT = re.compile(r"(?<=[.!?;])\s+")


def evidence_parts(a: dict) -> list[tuple[str, str]]:
    """(source field, text) in input order: title, long title (if different, first 400 chars), first 1,500 chars of text."""
    parts = [("title", a["title"])]
    if a.get("title_long") and a["title_long"] != a["title"]:
        parts.append(("title_long", a["title_long"][:400]))
    if a.get("text"):
        parts.append(("text", a["text"][:1500]))
    return parts


PATHLIKE = re.compile(r"[A-Za-z]:\\|\\[^\s]|\.(docx?|pdf|xlsx?)\b|https?://", re.I)


def sentences(a: dict) -> list[tuple[str, str]]:
    """Candidate evidence sentences (≥ 25 characters); file paths, document names and URLs are never offered."""
    out = []
    for src, part in evidence_parts(a):
        for s in SPLIT.split(part):
            s = s.strip()
            if len(s) >= 25 and not PATHLIKE.search(s):
                out.append((src, s))
    return out[:40]


EVID_Q = {
 "de": ("Welcher Satz begründet am besten, dass dieses Geschäft zum Thema «{name}» gehört? Antworte nur mit der Nummer als JSON.\n\n"
        "Geschäft (in nummerierten Sätzen):\n{num}\n\nAntworte nur mit der Nummer des Satzes als JSON: {{\"satz\": \"<Nummer>\"}}", '{"satz": "'),
}


def evidence_prompt(sents: list[str], name: str) -> tuple[str, str]:
    num = "\n".join(f"{i}. {s}" for i, s in enumerate(sents, 1))
    q, pre = EVID_Q["de"]
    return q.format(name=name, num=num), pre


# ---- flat schemes from a file (e.g. Bern's directorates, S6): options A.., last = none; title only
def flat_prompt(scheme: dict, title: str, lang: str) -> tuple[str, str, list[str]]:
    f = scheme["frame"][lang]
    opts = scheme["options"]
    codes = CODES_EXT[:len(opts) + 1]
    lines = [f"{codes[i]} = {o['abbr'][lang]} {o['name'][lang]}: {o['remit'][lang]}" for i, o in enumerate(opts)]
    lines.append(f"{codes[len(opts)]} = {scheme['none']['name'][lang]}")
    user = f"{f['ask']}\n\n{f['head']}:\n" + "\n".join(lines) + f"\n\n{f['item']}:\n{f['title']}: {title}\n\n{f['fmt']}"
    return user, '{"' + f["key"] + '": "', codes


# ---- named schemes from a file (a list of topic names, e.g. Basel-Stadt's own themes, S20): A–Z then a–z, last = none
CODES_NAMED = [chr(ord("A") + i) for i in range(26)] + [chr(ord("a") + i) for i in range(26)]


def named_perm(n: int) -> list[int]:
    p = list(range(n)); random.Random(7).shuffle(p)
    return p


def named_prompt(scheme: dict, a: dict, perm: list[int] | None = None,
                 examples: list[tuple[str, int]] | None = None) -> tuple[str, str, list[str]]:
    """perm[i] = the option (index into options + none) listed under code i; the input block as in the chapter step.
    `examples` = [(title, option index)] shown between list and item in the S9 D3 shape (S21)."""
    f = scheme["frame"]["de"]
    names = [o["name"]["de"] for o in scheme["options"]] + [scheme["none"]["name"]["de"]]
    perm = perm or list(range(len(names)))
    codes = CODES_NAMED[:len(names)]
    lines = "\n".join(f"{codes[i]} = {names[perm[i]]}" for i in range(len(names)))
    ex = ""
    if examples:
        inv = {perm[i]: i for i in range(len(names))}
        ex = f"{EX_HEAD}\n" + "\n".join(f"- {ti}\n  → Thema: {codes[inv[c]]} ({names[c]})" for ti, c in examples) + "\n\n"
    user = f"{f['ask']}\n\n{f['head']}:\n{lines}\n\n{ex}Geschäft:\n{affair_block(a, 'de')}\n\n{f['fmt']}"
    return user, '{"' + f["key"] + '": "', codes


# ---- verification for ad-hoc flags (S27): is the topic central, not just touched on or merely similar?
VERIFY = {"de": ("Ist «{name}» ein zentrales Thema dieses Geschäfts – nicht nur am Rande erwähnt oder bloss ähnlich?", "Ja, zentral", "Nein"),
          "fr": ("« {name} » est-il un thème central de cet objet – et non seulement mentionné en passant ou simplement voisin ?", "Oui, central", "Non"),
          "it": ("«{name}» è un tema centrale di questo oggetto – non solo menzionato di passaggio o semplicemente affine?", "Sì, centrale", "No")}


def verify_prompt(topic: dict, lang: str, title: str, title_long: str, order: str = "a") -> tuple[str, str]:
    item, ti, tl, _no, fmt, key = YN[lang]
    q, yes, no = VERIFY[lang]
    q = q.format(name=topic["names"][lang])
    opts = [("A", yes), ("B", no)] if order == "a" else [("A", no), ("B", yes)]
    blk = f"{ti}: {title[:400]}" + (f"\n{tl}: {title_long[:400]}" if title_long and title_long != title else "")
    u = f"{q}\n\n" + "\n".join(f"{c} = {s}" for c, s in opts) + f"\n\n{item}:\n{blk}\n\n{fmt}"
    return u, '{"' + key + '": "'


# ---- scope check for ad-hoc flags (S30): the topic with a generated include / exclude list (adhoc.SCOPE_PROMPT, stored in the
# topic file as `include` / `exclude` per language); asked on flags together with the S27 check, a flag is verified only if
# both say yes. Topics without these fields (Digitalisierung, the S19 files) never ask it.
SCOPE_CHECK = {
 "de": dict(incl="Dazu gehört:", excl="Nicht dazu gehört:", untitled="Geschäfte, deren Titel das Thema nicht erkennen lässt",
            ask="Gehört das folgende parlamentarische Geschäft zum Thema «{name}»?", yes="Ja, das Geschäft gehört zum Thema «{name}»"),
 "fr": dict(incl="En font partie :", excl="N'en font pas partie :", untitled="objets dont le titre ne laisse pas reconnaître le thème",
            ask="L'objet parlementaire suivant relève-t-il du thème « {name} » ?", yes="Oui, l'objet relève du thème « {name} »"),
 "it": dict(incl="Ne fanno parte:", excl="Non ne fanno parte:", untitled="oggetti il cui titolo non lascia riconoscere il tema",
            ask="Il seguente oggetto parlamentare rientra nel tema «{name}»?", yes="Sì, l'oggetto rientra nel tema «{name}»"),
}


def has_scope_check(topic: dict) -> bool:
    """True when flags of this topic get the S30 scope check (a verified topic with a generated include/exclude list)."""
    return bool(topic.get("verify")) and bool(topic.get("include") or topic.get("exclude"))


def scope_check_prompt(topic: dict, lang: str, title: str, title_long: str, order: str = "a") -> tuple[str, str]:
    """S30 (eval/s30/common.scope_prompt, byte-identical): «does the affair belong to «name»?», the include line, the
    exclude line ending in «affairs whose title does not show the topic», A/B as in the yes/no step."""
    item, ti, tl, no, fmt, key = YN[lang]
    f = SCOPE_CHECK[lang]; nm = topic["names"][lang]
    inc = (topic.get("include") or {}).get(lang) or (topic.get("include") or {}).get("de") or ""
    exc = (topic.get("exclude") or {}).get(lang) or (topic.get("exclude") or {}).get("de") or ""
    exc = (exc.rstrip(" .;,") + ", " if exc else "") + f["untitled"]
    lines = (f"{f['incl']} {inc.rstrip(' .')}.\n" if inc else "") + f"{f['excl']} {exc}."
    yes = f["yes"].format(name=nm)
    opts = [("A", yes), ("B", no)] if order == "a" else [("A", no), ("B", yes)]
    blk = f"{ti}: {title[:400]}" + (f"\n{tl}: {title_long[:400]}" if title_long and title_long != title else "")
    u = f"{f['ask'].format(name=nm)}\n{lines}\n\n" + "\n".join(f"{c} = {s}" for c, s in opts) + f"\n\n{item}:\n{blk}\n\n{fmt}"
    return u, '{"' + key + '": "'
