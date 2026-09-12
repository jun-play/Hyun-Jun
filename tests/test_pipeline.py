import tempfile
import unittest
from pathlib import Path

import _pathfix  # noqa: F401

from ylearn.config import Settings
from ylearn.distill.llm import ExtractiveFallbackDistiller
from ylearn.ingest.text import TextAdapter
from ylearn.pipeline import Pipeline

ACCOUNTING_TEXT = (
    "회계사 개업을 하려면 먼저 사업계획서를 작성해야 합니다. "
    "초기 6개월 운영자금을 미리 확보해두는 것이 중요합니다. "
    "잠재 고객이 될 만한 소규모 사업체 네트워크를 미리 만들어두세요."
)

FAMILY_TEXT = (
    "가장으로서 행복한 가정을 만들려면 와이프와 매일 대화하는 시간을 가지세요. "
    "서로의 하루를 공유하는 습관이 관계를 단단하게 만듭니다. "
    "작은 감사 표현을 자주 하는 것이 좋다."
)


class TestPipelineEndToEnd(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        db_path = Path(self._tmpdir.name) / "pipeline_test.db"
        settings = Settings(db_path=db_path, anthropic_api_key="")
        self.pipeline = Pipeline(settings=settings, distiller=ExtractiveFallbackDistiller())

    def tearDown(self):
        self.pipeline.close()
        self._tmpdir.cleanup()

    def test_ingest_creates_chunks_and_advice_cards(self):
        result = self.pipeline.ingest(
            TextAdapter(), f"회계사 개업 가이드|어떤저자|{ACCOUNTING_TEXT}"
        )
        self.assertFalse(result.skipped_duplicate)
        self.assertGreaterEqual(result.n_chunks, 1)
        self.assertGreaterEqual(result.n_advice_cards, 1)

    def test_duplicate_ingest_is_skipped(self):
        ref = f"회계사 개업 가이드|어떤저자|{ACCOUNTING_TEXT}"
        first = self.pipeline.ingest(TextAdapter(), ref)
        second = self.pipeline.ingest(TextAdapter(), ref)
        self.assertFalse(first.skipped_duplicate)
        self.assertTrue(second.skipped_duplicate)
        self.assertEqual(first.source.id, second.source.id)

    def test_ask_retrieves_relevant_domain(self):
        self.pipeline.ingest(TextAdapter(), f"회계사 개업 가이드|저자1|{ACCOUNTING_TEXT}")
        self.pipeline.ingest(TextAdapter(), f"행복한 결혼생활|저자2|{FAMILY_TEXT}")

        result = self.pipeline.ask("회계사 개업하려면 뭐부터 준비해야 해?", top_k=3)
        self.assertTrue(result.cards)
        self.assertEqual(result.cards[0].domain, "career_professional")

    def test_ask_with_no_data_returns_guidance(self):
        result = self.pipeline.ask("아무 질문")
        self.assertIn("먼저", result.answer)
        self.assertEqual(result.cards, [])


if __name__ == "__main__":
    unittest.main()
