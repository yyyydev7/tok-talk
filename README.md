# 톡,talk

최상위 작업 폴더는 frontend, backend, datapipeline, rag, infra입니다.
공통 실행 설정과 README, 환경변수 파일은 루트에 둡니다.

| 폴더 | 담당 | 작업 내용 |
| --- | --- | --- |
| frontend/ | 강도희 | Vue 화면, 질문·답변·출처·재고 표시 |
| backend/ | 정수민 | Java 인증, API 계약, DB 스키마 |
| datapipeline/ | 이연주 | NIOSH 수집·정제·청킹·임베딩·인덱스 생성 |
| rag/ | 김대훈 | FastAPI, 물질 식별, 검색·LLM 답변 |
| infra/ | 손연우 | 프록시·환경 설정·배포 기동 검사 |

정수민은 rag/app/api, security, repositories의 API·JWT·재고 조회 구현도 담당합니다.
손연우는 루트 Compose 파일과 infra/의 실행·배포 설정을 담당합니다.

## 구조

    tok-talk/
    ├─ frontend/
    ├─ backend/
    │  ├─ src/                 Java 인증 서버
    │  ├─ contracts/           API 목표 명세와 예시
    │  ├─ db/                  마이그레이션·시드 위치
    │  └─ docs/                설계·협업 문서
    ├─ datapipeline/
    │  ├─ pipeline/            수집·적재 코드 위치
    │  └─ data/                카탈로그·출처·인덱스 산출물
    ├─ rag/
    │  └─ app/                 API·인증 검증·검색·답변·재고 조회
    ├─ infra/
    │  ├─ proxy/               Nginx 설정
    │  ├─ scripts/             환경변수 생성
    │  ├─ tests/e2e/           배포 기동 검사
    │  ├─ github-actions.yml   CI 템플릿
    │  └─ README.md            실행·배포 안내
    ├─ compose.dev.yaml
    ├─ compose.demo.yaml
    └─ .env.example

현재 Vue 화면, Java 로그인·JWT, FastAPI RAG 답변과 MariaDB를 제공합니다.
시연용 재고 조회는 아직 구현되지 않았습니다.
기획 문서의 기준과 미결정 사항은 [설계 결정](backend/docs/decisions.md),
담당 범위는 [협업 규칙](backend/docs/contributing.md)에 있습니다.

## 개발환경 실행

Docker Desktop의 Linux 컨테이너 환경, Docker Compose, Python 3가 필요합니다.
명령은 이 README가 있는 tok-talk 디렉터리에서 실행합니다.

첫 실행 시 `.env`에 `KOSHA_API_KEY`를 설정하세요. 음성 질문과 답변 재생을
사용하려면 `ELEVENLABS_API_KEY`와 `ELEVENLABS_VOICE_ID`도 설정합니다.
API 키는 서버 전용이며 `VITE_*` 변수에 넣지 않습니다. Compose의 `indexer`가
KOSHA·NIOSH 인덱스를 생성하고, 이후에는 입력이 바뀌거나 KOSHA 갱신 주기가
도래한 경우에만 자료를 다시 확인합니다. 내용이 같으면 청킹·임베딩은 재사용합니다.

기본 질문 화면은 KOSHA 인덱스와 별개로 `LLM_API_KEY`를 사용해 일반 답변을
생성한 뒤 ElevenLabs로 읽습니다. KOSHA 인덱스는 물질 근거 검색 기능에서만
사용합니다.

    python3 infra/scripts/init_env.py
    docker compose --env-file .env -f compose.dev.yaml up --build -d --wait
    python3 infra/tests/e2e/smoke.py

환경변수 생성기는 기존 .env를 덮어쓰지 않습니다.
화면은 http://localhost:5174, Java는 8080, FastAPI는 8001, DB 호스트 포트는 13306입니다.
포트를 바꾸면 .env의 관련 주소와 CORS_ORIGINS도 함께 변경하세요.

각 서버의 /health/live는 프로세스 생존을 200으로 응답합니다.
Java /health는 인증 준비 시 200, FastAPI /health는 재고 조회 미구현 상태를 반영해
503을 응답합니다. FastAPI의 `index_ready`로 RAG 인덱스 상태를 확인할 수 있습니다.
기본 인덱스 경로는 호스트의 `datapipeline/data/indexes/current`,
RAG 컨테이너의 `/data/indexes/current`입니다.

    docker compose --env-file .env -f compose.dev.yaml down

이 중지 명령은 DB 볼륨을 보존합니다.

## 데모와 검증

데모에서 처음 인덱스를 만들려면 `.env.demo`에도 `KOSHA_API_KEY`를 설정하세요.

    python3 infra/scripts/init_env.py --demo
    docker compose --env-file .env.demo -f compose.demo.yaml up --build -d --wait
    python3 infra/tests/e2e/proxy_smoke.py

데모는 로컬 http://localhost:8088에만 노출합니다.
기본 프로젝트 이름이 개발 구성과 달라 DB 볼륨과 가입 계정도 분리됩니다.
발표·테스트용 임시 HTTPS 공개는 데모 실행 후
`python3 infra/scripts/public_demo.py start`를 사용합니다.
이 PC와 Docker를 켜 둔 동안 외부에서 접속할 수 있습니다.
공개 종료 및 로컬 복구는 `python3 infra/scripts/public_demo.py stop`입니다.
상시 운영 서버 배포는 별도 구성이 필요합니다.
자세한 내용은 [실행·배포 안내](infra/README.md)를 확인하세요.

두 검사는 실제 가입·중복 가입 거절·잘못된 비밀번호 거절·로그인·JWT 쿠키·로그아웃과
보호된 RAG 경로를 확인합니다. 인덱스 상태에 따라 인증된 물질 목록 200 또는
인덱스 사용 불가 503을 확인하고, 미구현 재고 API는 404를 예상합니다.
검사마다 임의 계정 하나가 DB에 남으며, 쿠키는 메모리에만 보관하고 토큰·비밀번호는 출력하지 않습니다.
실제 LLM 답변은 생성하지 않으므로 화면에서 질문 후 답변·출처 표시를 별도로 확인하세요.
상세 범위와 포트 변경 방법은 [검사 안내](infra/tests/e2e/README.md)에 있습니다.

- frontend: npm ci, npm run build
- backend: ./gradlew --no-daemon build
- datapipeline: uv sync --locked, uv run --locked python -m compileall -q pipeline
- rag: uv sync --locked, uv run --locked python -m compileall -q app

서비스별 명령은 해당 폴더에서 실행합니다.
GitHub Actions 설정은
infra/github-actions.yml에 템플릿으로 보관했습니다.
이 위치에서는 자동 실행되지 않습니다.
# tok-talk
