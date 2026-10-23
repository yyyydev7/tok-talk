# 실행·배포 환경

명령은 프로젝트 루트에서 실행합니다.

    python3 infra/scripts/init_env.py
    docker compose --env-file .env -f compose.dev.yaml config --quiet
    docker compose --env-file .env -f compose.dev.yaml up --build -d --wait

실제 환경변수가 포함된 config 전체 출력은 공유하지 마세요.
--quiet는 문법·보간만 확인하고 비밀값을 출력하지 않습니다.

## 현재 제공 범위

- 개발 구성: frontend, backend, rag, db
- 데모 구성: 위 서비스의 release 이미지와 같은 출처의 HTTP 프록시
- DB는 빈 tok_talk 데이터베이스와 로컬 개발용 일반 계정만 생성
- 마이그레이션·재고 시드·테이블별 권한 분리는 담당자가 구현할 위치와 규칙만 제공
- Java와 FastAPI의 DB 설정은 전달되지만 아직 연결하지 않음
- Compose의 프로세스 검사는 /health/live 사용; 업무 준비 상태는 /health로 별도 확인

DB와 인덱스 준비 상태를 서버 생존과 묶지 않았습니다.
향후 재고 DB 장애가 RAG 컨테이너 재시작이나 전체 접근 차단으로 이어지지 않도록 유지하세요.
DB를 사용하는 초기화 작업에는 db의 service_healthy 의존성을 추가합니다.

## 포트

개발 서비스는 호스트의 127.0.0.1에만 바인딩합니다.
같은 컴퓨터의 기존 실습 서버와 포트가 겹치면 .env에서 바꿀 수 있습니다.
컨테이너 사이의 주소는 db:3306, backend:8080, rag:8001을 사용합니다.

## 데모 구성 확인

다음 명령은 다른 COMPOSE_PROJECT_NAME과 새로운 비밀값을 가진 .env.demo를 생성합니다.
기존 파일은 덮어쓰지 않습니다.

    python3 infra/scripts/init_env.py --demo
    docker compose --env-file .env.demo -f compose.demo.yaml up --build -d --wait

접속: http://localhost:8088 (DEMO_HTTP_PORT로 변경 가능).
브라우저의 /api/*는 Java, /rag-query 및 /chemicals, /inventory, /health는 FastAPI로 전달됩니다.
루트 /는 빌드된 Vue 화면을 제공합니다. VITE_*는 빌드 시 고정되는 공개 설정입니다.

이 파일은 공개 HTTPS 배포를 완료한 구성이 아닙니다.
공개 전에는 TLS 종료, 실제 도메인, 쿠키 Secure/SameSite/Path, CSRF,
요청 제한, 테이블별 DB 계정과 이미지 digest를 확정하고 구현해야 합니다.
기능 API도 아직 구현하지 않았으므로 공개 서비스로 안내하지 마세요.

## DB 데이터 유지

down은 볼륨을 보존합니다. 비밀번호 환경변수를 바꿔도 이미 초기화된 DB 계정은 바뀌지 않습니다.
기존 데이터베이스는 담당자가 마이그레이션·계정 변경 절차로 관리합니다.

DB 변경 SQL은 backend/db/migrations, 시연 시드는 backend/db/seeds에 추가합니다.
프록시 설정은 infra/proxy/nginx.conf에 있습니다.

## CI 템플릿

github-actions.yml을 CI 템플릿으로 이 폴더에 보관합니다.
현재 위치에서는 GitHub Actions가 실행되지 않습니다. GitHub는 저장소 루트의
.github/workflows 안에 있는 워크플로 파일만 자동으로 탐색합니다.
추후 CI를 활성화할 때 이 파일을 .github/workflows/ci.yml로 옮기세요.
템플릿의 명령은 이 프로젝트 디렉터리를 팀 저장소 루트로 사용하는 것을 전제로 합니다.

## backend에서 분리한 파일

- backend/deploy/proxy → infra/proxy
- backend/deploy/github-actions.yml → infra/github-actions.yml
- backend/scripts → infra/scripts
- backend/tests/e2e → infra/tests/e2e

Compose 파일과 환경변수 파일은 저장소 루트에 유지합니다.
Java 소스·API 계약·DB SQL·서비스별 Dockerfile은 원래 위치에 유지합니다.
frontend, rag, datapipeline 폴더는 수정하지 않았습니다.
frontend/README.md와 rag/tests/README.md에 있는 이전 배포 경로는 위 이동표를 참고하세요.
