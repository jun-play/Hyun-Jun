import unittest

import _pathfix  # noqa: F401

from ylearn.textutil import chunk_text, split_sentences, tokenize


class TestSplitSentences(unittest.TestCase):
    def test_basic(self):
        text = "이것은 첫 문장이다. 이것은 두번째 문장이다! 세번째는 물음표?"
        sentences = split_sentences(text)
        self.assertEqual(len(sentences), 3)

    def test_empty(self):
        self.assertEqual(split_sentences(""), [])
        self.assertEqual(split_sentences("   "), [])


class TestTokenize(unittest.TestCase):
    def test_removes_stopwords_and_short_tokens(self):
        tokens = tokenize("그리고 저는 회계사 개업을 하고 싶습니다")
        self.assertNotIn("그리고", tokens)
        self.assertIn("회계사", tokens)

    def test_lowercases_english(self):
        tokens = tokenize("Budget Planning is Important")
        self.assertIn("budget", tokens)
        self.assertNotIn("Budget", tokens)


class TestChunkText(unittest.TestCase):
    def test_short_text_single_chunk(self):
        text = "짧은 문장입니다. 두번째 문장."
        chunks = chunk_text(text, target_chars=900, overlap_chars=150)
        self.assertEqual(len(chunks), 1)

    def test_long_text_splits_into_multiple_chunks(self):
        sentence = "이 문장은 반복해서 길어지는 테스트용 문장입니다. "
        text = sentence * 100  # 충분히 길게 만든다
        chunks = chunk_text(text, target_chars=200, overlap_chars=50)
        self.assertGreater(len(chunks), 1)
        for c in chunks:
            self.assertLessEqual(len(c), 200 + len(sentence))

    def test_empty_text(self):
        self.assertEqual(chunk_text(""), [])


if __name__ == "__main__":
    unittest.main()
