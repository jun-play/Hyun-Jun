import tempfile
import unittest
from pathlib import Path

import _pathfix  # noqa: F401

from ylearn.models import AdviceCard, Chunk, Source
from ylearn.store import Store


class TestStore(unittest.TestCase):
    def setUp(self):
        self._tmpdir = tempfile.TemporaryDirectory()
        self.db_path = Path(self._tmpdir.name) / "test.db"
        self.store = Store(self.db_path)

    def tearDown(self):
        self.store.close()
        self._tmpdir.cleanup()

    def test_add_and_get_source(self):
        source = Source.new(type="youtube", url="https://y/1", title="영상1")
        self.store.add_source(source)

        fetched = self.store.get_source(source.id)
        self.assertEqual(fetched.title, "영상1")

        by_url = self.store.find_source_by_url("https://y/1")
        self.assertEqual(by_url.id, source.id)

    def test_chunks_and_advice_cards_roundtrip(self):
        source = Source.new(type="text", url="book://1", title="책1")
        self.store.add_source(source)

        chunk = Chunk.new(source_id=source.id, order=0, text="본문 내용")
        self.store.add_chunk(chunk)

        card = AdviceCard.new(
            source_id=source.id,
            chunk_id=chunk.id,
            domain="money_management",
            summary="요약",
            action_items=["행동1", "행동2"],
            quote="인용문",
            confidence=0.7,
        )
        self.store.add_advice_card(card)

        chunks = self.store.list_chunks(source.id)
        self.assertEqual(len(chunks), 1)
        self.assertEqual(chunks[0].text, "본문 내용")

        cards = self.store.list_advice_cards(domain="money_management")
        self.assertEqual(len(cards), 1)
        self.assertEqual(cards[0].action_items, ["행동1", "행동2"])

    def test_stats(self):
        source = Source.new(type="text", url="book://2", title="책2")
        self.store.add_source(source)
        chunk = Chunk.new(source_id=source.id, order=0, text="내용")
        self.store.add_chunk(chunk)
        card = AdviceCard.new(
            source_id=source.id,
            chunk_id=chunk.id,
            domain="happiness_wellbeing",
            summary="요약",
            action_items=[],
            quote="인용",
            confidence=0.5,
        )
        self.store.add_advice_card(card)

        stats = self.store.stats()
        self.assertEqual(stats["sources"], 1)
        self.assertEqual(stats["chunks"], 1)
        self.assertEqual(stats["advice_cards"], 1)
        self.assertEqual(stats["advice_by_domain"]["happiness_wellbeing"], 1)


if __name__ == "__main__":
    unittest.main()
