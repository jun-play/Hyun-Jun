"""ylearn CLI.

사용 예:
    python -m ylearn.cli ingest --youtube "https://youtu.be/XXXXXXXXXXX"
    python -m ylearn.cli ingest --text "책 제목|저자|본문 발췌..."
    python -m ylearn.cli ask "회계사 개업하려면 뭐부터 준비해야 해?"
    python -m ylearn.cli domains
    python -m ylearn.cli stats
"""

from __future__ import annotations

import argparse
import sys

from .config import Settings, load_domains
from .ingest.text import TextAdapter
from .ingest.youtube import YouTubeAdapter
from .pipeline import Pipeline


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="ylearn")
    sub = parser.add_subparsers(dest="command", required=True)

    ingest_p = sub.add_parser("ingest", help="영상/텍스트를 수집해 조언 카드로 증류한다")
    src_group = ingest_p.add_mutually_exclusive_group(required=True)
    src_group.add_argument("--youtube", help="유튜브 URL 또는 video id")
    src_group.add_argument(
        "--text", help='텍스트 직접 입력: "제목|저자|본문" 형식, 또는 파일 경로'
    )

    ask_p = sub.add_parser("ask", help="질문에 대해 정제된 조언을 받는다")
    ask_p.add_argument("question")
    ask_p.add_argument("--top-k", type=int, default=5)
    ask_p.add_argument("--domain", default=None, help="특정 도메인 id로 필터링")

    sub.add_parser("domains", help="도메인 taxonomy 목록을 보여준다")
    sub.add_parser("stats", help="수집/증류 현황 통계를 보여준다")

    return parser


def main(argv=None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "domains":
        for d in load_domains():
            print(f"- {d.id}: {d.name_ko} ({d.name_en})")
            print(f"    {d.description}")
        return 0

    settings = Settings.from_env()

    with Pipeline(settings=settings) as pipeline:
        if args.command == "ingest":
            if args.youtube:
                result = pipeline.ingest(YouTubeAdapter(), args.youtube)
            else:
                result = pipeline.ingest(TextAdapter(), args.text)

            if result.skipped_duplicate:
                print(f"이미 수집된 자료입니다: {result.source.title}")
            else:
                print(f"수집 완료: {result.source.title}")
                print(f"  청크 수: {result.n_chunks}")
                print(f"  조언 카드 수: {result.n_advice_cards}")
            return 0

        if args.command == "ask":
            result = pipeline.ask(args.question, top_k=args.top_k, domain=args.domain)
            print(result.answer)
            print()
            print(f"(참고한 조언 카드 {len(result.cards)}개)")
            return 0

        if args.command == "stats":
            stats = pipeline.store.stats()
            print(f"출처 수: {stats['sources']}")
            print(f"청크 수: {stats['chunks']}")
            print(f"조언 카드 수: {stats['advice_cards']}")
            print("도메인별 조언 카드 수:")
            for domain, count in stats["advice_by_domain"].items():
                print(f"  - {domain}: {count}")
            return 0

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
