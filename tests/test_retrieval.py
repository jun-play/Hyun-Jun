import unittest

import _pathfix  # noqa: F401

from ylearn.retrieval import TfidfIndex


class TestTfidfIndex(unittest.TestCase):
    def setUp(self):
        self.index = TfidfIndex()
        self.index.add_document("d1", "회계사 개업을 위해서는 사업계획서와 자금 준비가 필요하다")
        self.index.add_document("d2", "와이프와 행복한 결혼 생활을 위해서는 대화가 중요하다")
        self.index.add_document("d3", "가계부를 써서 지출을 관리하면 저축을 늘릴 수 있다")
        self.index.build()

    def test_search_returns_most_relevant_doc_first(self):
        results = self.index.search("회계사 개업 준비 어떻게 해야 하나요", top_k=3)
        self.assertTrue(results)
        self.assertEqual(results[0].doc_id, "d1")

    def test_search_respects_top_k(self):
        results = self.index.search("결혼 생활", top_k=1)
        self.assertEqual(len(results), 1)

    def test_empty_query_returns_empty(self):
        results = self.index.search("", top_k=3)
        self.assertEqual(results, [])

    def test_remove_document_excludes_it_from_results(self):
        self.index.remove_document("d1")
        self.index.build()
        results = self.index.search("회계사 개업", top_k=3)
        ids = [r.doc_id for r in results]
        self.assertNotIn("d1", ids)


if __name__ == "__main__":
    unittest.main()
