import unittest

import _pathfix  # noqa: F401

from ylearn.ingest.youtube import extract_video_id


class TestExtractVideoId(unittest.TestCase):
    def test_watch_url(self):
        self.assertEqual(
            extract_video_id("https://www.youtube.com/watch?v=dQw4w9WgXcQ"),
            "dQw4w9WgXcQ",
        )

    def test_short_url(self):
        self.assertEqual(
            extract_video_id("https://youtu.be/dQw4w9WgXcQ"), "dQw4w9WgXcQ"
        )

    def test_shorts_url(self):
        self.assertEqual(
            extract_video_id("https://www.youtube.com/shorts/dQw4w9WgXcQ"),
            "dQw4w9WgXcQ",
        )

    def test_watch_url_with_extra_params(self):
        self.assertEqual(
            extract_video_id(
                "https://www.youtube.com/watch?v=dQw4w9WgXcQ&t=42s&list=PL123"
            ),
            "dQw4w9WgXcQ",
        )

    def test_bare_video_id(self):
        self.assertEqual(extract_video_id("dQw4w9WgXcQ"), "dQw4w9WgXcQ")

    def test_invalid_ref_raises(self):
        with self.assertRaises(ValueError):
            extract_video_id("not a youtube url")


if __name__ == "__main__":
    unittest.main()
