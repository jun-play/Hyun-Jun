# 아키텍처

```
                ┌──────────────┐
  YouTube URL → │ YouTubeAdapter│ ─┐
                └──────────────┘  │
                                  │  Fetched(type, url, title, author, text)
  텍스트/책 발췌 → │ TextAdapter  │ ─┘
                └──────────────┘
                       │
                       ▼
              chunk_text() (textutil.py)
                       │  문장 경계를 지키며 target_chars 단위로 분할
                       ▼
              Distiller.distill(chunk, domains)
       ┌───────────────┴────────────────┐
       ▼                                ▼
AnthropicDistiller                ExtractiveFallbackDistiller
(Claude API, 의미 기반)             (규칙 기반, 의존성 없음)
       └───────────────┬────────────────┘
                       ▼
              AdviceCard(domain, summary, action_items, quote, confidence)
                       │
                       ▼
                 Store (SQLite)
                       │
                       ▼
        ask(question) → TfidfIndex.search() → top-k AdviceCard
                       │
                       ▼
              Distiller.synthesize(question, cards) → 최종 답변
```

## 모듈 책임

| 모듈 | 책임 |
|---|---|
| `config.py` | 설정값, `data/domains.yaml` 로딩 |
| `models.py` | `Source` / `Chunk` / `AdviceCard` 데이터클래스 |
| `textutil.py` | 문장 분리, 토크나이즈(조사 제거 근사치), 청킹 — 외부 의존성 없음 |
| `retrieval.py` | 순수 파이썬 TF-IDF 코사인 유사도 검색 |
| `store.py` | SQLite 영속 저장 (sources/chunks/advice_cards) |
| `ingest/base.py` | `SourceAdapter` 프로토콜 (`fetch(ref) -> Fetched`) |
| `ingest/youtube.py` | 유튜브 자막(youtube-transcript-api) + 메타데이터(yt-dlp), 둘 다 optional |
| `ingest/text.py` | 직접 입력한 텍스트/파일 (책 발췌 등)을 같은 파이프라인에 태우는 어댑터 |
| `distill/llm.py` | `Distiller` 프로토콜, Claude 기반 구현과 규칙 기반 fallback 구현 |
| `distill/prompts.py` | Claude 호출용 프롬프트 템플릿 |
| `pipeline.py` | `ingest()` / `ask()` 오케스트레이션, 중복 수집 방지 |
| `cli.py` | `python -m ylearn.cli {ingest,ask,domains,stats}` |

## 설계 원칙

- **의존성 없이도 end-to-end로 동작해야 한다.** `anthropic`,
  `youtube-transcript-api`, `yt-dlp` 는 전부 optional import이며, 없으면
  `ExtractiveFallbackDistiller`(규칙 기반)와 `TextAdapter`만으로도 수집 →
  증류 → 검색 → 답변까지 전부 동작한다. 이는 테스트/CI/오프라인 개발
  환경에서도 파이프라인 전체를 검증할 수 있게 하기 위함이다.
- **어댑터 패턴으로 새 출처를 추가할 수 있다.** `SourceAdapter.fetch(ref)`
  만 구현하면 새로운 출처(예: 팟캐스트, 블로그, 전자도서관 API)를
  파이프라인에 추가할 수 있다.
- **도메인 taxonomy는 코드가 아니라 데이터.** `data/domains.yaml`을
  수정하는 것만으로 삶의 영역을 추가/수정할 수 있다.
- **조언 카드는 항상 출처를 남긴다.** `AdviceCard.source_id` /
  `chunk_id`를 통해 어떤 영상/책의 어느 부분에서 나온 조언인지 항상
  역추적할 수 있다 (근거 없는 조언을 만들지 않기 위함).

## 향후 개선 아이디어

- **검색 품질**: 지금은 의존성 없는 TF-IDF다. 정확도를 높이려면
  `retrieval.py`의 `TfidfIndex` 인터페이스(`add_document`/`build`/`search`)
  를 유지한 채, 내부를 실제 임베딩(예: `sentence-transformers`,
  또는 Claude/OpenAI 임베딩 API) + 벡터DB(`chromadb`, `sqlite-vss`)로
  교체하면 된다.
- **한국어 토크나이징**: 지금은 조사(josa) 제거 휴리스틱만 쓴다.
  `konlpy`/`kiwipiepy` 같은 형태소 분석기를 optional 의존성으로 붙이면
  훨씬 정확해진다.
- **책 출처 자동화**: `ingest/text.py`와 같은 인터페이스로
  `ingest/library.py`(전자도서관 API), `ingest/aladin.py`(알라딘 API)
  어댑터를 추가할 수 있다. 저작권 범위 내에서 목차/서평/발췌만 가져오는
  형태를 권장한다.
- **중복/모순 조언 정리**: 같은 도메인 안에서 조언 카드가 쌓이면, 주기적으로
  LLM에게 "이 카드들 중 겹치는 것을 합치고, 서로 모순되는 조언이 있으면
  표시해줘" 같은 배치 작업을 돌리는 `dedupe.py`를 추가할 수 있다.
- **UI**: 지금은 CLI다. 개인용 웹 UI(예: 간단한 Flask/Streamlit 대시보드)를
  올리면 도메인별로 조언 카드를 브라우징하기 편해진다.
