"""유튜브 영상의 자막과 메타데이터를 가져오는 어댑터.

`youtube-transcript-api` 와 `yt-dlp` 는 선택적(optional) 의존성이다.
설치되어 있지 않으면 실제 네트워크 수집 시점에만 에러를 내고, 이 모듈을
import 하거나 나머지 파이프라인(청킹/증류/저장/검색)을 테스트하는 데는
아무 지장이 없도록 만든다 (샌드박스/CI 환경에서도 나머지 로직은 검증 가능).
"""

from __future__ import annotations

import re
from typing import Optional

from .base import Fetched

_VIDEO_ID_PATTERNS = [
    re.compile(r"(?:v=|/videos/|embed/|youtu\.be/|/v/|/shorts/)([A-Za-z0-9_-]{11})"),
]


def extract_video_id(ref: str) -> str:
    """URL 또는 순수 video id 문자열에서 11자리 유튜브 video id를 뽑아낸다."""
    ref = ref.strip()
    if re.fullmatch(r"[A-Za-z0-9_-]{11}", ref):
        return ref
    for pattern in _VIDEO_ID_PATTERNS:
        m = pattern.search(ref)
        if m:
            return m.group(1)
    raise ValueError(f"유튜브 video id를 인식할 수 없습니다: {ref}")


class YouTubeAdapter:
    def fetch(self, ref: str) -> Fetched:
        video_id = extract_video_id(ref)
        text = self._fetch_transcript(video_id)
        title, channel = self._fetch_metadata(video_id)
        return Fetched(
            type="youtube",
            url=f"https://www.youtube.com/watch?v={video_id}",
            title=title,
            author_or_channel=channel,
            text=text,
        )

    def _fetch_transcript(self, video_id: str) -> str:
        try:
            from youtube_transcript_api import YouTubeTranscriptApi
        except ImportError as e:
            raise RuntimeError(
                "youtube-transcript-api 가 설치되어 있지 않습니다. "
                "`pip install youtube-transcript-api` 후 다시 시도하세요."
            ) from e

        transcript = YouTubeTranscriptApi.get_transcript(
            video_id, languages=["ko", "en"]
        )
        return " ".join(seg["text"] for seg in transcript if seg.get("text"))

    def _fetch_metadata(self, video_id: str) -> tuple[str, str]:
        try:
            import yt_dlp
        except ImportError:
            # 메타데이터는 부가 정보이므로, 못 가져와도 파이프라인 전체를
            # 막지 않고 video_id를 제목 대신 사용한다.
            return video_id, ""

        opts = {"quiet": True, "skip_download": True, "no_warnings": True}
        with yt_dlp.YoutubeDL(opts) as ydl:
            info = ydl.extract_info(
                f"https://www.youtube.com/watch?v={video_id}", download=False
            )
        return info.get("title", video_id), info.get("uploader", "")
