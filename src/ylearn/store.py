"""SQLite 기반 영속 저장소.

sources / chunks / advice_cards 세 테이블만으로 단순하게 구성한다.
외부 DB 서버 없이 파일 하나로 동작해야 개인 프로젝트로 부담 없이 쓸 수 있다.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import List, Optional

from .models import AdviceCard, Chunk, Source

SCHEMA = """
CREATE TABLE IF NOT EXISTS sources (
    id TEXT PRIMARY KEY,
    type TEXT NOT NULL,
    url TEXT NOT NULL,
    title TEXT NOT NULL,
    author_or_channel TEXT,
    fetched_at REAL NOT NULL
);

CREATE TABLE IF NOT EXISTS chunks (
    id TEXT PRIMARY KEY,
    source_id TEXT NOT NULL REFERENCES sources(id),
    "order" INTEGER NOT NULL,
    text TEXT NOT NULL,
    start_time_sec REAL
);

CREATE TABLE IF NOT EXISTS advice_cards (
    id TEXT PRIMARY KEY,
    source_id TEXT NOT NULL REFERENCES sources(id),
    chunk_id TEXT NOT NULL REFERENCES chunks(id),
    domain TEXT NOT NULL,
    summary TEXT NOT NULL,
    action_items TEXT NOT NULL,
    quote TEXT NOT NULL,
    confidence REAL NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_chunks_source ON chunks(source_id);
CREATE INDEX IF NOT EXISTS idx_advice_source ON advice_cards(source_id);
CREATE INDEX IF NOT EXISTS idx_advice_domain ON advice_cards(domain);
"""


class Store:
    def __init__(self, db_path: Path | str):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._conn = sqlite3.connect(str(self.db_path))
        self._conn.row_factory = sqlite3.Row
        self._conn.executescript(SCHEMA)
        self._conn.commit()

    def close(self) -> None:
        self._conn.close()

    def __enter__(self) -> "Store":
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    # -- sources -----------------------------------------------------
    def add_source(self, source: Source) -> None:
        self._conn.execute(
            "INSERT INTO sources (id, type, url, title, author_or_channel, fetched_at)"
            " VALUES (?, ?, ?, ?, ?, ?)",
            (
                source.id,
                source.type,
                source.url,
                source.title,
                source.author_or_channel,
                source.fetched_at,
            ),
        )
        self._conn.commit()

    def get_source(self, source_id: str) -> Optional[Source]:
        row = self._conn.execute(
            "SELECT * FROM sources WHERE id = ?", (source_id,)
        ).fetchone()
        return _row_to_source(row) if row else None

    def find_source_by_url(self, url: str) -> Optional[Source]:
        row = self._conn.execute(
            "SELECT * FROM sources WHERE url = ?", (url,)
        ).fetchone()
        return _row_to_source(row) if row else None

    def list_sources(self) -> List[Source]:
        rows = self._conn.execute("SELECT * FROM sources ORDER BY fetched_at DESC")
        return [_row_to_source(r) for r in rows]

    # -- chunks --------------------------------------------------------
    def add_chunk(self, chunk: Chunk) -> None:
        self._conn.execute(
            'INSERT INTO chunks (id, source_id, "order", text, start_time_sec)'
            " VALUES (?, ?, ?, ?, ?)",
            (chunk.id, chunk.source_id, chunk.order, chunk.text, chunk.start_time_sec),
        )
        self._conn.commit()

    def get_chunk(self, chunk_id: str) -> Optional[Chunk]:
        row = self._conn.execute(
            "SELECT * FROM chunks WHERE id = ?", (chunk_id,)
        ).fetchone()
        return _row_to_chunk(row) if row else None

    def list_chunks(self, source_id: Optional[str] = None) -> List[Chunk]:
        if source_id:
            rows = self._conn.execute(
                'SELECT * FROM chunks WHERE source_id = ? ORDER BY "order"',
                (source_id,),
            )
        else:
            rows = self._conn.execute('SELECT * FROM chunks ORDER BY "order"')
        return [_row_to_chunk(r) for r in rows]

    # -- advice cards ----------------------------------------------------
    def add_advice_card(self, card: AdviceCard) -> None:
        self._conn.execute(
            "INSERT INTO advice_cards"
            " (id, source_id, chunk_id, domain, summary, action_items, quote, confidence)"
            " VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            (
                card.id,
                card.source_id,
                card.chunk_id,
                card.domain,
                card.summary,
                json.dumps(card.action_items, ensure_ascii=False),
                card.quote,
                card.confidence,
            ),
        )
        self._conn.commit()

    def list_advice_cards(self, domain: Optional[str] = None) -> List[AdviceCard]:
        if domain:
            rows = self._conn.execute(
                "SELECT * FROM advice_cards WHERE domain = ?", (domain,)
            )
        else:
            rows = self._conn.execute("SELECT * FROM advice_cards")
        return [_row_to_advice(r) for r in rows]

    def get_advice_card(self, advice_id: str) -> Optional[AdviceCard]:
        row = self._conn.execute(
            "SELECT * FROM advice_cards WHERE id = ?", (advice_id,)
        ).fetchone()
        return _row_to_advice(row) if row else None

    def stats(self) -> dict:
        n_sources = self._conn.execute("SELECT COUNT(*) FROM sources").fetchone()[0]
        n_chunks = self._conn.execute("SELECT COUNT(*) FROM chunks").fetchone()[0]
        n_advice = self._conn.execute("SELECT COUNT(*) FROM advice_cards").fetchone()[
            0
        ]
        by_domain = dict(
            self._conn.execute(
                "SELECT domain, COUNT(*) FROM advice_cards GROUP BY domain"
            ).fetchall()
        )
        return {
            "sources": n_sources,
            "chunks": n_chunks,
            "advice_cards": n_advice,
            "advice_by_domain": by_domain,
        }


def _row_to_source(row: sqlite3.Row) -> Source:
    return Source(
        id=row["id"],
        type=row["type"],
        url=row["url"],
        title=row["title"],
        author_or_channel=row["author_or_channel"] or "",
        fetched_at=row["fetched_at"],
    )


def _row_to_chunk(row: sqlite3.Row) -> Chunk:
    return Chunk(
        id=row["id"],
        source_id=row["source_id"],
        order=row["order"],
        text=row["text"],
        start_time_sec=row["start_time_sec"],
    )


def _row_to_advice(row: sqlite3.Row) -> AdviceCard:
    return AdviceCard(
        id=row["id"],
        source_id=row["source_id"],
        chunk_id=row["chunk_id"],
        domain=row["domain"],
        summary=row["summary"],
        action_items=json.loads(row["action_items"]),
        quote=row["quote"],
        confidence=row["confidence"],
    )
