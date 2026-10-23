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

현재는 Vue 시작 화면, Java/FastAPI 최소 서버, 빈 MariaDB를 제공하는 개발 골격입니다.
로그인·JWT 검증·문서 적재·RAG 답변·재고 조회는 아직 구현하지 않았습니다.
기획 문서의 기준과 미결정 사항은 [설계 결정](backend/docs/decisions.md),
담당 범위는 [협업 규칙](backend/docs/contributing.md)에 있습니다.

## 개발환경 실행

Docker Desktop의 Linux 컨테이너 환경, Docker Compose, Python 3가 필요합니다.
명령은 이 README가 있는 tok-talk 디렉터리에서 실행합니다.

    python3 infra/scripts/init_env.py
    docker compose --env-file .env -f compose.dev.yaml up --build -d --wait
    python3 infra/tests/e2e/smoke.py

환경변수 생성기는 기존 .env를 덮어쓰지 않습니다.
화면은 http://localhost:5174, Java는 8080, FastAPI는 8001, DB 호스트 포트는 13306입니다.
포트를 바꾸면 .env의 관련 주소와 CORS_ORIGINS도 함께 변경하세요.

/health/live는 프로세스 생존을 200으로 응답합니다.
/health는 미구현 기능을 준비 완료로 표시하지 않고 503을 응답합니다.
화면은 아직 업무 API를 호출하지 않습니다.

    docker compose --env-file .env -f compose.dev.yaml down

이 중지 명령은 DB 볼륨을 보존합니다.

## 데모와 검증

    python3 infra/scripts/init_env.py --demo
    docker compose --env-file .env.demo -f compose.demo.yaml up --build -d --wait
    python3 infra/tests/e2e/proxy_smoke.py

데모는 로컬 http://localhost:8088에만 노출합니다.
공개 HTTPS 배포는 아직 구성하지 않았습니다.
자세한 내용은 [실행·배포 안내](infra/README.md)를 확인하세요.

- frontend: npm ci, npm run build
- backend: ./gradlew --no-daemon build
- datapipeline: uv sync --locked, uv run --locked python -m compileall -q pipeline
- rag: uv sync --locked, uv run --locked python -m compileall -q app

서비스별 명령은 해당 폴더에서 실행합니다.
GitHub Actions 설정은
infra/github-actions.yml에 템플릿으로 보관했습니다.
이 위치에서는 자동 실행되지 않습니다.
# tok-talk
