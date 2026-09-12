# ylearn — 유튜브 AI 학습/조언 증류 시스템

유튜브(그리고 앞으로는 책)에 흩어져 있는 삶의 조언들을 수집해서, 삶의
영역별로 정제된 "조언 카드"로 증류하고, 질문을 던지면 관련된 조언을
종합해서 답해주는 개인용 지식 시스템이다.

왜 이걸 만들었는지는 [`docs/VISION.md`](docs/VISION.md)에, 어떻게 동작하는지는
[`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md)에 정리되어 있다.

## 빠른 시작

추가 설치 없이 (PyYAML만 있으면) 바로 동작한다:

```bash
pip install -r requirements.txt   # PyYAML 뿐 — 이미 있다면 생략 가능

# 1. 도메인(삶의 영역) 목록 확인
PYTHONPATH=src python -m ylearn.cli domains

# 2. 자료 수집 — 텍스트 직접 입력 ("제목|저자|본문" 형식)
PYTHONPATH=src python -m ylearn.cli ingest --text \
  "회계사 개업 노하우|김회계|회계사로 개업을 하려면 먼저 사업계획서를 작성해야 합니다. 초기 6개월 운영자금을 미리 확보해두는 것이 중요합니다."

# 3. 질문하기
PYTHONPATH=src python -m ylearn.cli ask "회계사 개업하려면 뭐부터 준비해야 해?"

# 4. 현황 통계
PYTHONPATH=src python -m ylearn.cli stats
```

## 유튜브 영상 수집하기

```bash
pip install youtube-transcript-api yt-dlp   # 선택 설치
PYTHONPATH=src python -m ylearn.cli ingest --youtube "https://www.youtube.com/watch?v=XXXXXXXXXXX"
```

자막이 없는 영상이거나 `youtube-transcript-api`가 설치되어 있지 않으면
에러 메시지로 안내한다 (파이프라인의 나머지 부분은 텍스트 입력만으로도
독립적으로 계속 쓸 수 있다).

## Claude로 실제 의미 기반 증류/종합 쓰기

`ANTHROPIC_API_KEY`가 없으면 규칙 기반(fallback) distiller가 자동으로
대신 동작한다 (품질은 낮지만 항상 동작). 실제 의미 이해 기반으로 쓰려면:

```bash
pip install anthropic
cp .env.example .env   # 값 채우고
export ANTHROPIC_API_KEY=sk-...
```

## 책/도서 자료 넣기

전자도서관, 알라딘 같은 곳은 자동 스크래핑 대신, 사용자가 읽은 내용의
발췌/요약을 직접 넣도록 되어 있다 (`--text` 옵션, 파일 경로도 가능).
같은 파이프라인(청킹 → 증류 → 저장 → 검색)을 그대로 탄다.

## 도메인(삶의 영역) 추가/수정하기

코드를 건드릴 필요 없이 [`data/domains.yaml`](data/domains.yaml)만 수정하면 된다.

## 테스트

```bash
python -m unittest discover -s tests -t tests
```

외부 API 키나 네트워크 없이, 전부 로컬에서 동작하는 24개 테스트가 있다.

## 프로젝트 구조

```
src/ylearn/
  config.py        설정 + 도메인 taxonomy 로딩
  models.py        Source / Chunk / AdviceCard
  textutil.py       문장 분리 / 토크나이즈 / 청킹 (의존성 없음)
  retrieval.py      순수 파이썬 TF-IDF 검색
  store.py          SQLite 저장소
  ingest/           수집 어댑터 (youtube, text)
  distill/          증류/종합 (Claude 기반 + 규칙 기반 fallback)
  pipeline.py       ingest() / ask() 오케스트레이션
  cli.py            CLI 진입점
data/domains.yaml  삶의 영역(도메인) 정의
tests/             단위/통합 테스트
docs/              비전 & 아키텍처 문서
```
