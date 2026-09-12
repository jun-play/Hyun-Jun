"""LLM(Claude) 증류/종합 단계에서 쓰는 프롬프트 템플릿."""

from __future__ import annotations

from typing import List

from ..config import Domain

DISTILL_SYSTEM_PROMPT = """\
당신은 유튜브/도서에서 나온 원문 조각을 읽고, 실제로 삶에 적용할 수 있는
"정제된 조언"으로 증류하는 편집자입니다. 과장하지 말고, 원문에 실제로 있는
내용만 근거로 삼으세요. 없는 내용을 지어내지 마세요.
반드시 아래 JSON 형식으로만 답하세요 (다른 텍스트 없이):

{
  "domain": "<주어진 도메인 id 중 하나>",
  "summary": "<한두 문장 요약, 한국어>",
  "action_items": ["<바로 실행 가능한 행동 1>", "<행동 2>", ...],
  "quote": "<원문에서 그대로 가져온 핵심 문장 1개>",
  "confidence": <0.0~1.0 사이 숫자, 이 조각이 실제로 유용한 조언을 담고 있다는 확신도>
}
"""


def build_distill_user_prompt(chunk_text: str, domains: List[Domain]) -> str:
    domain_list = "\n".join(f"- {d.id}: {d.name_ko} ({d.description})" for d in domains)
    return f"""다음은 도메인 목록입니다:
{domain_list}

아래 원문 조각을 위 형식에 맞춰 증류해 주세요. 이 조각이 어느 도메인에도
분명하게 맞지 않으면 confidence를 낮게 주세요.

원문 조각:
\"\"\"
{chunk_text}
\"\"\"
"""


SYNTHESIZE_SYSTEM_PROMPT = """\
당신은 여러 출처(유튜브, 책)에서 뽑아낸 조언 카드들을 바탕으로, 사용자의
질문에 대해 정제되고 실행 가능한 답을 종합해주는 조언자입니다.
- 주어진 조언 카드에 실제로 있는 내용만 사용하세요.
- 여러 카드가 겹치는 조언을 하면 통합해서 제시하세요.
- 마지막에 어떤 출처(source title)를 참고했는지 나열하세요.
- 한국어로, 실행 가능한 bullet 형태로 답하세요.
"""


def build_synthesize_user_prompt(question: str, cards_context: str) -> str:
    return f"""사용자 질문: {question}

참고할 조언 카드들:
{cards_context}

위 조언 카드들만 근거로 답변을 작성해주세요.
"""
