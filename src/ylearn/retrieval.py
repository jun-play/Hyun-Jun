"""외부 벡터DB/임베딩 라이브러리 없이 동작하는 TF-IDF 기반 검색기.

numpy/faiss/sentence-transformers 등은 설치가 무겁고, 이 프로젝트의 MVP
단계에서는 "질문과 관련된 조언 카드 top-k를 찾는다"는 목적만 충족하면
충분하다. 나중에 진짜 임베딩 기반 검색으로 바꾸고 싶다면 이 모듈의
인터페이스(TfidfIndex.build / .search)만 유지한 채 내부 구현을 교체하면 된다.
"""

from __future__ import annotations

import math
from collections import Counter, defaultdict
from dataclasses import dataclass
from typing import Dict, List, Tuple

from .textutil import tokenize


@dataclass
class ScoredDoc:
    doc_id: str
    score: float


class TfidfIndex:
    """메모리 상의 단순 TF-IDF 코사인 유사도 인덱스."""

    def __init__(self) -> None:
        self._doc_tokens: Dict[str, List[str]] = {}
        self._doc_term_freq: Dict[str, Counter] = {}
        self._df: Counter = Counter()
        self._idf: Dict[str, float] = {}
        self._doc_norm: Dict[str, float] = {}
        self._built = False

    def add_document(self, doc_id: str, text: str) -> None:
        tokens = tokenize(text)
        self._doc_tokens[doc_id] = tokens
        self._built = False

    def remove_document(self, doc_id: str) -> None:
        self._doc_tokens.pop(doc_id, None)
        self._built = False

    def build(self) -> None:
        self._doc_term_freq = {}
        self._df = Counter()

        for doc_id, tokens in self._doc_tokens.items():
            tf = Counter(tokens)
            self._doc_term_freq[doc_id] = tf
            for term in tf.keys():
                self._df[term] += 1

        n_docs = max(len(self._doc_tokens), 1)
        self._idf = {
            term: math.log((n_docs + 1) / (df + 1)) + 1.0
            for term, df in self._df.items()
        }

        self._doc_norm = {}
        for doc_id, tf in self._doc_term_freq.items():
            norm = math.sqrt(
                sum((tf[term] * self._idf.get(term, 0.0)) ** 2 for term in tf)
            )
            self._doc_norm[doc_id] = norm or 1.0

        self._built = True

    def search(self, query: str, top_k: int = 5) -> List[ScoredDoc]:
        if not self._built:
            self.build()

        query_tokens = tokenize(query)
        if not query_tokens:
            return []

        query_tf = Counter(query_tokens)
        query_vec = {
            term: query_tf[term] * self._idf.get(term, 0.0) for term in query_tf
        }
        query_norm = math.sqrt(sum(v * v for v in query_vec.values())) or 1.0

        scores: List[Tuple[str, float]] = []
        for doc_id, tf in self._doc_term_freq.items():
            dot = 0.0
            for term, qw in query_vec.items():
                if term in tf:
                    dot += qw * (tf[term] * self._idf.get(term, 0.0))
            if dot <= 0:
                continue
            score = dot / (query_norm * self._doc_norm[doc_id])
            scores.append((doc_id, score))

        scores.sort(key=lambda x: x[1], reverse=True)
        return [ScoredDoc(doc_id=d, score=s) for d, s in scores[:top_k]]
