"""파이프라인 전체에서 공유하는 데이터 모델."""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from typing import List, Optional


def _new_id(prefix: str) -> str:
    return f"{prefix}_{uuid.uuid4().hex[:12]}"


@dataclass
class Source:
    """수집 대상 원천 (유튜브 영상, 책 발췌 등)."""

    id: str
    type: str  # "youtube" | "book" | "text"
    url: str
    title: str
    author_or_channel: str = ""
    fetched_at: float = field(default_factory=time.time)

    @staticmethod
    def new(
        type: str, url: str, title: str, author_or_channel: str = ""
    ) -> "Source":
        return Source(
            id=_new_id("src"),
            type=type,
            url=url,
            title=title,
            author_or_channel=author_or_channel,
        )


@dataclass
class Chunk:
    """원천 텍스트를 일정 길이로 자른 조각."""

    id: str
    source_id: str
    order: int
    text: str
    start_time_sec: Optional[float] = None

    @staticmethod
    def new(
        source_id: str, order: int, text: str, start_time_sec: Optional[float] = None
    ) -> "Chunk":
        return Chunk(
            id=_new_id("chk"),
            source_id=source_id,
            order=order,
            text=text,
            start_time_sec=start_time_sec,
        )


@dataclass
class AdviceCard:
    """하나의 chunk에서 증류(distill)된, 실제로 재사용 가능한 조언 단위."""

    id: str
    source_id: str
    chunk_id: str
    domain: str
    summary: str
    action_items: List[str]
    quote: str
    confidence: float  # 0.0 ~ 1.0, distiller의 자체 판단 신뢰도

    @staticmethod
    def new(
        source_id: str,
        chunk_id: str,
        domain: str,
        summary: str,
        action_items: List[str],
        quote: str,
        confidence: float,
    ) -> "AdviceCard":
        return AdviceCard(
            id=_new_id("adv"),
            source_id=source_id,
            chunk_id=chunk_id,
            domain=domain,
            summary=summary,
            action_items=action_items,
            quote=quote,
            confidence=confidence,
        )
