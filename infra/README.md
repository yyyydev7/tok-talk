# 실행·배포 환경

명령은 프로젝트 루트에서 실행합니다.

    python3 infra/scripts/init_env.py
    docker compose --env-file .env -f compose.dev.yaml config --quiet
    docker compose --env-file .env -f compose.dev.yaml up --build -d --wait

실제 환경변수가 포함된 config 전체 출력은 공유하지 마세요.
--quiet는 문법·보간만 확인하고 비밀값을 출력하지 않습니다.

## 현재 제공 범위

- 개발 구성: frontend, backend, rag, db와 인덱스를 준비하는 indexer
- 데모 구성: 위 서비스의 release 이미지와 같은 출처의 HTTP 프록시
- Java 인증 서버는 MariaDB에 가입 계정을 저장하고 JWT 쿠키를 발급
- FastAPI는 같은 JWT 설정으로 인증하며 FAISS 물질 목록·질문 API를 제공
- 재고 조회·재고 시드·테이블별 권한 분리는 미구현
- Compose의 프로세스 검사는 /health/live 사용; 업무 준비 상태는 /health로 별도 확인

DB와 인덱스 준비 상태를 서버 생존과 묶지 않았습니다.
향후 재고 DB 장애가 RAG 컨테이너 재시작이나 전체 접근 차단으로 이어지지 않도록 유지하세요.
DB를 사용하는 초기화 작업에는 db의 service_healthy 의존성을 추가합니다.
indexer가 성공한 뒤 RAG가 시작되며, 호스트의 `datapipeline/data/indexes/current`를
RAG 컨테이너의 `/data/indexes/current`로 읽습니다. `RAG_INDEX_PATH`로 변경할 수 있습니다.

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
기본 프로젝트 이름이 개발 구성과 달라 DB 볼륨과 가입 계정도 분리됩니다.

## 기동·인증 검증

각 구성 실행 후 다음 검사를 사용합니다.

    python3 infra/tests/e2e/smoke.py
    python3 infra/tests/e2e/proxy_smoke.py

첫 명령은 개발 구성, 두 번째 명령은 데모 구성을 검사합니다. 화면과 프로세스 생존에 더해
실제 가입·중복 거절·잘못된 비밀번호 거절·로그인·JWT 쿠키·로그아웃과 보호된 RAG 경로를 확인합니다.
RAG `/health`의 503은 재고 DB 미구현을 반영합니다. `index_ready`에 따라 인증된 물질 목록의
200 또는 인덱스 사용 불가 503을 확인하며, 재고 API는 아직 404를 예상합니다.

검사마다 임의 가입 계정 하나가 DB에 남습니다. 쿠키는 메모리에만 보관하고 토큰·비밀번호는
출력하지 않습니다. 실제 LLM 답변 생성은 별도 화면 검증이 필요합니다.
자세한 범위와 포트 변경 인자는 [검사 안내](tests/e2e/README.md)를 참고하세요.

`compose.demo.yaml` 단독 구성은 로컬 HTTP용입니다.
발표·테스트용 임시 HTTPS 공개는 아래 절차를 사용하세요.
상시 운영 서버 배포에는 실제 도메인, 테이블별 DB 계정, 이미지 digest,
DB 백업·복구와 키 교체 절차를 별도로 준비해야 합니다.

## 발표·테스트용 임시 HTTPS 공개

다른 PC에서 데모 실행을 재현하고 로그인·질문·출처 표시까지 확인한 다음 진행합니다.
데모 스택이 실행 중인 상태에서 프로젝트 루트에서 실행하세요.

    python3 infra/scripts/public_demo.py start

스크립트가 Cloudflare Quick Tunnel의 `https://...trycloudflare.com` 주소를 출력합니다.
별도 서버·도메인·Cloudflare 계정이 필요하지 않습니다. 처음 실행하면 공식
`cloudflare/cloudflared` 이미지를 다운로드합니다. 공유기 포트 개방도 필요하지 않습니다.
서비스는 이 PC와 Docker가 실행 중인 동안 사용할 수 있고, PC 절전 중에는 접속할 수 없습니다.
Quick Tunnel은 개발·테스트용이며 상시 운영을 보장하지 않습니다.
공식 안내: https://developers.cloudflare.com/tunnel/get-started/quick-tunnels/

구조는 외부 브라우저 → Cloudflare HTTPS → tunnel → public-proxy → 기존 서비스입니다.
`public-proxy`와 `tunnel` 두 컨테이너를 기존 데모 프로젝트에 추가합니다.
DB·RAG·프런트 컨테이너와 기존 데이터를 그대로 사용하고 백엔드만 HTTPS 인증 설정으로
재생성합니다. 기존 로그인은 다시 해야 합니다. 공개 중에는 출력된 HTTPS 주소를 사용하세요.
백엔드가 공개 Origin만 허용하므로 로컬 8088의 로그인·가입은 중지 명령 실행 후 이용합니다.

`compose.public.yaml`은 데모 파일에 덧붙이는 설정입니다. 단독 실행하지 마세요.
시작 스크립트가 주소 발급 후 CORS와 Secure 쿠키를 적용하고, 전용 Nginx에서 잘못된 Host,
Origin이 없거나 다른 사이트에서 온 POST 요청을 거절합니다.
회원가입·로그인은 전체 방문자 합산 분당 30건(추가 burst 10), 질문은 두 경로 합산
분당 6건(추가 burst 5), 동시 질문 최대 2건으로 제한합니다. 초과하면 HTTP 429가 나옵니다.
쿠키와 요청 본문은 프록시 로그에 기록하지 않습니다.
실제 질문은 기존 LLM API 사용량에 포함됩니다.

발급된 주소는 `.env.public`에 보관합니다. 이 파일에는 공개 주소만 있고 Git에서는 제외됩니다.
실행 중 `start`를 다시 호출하면 기존 터널을 사용합니다. 터널을 종료하고 다시 시작하거나
Docker/PC를 재시작하면 주소가 바뀔 수 있으므로 `start`를 다시 실행하고 새 주소를 공유하세요.

    python3 infra/scripts/public_demo.py status
    python3 infra/tests/e2e/proxy_smoke.py --base https://발급된주소.trycloudflare.com --public

공개 검사는 화면·Vue 직접 경로·Origin 차단·Secure 쿠키·가입·로그인·로그아웃과
준비된 인덱스의 실제 물질 목록을 확인합니다. 임의 계정 한 개가 DB에 남으며 실제 LLM
질문은 별도 화면 검증이 필요합니다. 휴대폰 Wi-Fi를 끄고 모바일 데이터에서도 확인하세요.

공개를 끝내려면 다음 명령을 실행합니다.

    python3 infra/scripts/public_demo.py stop

터널을 먼저 닫고 추가 컨테이너만 제거한 뒤 백엔드와 기존 프록시를 로컬 설정으로
복구합니다. DB 볼륨과 인덱스는 보존하며 로컬 `http://localhost:8088`을 다시 사용할 수 있습니다.
전체 데모를 정리할 때도 데이터가 필요하면 `down --volumes`를 사용하지 마세요.

주소가 발급되지 않으면 Docker 인터넷 연결과 학교·회사망의 외부 TCP 7844 허용 여부를
확인하세요. 이 구성은 터널 연결에 HTTP/2를 사용합니다. 시작 도중 실패하면 스크립트가
터널을 닫고 로컬 데모 복구를 시도합니다. 강제 종료 등으로 남은 컨테이너도 `stop`으로 정리합니다.
키·JWT·DB 비밀번호가 포함된 Compose `config` 전체 출력이나 `.env.demo`를 공유하지 마세요.

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
