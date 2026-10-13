"""Labelled examples: the five most similar affairs with a known label, retrieved by BM25 over titles (S9 D3).
The APS pool is the federal affairs whose APS editors' chapter was recovered (S9 + ideation-1 S5 items)."""
from __future__ import annotations

import collections
import json
import math
import re
from pathlib import Path

TOK = re.compile(r"\w+")
STOP = set("der die das und oder für von mit des den dem ein eine einer eines zur zum auf aus bei nach über unter vom "
           "les des une pour par sur aux dans avec est que qui son ses leur "
           "della delle degli dei per con nel nella sul sulla che una gli alla allo".split())


def toks(s: str | None) -> list[str]:
    return [w for w in TOK.findall((s or "").lower()) if len(w) >= 3 and w not in STOP and not w.isdigit()]


class BM25:
    def __init__(self, docs: list[list[str]], k1: float = 1.2, b: float = 0.75):
        self.docs, self.N, self.k1, self.b = docs, len(docs), k1, b
        self.len = [len(d) for d in docs]
        self.avg = (sum(self.len) / self.N) if self.N else 1
        self.inv = collections.defaultdict(list)
        for j, d in enumerate(docs):
            for w, c in collections.Counter(d).items():
                self.inv[w].append((j, c))
        self.idf = {w: math.log(1 + (self.N - len(p) + 0.5) / (len(p) + 0.5)) for w, p in self.inv.items()}

    def top(self, q: list[str], k: int) -> list[tuple[int, float]]:
        sc = collections.defaultdict(float)
        for w in set(q):
            for j, c in self.inv.get(w, ()):
                sc[j] += self.idf[w] * c * (self.k1 + 1) / (c + self.k1 * (1 - self.b + self.b * self.len[j] / self.avg))
        return sorted(sc.items(), key=lambda x: -x[1])[:k]


class ExamplePool:
    """pool rows: {oid, title, chapter (index 0..24)}"""

    def __init__(self, pool: list[dict], k: int = 5):
        self.pool, self.k = pool, k
        self.bm = BM25([toks(x["title"]) for x in pool])

    @classmethod
    def load(cls, path: str | Path, k: int = 5) -> "ExamplePool":
        return cls([json.loads(l) for l in open(path) if l.strip()], k)

    def neighbours(self, a: dict) -> list[dict]:
        q = toks(a["title"]) * 2 + toks((a.get("text") or "")[:400])
        hits = [j for j, _ in self.bm.top(q, self.k + 6) if self.pool[j]["oid"] != a["id"]][: self.k]
        return [self.pool[j] for j in hits]

    def add(self, row: dict):
        """An editor's confirmed decision becomes an example (pool rebuilt; small pools only)."""
        self.pool.append(row)
        self.bm = BM25([toks(x["title"]) for x in self.pool])
