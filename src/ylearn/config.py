"""전역 설정: 경로, 환경 변수, 도메인 taxonomy 로딩."""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List

import yaml

PROJECT_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_DOMAINS_PATH = PROJECT_ROOT / "data" / "domains.yaml"
DEFAULT_DB_PATH = PROJECT_ROOT / "data" / "ylearn.db"


@dataclass(frozen=True)
class Domain:
    id: str
    name_ko: str
    name_en: str
    description: str
    keywords: List[str] = field(default_factory=list)


def load_domains(path: Path = DEFAULT_DOMAINS_PATH) -> List[Domain]:
    """domains.yaml 을 읽어 Domain 객체 리스트로 반환한다."""
    if not path.exists():
        raise FileNotFoundError(f"도메인 정의 파일을 찾을 수 없습니다: {path}")
    with open(path, "r", encoding="utf-8") as f:
        raw = yaml.safe_load(f) or []
    domains = []
    for entry in raw:
        domains.append(
            Domain(
                id=entry["id"],
                name_ko=entry["name_ko"],
                name_en=entry.get("name_en", entry["id"]),
                description=entry.get("description", "").strip(),
                keywords=entry.get("keywords", []),
            )
        )
    return domains


def domains_by_id(path: Path = DEFAULT_DOMAINS_PATH) -> Dict[str, Domain]:
    return {d.id: d for d in load_domains(path)}


@dataclass
class Settings:
    db_path: Path = DEFAULT_DB_PATH
    domains_path: Path = DEFAULT_DOMAINS_PATH
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-5"
    chunk_target_chars: int = 900
    chunk_overlap_chars: int = 150

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            db_path=Path(os.environ.get("YLEARN_DB_PATH", str(DEFAULT_DB_PATH))),
            domains_path=Path(
                os.environ.get("YLEARN_DOMAINS_PATH", str(DEFAULT_DOMAINS_PATH))
            ),
            anthropic_api_key=os.environ.get("ANTHROPIC_API_KEY", ""),
            anthropic_model=os.environ.get("YLEARN_MODEL", "claude-sonnet-5"),
            chunk_target_chars=int(os.environ.get("YLEARN_CHUNK_CHARS", "900")),
            chunk_overlap_chars=int(os.environ.get("YLEARN_CHUNK_OVERLAP", "150")),
        )
