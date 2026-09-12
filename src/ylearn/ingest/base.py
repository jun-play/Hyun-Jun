"""수집(ingest) 어댑터 공통 인터페이스.

유튜브뿐 아니라 전자도서관/알라딘 같은 도서 자료도 결국 "제목 + 본문 텍스트"로
환원할 수 있으므로, 모든 어댑터는 이 인터페이스만 구현하면 동일한 파이프라인
(chunk -> distill -> store)에 그대로 태울 수 있다.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol


@dataclass
class Fetched:
    """어댑터가 반환하는, 아직 chunk로 나뉘지 않은 원시 수집 결과."""

    type: str  # "youtube" | "book" | "text"
    url: str
    title: str
    author_or_channel: str
    text: str


class SourceAdapter(Protocol):
    def fetch(self, ref: str) -> Fetched:
        """ref(URL, 파일 경로 등)로부터 원문 텍스트와 메타데이터를 가져온다."""
        ...
