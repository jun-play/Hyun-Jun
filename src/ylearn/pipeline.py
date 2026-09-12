"""전체 파이프라인 오케스트레이션: 수집 -> 청킹 -> 증류 -> 저장 / 검색 -> 종합."""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional

from .config import Domain, Settings, load_domains
from .distill.llm import Distiller, make_default_distiller
from .ingest.base import SourceAdapter
from .models import AdviceCard, Source
from .retrieval import TfidfIndex
from .store import Store
from .textutil import chunk_text


@dataclass
class IngestResult:
    source: Source
    n_chunks: int
    n_advice_cards: int
    skipped_duplicate: bool = False


@dataclass
class AskResult:
    answer: str
    cards: List[AdviceCard]


class Pipeline:
    def __init__(
        self,
        settings: Optional[Settings] = None,
        store: Optional[Store] = None,
        distiller: Optional[Distiller] = None,
        domains: Optional[List[Domain]] = None,
    ):
        self.settings = settings or Settings.from_env()
        self.store = store or Store(self.settings.db_path)
        self.distiller = distiller or make_default_distiller(self.settings)
        self.domains = domains or load_domains(self.settings.domains_path)

    def close(self) -> None:
        self.store.close()

    def __enter__(self) -> "Pipeline":
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    # -- ingest ------------------------------------------------------------
    def ingest(self, adapter: SourceAdapter, ref: str) -> IngestResult:
        existing = self.store.find_source_by_url(ref)
        if existing:
            return IngestResult(
                source=existing,
                n_chunks=len(self.store.list_chunks(existing.id)),
                n_advice_cards=len(
                    [c for c in self.store.list_advice_cards() if c.source_id == existing.id]
                ),
                skipped_duplicate=True,
            )

        fetched = adapter.fetch(ref)

        source = Source.new(
            type=fetched.type,
            url=fetched.url,
            title=fetched.title,
            author_or_channel=fetched.author_or_channel,
        )
        # url이 정규화되어 바뀌었을 수 있으니(예: video id -> full url) 다시 확인.
        existing = self.store.find_source_by_url(source.url)
        if existing:
            return IngestResult(
                source=existing,
                n_chunks=len(self.store.list_chunks(existing.id)),
                n_advice_cards=len(
                    [c for c in self.store.list_advice_cards() if c.source_id == existing.id]
                ),
                skipped_duplicate=True,
            )

        self.store.add_source(source)

        pieces = chunk_text(
            fetched.text,
            target_chars=self.settings.chunk_target_chars,
            overlap_chars=self.settings.chunk_overlap_chars,
        )

        n_advice = 0
        for order, piece in enumerate(pieces):
            chunk = _make_chunk(source.id, order, piece)
            self.store.add_chunk(chunk)

            result = self.distiller.distill(piece, self.domains)
            if not result.summary and not result.action_items:
                continue
            card = AdviceCard.new(
                source_id=source.id,
                chunk_id=chunk.id,
                domain=result.domain,
                summary=result.summary,
                action_items=result.action_items,
                quote=result.quote,
                confidence=result.confidence,
            )
            self.store.add_advice_card(card)
            n_advice += 1

        return IngestResult(source=source, n_chunks=len(pieces), n_advice_cards=n_advice)

    # -- ask -----------------------------------------------------------------
    def ask(self, question: str, top_k: int = 5, domain: Optional[str] = None) -> AskResult:
        cards = self.store.list_advice_cards(domain=domain)
        if not cards:
            return AskResult(
                answer="아직 저장된 조언 카드가 없습니다. 먼저 영상/자료를 수집(ingest)하세요.",
                cards=[],
            )

        index = TfidfIndex()
        for card in cards:
            doc_text = f"{card.summary} {' '.join(card.action_items)} {card.quote}"
            index.add_document(card.id, doc_text)
        index.build()

        scored = index.search(question, top_k=top_k)
        card_by_id = {c.id: c for c in cards}
        matched = [card_by_id[s.doc_id] for s in scored if s.doc_id in card_by_id]

        if not matched:
            return AskResult(
                answer="질문과 관련된 조언을 찾지 못했습니다. 다른 표현으로 질문해보거나 "
                "관련 자료를 더 수집해보세요.",
                cards=[],
            )

        context = self._format_cards_context(matched)
        answer = self.distiller.synthesize(question, context)
        return AskResult(answer=answer, cards=matched)

    def _format_cards_context(self, cards: List[AdviceCard]) -> str:
        domain_names = {d.id: d.name_ko for d in self.domains}
        lines = []
        for i, card in enumerate(cards, start=1):
            source = self.store.get_source(card.source_id)
            source_label = source.title if source else card.source_id
            lines.append(
                f"[{i}] 도메인: {domain_names.get(card.domain, card.domain)} | 출처: {source_label}\n"
                f"    요약: {card.summary}\n"
                f"    행동: {', '.join(card.action_items) if card.action_items else '(없음)'}\n"
                f"    인용: \"{card.quote}\""
            )
        return "\n".join(lines)


def _make_chunk(source_id: str, order: int, text: str):
    from .models import Chunk

    return Chunk.new(source_id=source_id, order=order, text=text)
