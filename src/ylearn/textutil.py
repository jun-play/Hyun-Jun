"""외부 의존성 없이 동작하는 텍스트 유틸: 토크나이즈, 문장 분리, 청킹.

한국어 형태소 분석기(예: KoNLPy, mecab)는 설치가 무겁고 환경마다 실패하기
쉬우므로, MVP 단계에서는 공백/구두점 기반의 단순 토크나이저로 대체한다.
정확도보다 "의존성 없이 어디서나 동작하는 것"을 우선한다.
"""

from __future__ import annotations

import re
from typing import List

_SENTENCE_SPLIT_RE = re.compile(r"(?<=[.!?。!?\n])\s+")
_TOKEN_RE = re.compile(r"[0-9A-Za-z가-힣]+")

_STOPWORDS = {
    "그리고", "그래서", "하지만", "그런데", "이제", "그냥", "이거", "그거",
    "저는", "제가", "그니까", "그러니까", "약간", "진짜", "이런", "저런",
    "the", "a", "an", "is", "are", "and", "or", "of", "to", "in",
}

# 형태소 분석기 없이 "회계사"/"회계사로"/"회계사를" 같은 조사 변형을
# 최대한 같은 토큰으로 모으기 위한 아주 단순한 접미사 제거 규칙.
# 완벽하지 않다(예: "국가"의 "가"를 조사로 오인할 수 있음)는 것을 알고
# 쓰는 트레이드오프이며, 그래서 stripping 후 길이가 2 미만이 되면 원래
# 토큰을 그대로 둔다 — 2음절 이하 단어를 뭉개는 사고를 막기 위함이다.
_MULTI_JOSA = [
    "으로부터", "로부터", "에게서", "한테서",
    "이라는", "라는", "에서", "한테", "까지", "부터",
    "이나", "라도", "이라", "로서", "로써", "으로", "에게",
]
_SINGLE_JOSA = ["은", "는", "이", "가", "을", "를", "의", "에", "도", "만", "로", "와", "과", "나", "랑"]


def _strip_josa(token: str) -> str:
    for josa in _MULTI_JOSA:
        if token.endswith(josa) and len(token) - len(josa) >= 2:
            return token[: -len(josa)]
    for josa in _SINGLE_JOSA:
        if token.endswith(josa) and len(token) - len(josa) >= 2:
            return token[: -len(josa)]
    return token


def split_sentences(text: str) -> List[str]:
    """아주 단순한 규칙 기반 문장 분리기 (마침표/느낌표/물음표/개행 기준)."""
    text = text.strip()
    if not text:
        return []
    parts = _SENTENCE_SPLIT_RE.split(text)
    return [p.strip() for p in parts if p.strip()]


def tokenize(text: str) -> List[str]:
    """소문자화 + 한글/영문/숫자 토큰 추출 + 조사 제거(근사치) + 불용어 제거."""
    raw = [t.lower() for t in _TOKEN_RE.findall(text)]
    tokens = [_strip_josa(t) for t in raw]
    return [t for t in tokens if t not in _STOPWORDS and len(t) > 1]


def chunk_text(
    text: str, target_chars: int = 900, overlap_chars: int = 150
) -> List[str]:
    """문장 경계를 최대한 지키면서 target_chars 근처 길이로 텍스트를 자른다.

    긴 유튜브 자막 전체를 한 번에 LLM에 넣지 않고, 의미 단위(문장)를 지키는
    선에서 적당한 크기로 나눠 distill 단계와 검색 단계 모두에 쓴다.
    """
    sentences = split_sentences(text)
    if not sentences:
        return []

    chunks: List[str] = []
    current: List[str] = []
    current_len = 0

    for sentence in sentences:
        if current_len + len(sentence) > target_chars and current:
            chunks.append(" ".join(current))
            # 겹치는 부분(overlap)을 만들어 문맥 단절을 줄인다.
            overlap: List[str] = []
            overlap_len = 0
            for s in reversed(current):
                if overlap_len >= overlap_chars:
                    break
                overlap.insert(0, s)
                overlap_len += len(s)
            current = overlap
            current_len = overlap_len

        current.append(sentence)
        current_len += len(sentence)

    if current:
        chunks.append(" ".join(current))

    return chunks
