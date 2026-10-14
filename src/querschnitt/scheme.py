"""Schemes are files: `schemes/*.yaml` (codes, names de/fr/it, hierarchy) and `schemes/adhoc/*.yaml` (one ad-hoc topic:
question with scope note and yes answer per language, cut-off, examples). No training step."""
from __future__ import annotations

import functools
import pathlib
import re

import yaml

HERE = pathlib.Path(__file__).resolve().parent / "schemes"


class Aps:
    """APS: 24 chapters × 190 subtopics + 'no policy topic' (index 24)."""

    def __init__(self, doc: dict):
        self.doc = doc
        ch = doc["chapters"]
        self.codes = [c["code"] for c in ch] + [doc["none"]["code"]]
        self.names = {l: [c["name"].get(l) for c in ch] + [doc["none"]["name"][l]] for l in ("de", "fr", "it")}
        self.chapter_names_de_with_none = self.names["de"]
        self.subs_de = {i: [s["name"]["de"] for s in c["subtopics"]] for i, c in enumerate(ch)}
        self.sub_codes = {i: [s["code"] for s in c["subtopics"]] for i, c in enumerate(ch)}
        self.sub_index = {s: (i, j) for i, l in self.sub_codes.items() for j, s in enumerate(l)}
        self.sub_name = {s["code"]: s["name"]["de"] for c in ch for s in c["subtopics"]}

    def short(self, i: int, lang: str = "de") -> str:
        """Chapter name; for 'none', the part before the parenthesis."""
        return re.sub(r"\s*\(.*\)$", "", self.names[lang][i])


APS = Aps(yaml.safe_load((HERE / "aps.yaml").read_text()))


@functools.lru_cache(maxsize=None)
def adhoc(slug: str) -> dict:
    p = HERE / "adhoc" / f"{slug}.yaml"
    return yaml.safe_load(p.read_text())


def adhoc_topics() -> list[str]:
    return sorted(p.stem for p in (HERE / "adhoc").glob("*.yaml"))


@functools.lru_cache(maxsize=None)
def flat(name: str) -> dict:
    return yaml.safe_load((HERE / f"{name}.yaml").read_text())


def named(name: str) -> dict:
    return flat(name)


def named_schemes() -> list[dict]:
    """Every named scheme file (topic names only) with the parliament it applies to (`body`)."""
    out = []
    for p in sorted(HERE.glob("*.yaml")):
        d = yaml.safe_load(p.read_text())
        if d.get("kind") == "named":
            out.append(d)
    return out
