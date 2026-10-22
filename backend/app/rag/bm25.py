"""BM25 (Okapi) over pythainlp word tokens. Thai has no spaces between words, so whitespace
tokenisation would treat a whole phrase as one token; newmm dictionary segmentation fixes that."""

import math
import re
from collections import Counter

from pythainlp.tokenize import word_tokenize

_KEEP = re.compile(r"[\wก-๙]")


def tokenize(text: str) -> list[str]:
    toks = word_tokenize(text.lower(), engine="newmm", keep_whitespace=False)
    return [t for t in toks if _KEEP.search(t)]


class BM25:
    def __init__(self, docs: list[list[str]], k1: float = 1.5, b: float = 0.75):
        self.k1, self.b = k1, b
        self.tf = [Counter(d) for d in docs]
        self.len = [len(d) for d in docs]
        self.avg = sum(self.len) / max(len(docs), 1)
        df = Counter(t for d in docs for t in set(d))
        n = len(docs)
        self.idf = {t: math.log(1 + (n - f + 0.5) / (f + 0.5)) for t, f in df.items()}

    def scores(self, query: list[str]) -> list[float]:
        out = []
        for tf, dl in zip(self.tf, self.len):
            s = 0.0
            for t in query:
                if t in tf:
                    f = tf[t]
                    s += self.idf[t] * f * (self.k1 + 1) / (f + self.k1 * (1 - self.b + self.b * dl / self.avg))
            out.append(s)
        return out
