"""원문 조각(chunk)을 "정제된 조언"으로 증류하는 두 가지 구현.

- AnthropicDistiller: Claude API를 호출해 실제 의미 이해 기반으로 증류한다.
  (ANTHROPIC_API_KEY 필요, `pip install anthropic` 필요)
- ExtractiveFallbackDistiller: 외부 API/의존성 없이 규칙 기반으로 동작한다.
  키가 없거나 오프라인 환경(테스트, 초기 개발)에서도 파이프라인 전체가
  end-to-end로 돌아가게 하기 위한 기본값이다.

두 구현 모두 같은 Distiller 인터페이스(distill, synthesize)를 따르므로
pipeline.py는 어떤 구현이 쓰이는지 신경 쓰지 않는다.
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from typing import List, Protocol

from ..config import Domain
from ..models import AdviceCard
from ..textutil import split_sentences, tokenize
from .prompts import (
    DISTILL_SYSTEM_PROMPT,
    SYNTHESIZE_SYSTEM_PROMPT,
    build_distill_user_prompt,
    build_synthesize_user_prompt,
)


@dataclass
class DistillResult:
    domain: str
    summary: str
    action_items: List[str]
    quote: str
    confidence: float


class Distiller(Protocol):
    def distill(self, chunk_text: str, domains: List[Domain]) -> DistillResult: ...

    def synthesize(self, question: str, cards_context: str) -> str: ...


_ACTION_HINT_RE = re.compile(
    r"(하세요|하자|해야|하십시오|합시다|것이 좋다|것이 중요|필요하다|해보세요)$"
)


class ExtractiveFallbackDistiller:
    """LLM 없이 동작하는 규칙 기반 distiller. 정확도는 낮지만 항상 동작한다."""

    def distill(self, chunk_text: str, domains: List[Domain]) -> DistillResult:
        sentences = split_sentences(chunk_text)
        if not sentences:
            return DistillResult(
                domain=domains[0].id if domains else "unknown",
                summary="",
                action_items=[],
                quote="",
                confidence=0.0,
            )

        domain_id, confidence = self._classify_domain(chunk_text, domains)
        summary = " ".join(sentences[:2])
        action_items = self._extract_action_items(sentences)
        quote = max(sentences, key=len)

        return DistillResult(
            domain=domain_id,
            summary=summary,
            action_items=action_items,
            quote=quote,
            confidence=confidence,
        )

    def synthesize(self, question: str, cards_context: str) -> str:
        # LLM 없이도 최소한의 답을 준다: 검색된 카드 요약을 그대로 나열.
        lines = [f"(규칙 기반 요약 — ANTHROPIC_API_KEY가 없어 LLM 종합을 건너뜁니다)"]
        lines.append(f"질문: {question}")
        lines.append("")
        lines.append(cards_context)
        return "\n".join(lines)

    @staticmethod
    def _classify_domain(text: str, domains: List[Domain]) -> tuple[str, float]:
        text_lower = text.lower()
        best_domain = domains[0].id if domains else "unknown"
        best_score = 0
        for domain in domains:
            score = sum(1 for kw in domain.keywords if kw.lower() in text_lower)
            if score > best_score:
                best_score = score
                best_domain = domain.id
        confidence = min(0.3 + 0.15 * best_score, 0.9) if best_score else 0.2
        return best_domain, confidence

    @staticmethod
    def _extract_action_items(sentences: List[str]) -> List[str]:
        hinted = [s for s in sentences if _ACTION_HINT_RE.search(s.strip())]
        if hinted:
            return hinted[:3]
        # 힌트가 없으면 토큰 수가 많은(정보량이 많아 보이는) 문장을 대신 쓴다.
        ranked = sorted(sentences, key=lambda s: len(tokenize(s)), reverse=True)
        return ranked[:2]


class AnthropicDistiller:
    """Claude API를 사용하는 실제 증류/종합 구현."""

    def __init__(self, api_key: str, model: str = "claude-sonnet-5"):
        try:
            import anthropic
        except ImportError as e:
            raise RuntimeError(
                "anthropic 패키지가 설치되어 있지 않습니다. "
                "`pip install anthropic` 후 다시 시도하세요."
            ) from e
        if not api_key:
            raise RuntimeError("ANTHROPIC_API_KEY가 설정되어 있지 않습니다.")
        self._client = anthropic.Anthropic(api_key=api_key)
        self._model = model

    def distill(self, chunk_text: str, domains: List[Domain]) -> DistillResult:
        response = self._client.messages.create(
            model=self._model,
            max_tokens=600,
            system=DISTILL_SYSTEM_PROMPT,
            messages=[
                {
                    "role": "user",
                    "content": build_distill_user_prompt(chunk_text, domains),
                }
            ],
        )
        raw = "".join(
            block.text for block in response.content if getattr(block, "type", "") == "text"
        )
        data = _parse_json_object(raw)
        return DistillResult(
            domain=data.get("domain", domains[0].id if domains else "unknown"),
            summary=data.get("summary", ""),
            action_items=list(data.get("action_items", [])),
            quote=data.get("quote", ""),
            confidence=float(data.get("confidence", 0.5)),
        )

    def synthesize(self, question: str, cards_context: str) -> str:
        response = self._client.messages.create(
            model=self._model,
            max_tokens=800,
            system=SYNTHESIZE_SYSTEM_PROMPT,
            messages=[
                {
                    "role": "user",
                    "content": build_synthesize_user_prompt(question, cards_context),
                }
            ],
        )
        return "".join(
            block.text for block in response.content if getattr(block, "type", "") == "text"
        )


def _parse_json_object(raw: str) -> dict:
    """모델이 코드펜스(```json ... ```)를 붙이는 경우까지 관대하게 파싱한다."""
    text = raw.strip()
    if text.startswith("```"):
        text = re.sub(r"^```[a-zA-Z]*\n?", "", text)
        text = re.sub(r"\n?```$", "", text)
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        raise ValueError(f"LLM 응답에서 JSON을 찾을 수 없습니다: {raw!r}")
    return json.loads(match.group(0))


def make_default_distiller(settings) -> Distiller:
    """설정에 API 키가 있으면 AnthropicDistiller, 없으면 fallback을 반환한다."""
    if settings.anthropic_api_key:
        try:
            return AnthropicDistiller(settings.anthropic_api_key, settings.anthropic_model)
        except RuntimeError:
            pass
    return ExtractiveFallbackDistiller()
