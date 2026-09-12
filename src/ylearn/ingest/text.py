"""직접 붙여넣은 텍스트(책 발췌, 전자도서관/알라딘 요약 등)를 수집하는 어댑터.

전자도서관이나 알라딘은 저작권 때문에 자동 스크래핑이 어렵거나 바람직하지
않은 경우가 많다. 대신 사용자가 합법적으로 읽은 내용의 요약/발췌를 직접
붙여넣으면, 유튜브 자막과 동일한 파이프라인(chunk -> distill -> store)으로
처리한다. `ref`는 "제목|저자|본문" 형식의 문자열이거나, 로컬 텍스트 파일 경로다.
"""

from __future__ import annotations

from pathlib import Path

from .base import Fetched


class TextAdapter:
    def fetch(self, ref: str) -> Fetched:
        if self._looks_like_file_path(ref) and Path(ref).is_file():
            path = Path(ref)
            text = path.read_text(encoding="utf-8")
            title = path.stem
            author = ""
        else:
            title, author, text = self._parse_inline(ref)

        return Fetched(
            type="book",
            url=str(ref),
            title=title,
            author_or_channel=author,
            text=text,
        )

    @staticmethod
    def _looks_like_file_path(ref: str) -> bool:
        # "제목|저자|본문" 형식(긴 자유 텍스트, '|' 포함, 개행 포함)은 파일 경로일 수
        # 없으므로 os.stat까지 가지 않고 먼저 걸러낸다 (긴 문자열은 OSError를 낸다).
        return "|" not in ref and "\n" not in ref and len(ref) < 255

    @staticmethod
    def _parse_inline(ref: str) -> tuple[str, str, str]:
        parts = ref.split("|", 2)
        if len(parts) == 3:
            title, author, text = parts
        elif len(parts) == 2:
            title, text = parts
            author = ""
        else:
            title, author, text = "(제목 없음)", "", ref
        return title.strip(), author.strip(), text.strip()
