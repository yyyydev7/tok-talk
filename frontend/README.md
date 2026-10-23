# 톡talk 프론트엔드

Vue 3 + Vite + TypeScript 화면입니다. Java 인증 서버가 발급한 HttpOnly JWT 쿠키를 확인한 뒤 RAG 물질 검색·질문 API와 별도 가상 재고 조회 API를 호출합니다.

## 로컬 실행

Node.js 24.22.1을 사용합니다. `.node-version`을 지원하는 버전 관리 도구로 버전을 맞추거나 루트의 Docker Compose 실행 절차를 사용하세요.

```sh
cp .env.example .env
npm ci
npm run dev
```

브라우저에서 `http://localhost:5174`에 접속합니다. 5174 포트를 사용 중이면 자동으로 다른 포트를 선택하지 않고 종료합니다.

```sh
npm run typecheck
npm run build
```

`npm run preview`는 빌드 결과의 로컬 확인용입니다. 데모 배포 이미지는 Nginx로 정적 파일을 제공합니다.

## 환경변수

| 변수 | 용도 | 로컬 예시 |
| --- | --- | --- |
| `VITE_AUTH_BASE_URL` | Java 인증 서버의 기본 주소 | `http://localhost:8080` |
| `VITE_RAG_BASE_URL` | FastAPI 서버의 기본 주소 | `http://localhost:8001` |

인증 확인은 `GET /api/auth/check`, 로그인은 `POST /api/login`, 회원가입은 `POST /api/signup`을 호출합니다. 회원가입의 302 응답은 브라우저 내 화면 이동으로 이어지지 않도록 수동 처리합니다. 질문은 `/rag-query/auto` 또는 `/rag-query`, 물질 선택은 `GET /chemicals`, 재고는 `GET /inventory?material_id=...`를 사용합니다. 쿠키가 필요한 모든 호출에는 `credentials: 'include'`를 적용합니다. 화면의 기본 주소에는 개별 API 경로를 붙이지 않습니다.

인증 서버가 503이면 연결 불가 화면을 표시합니다. RAG API가 401을 반환하면 로그인 화면으로 돌아가고, 재고 조회가 실패해도 RAG 답변은 유지합니다. 재고는 `is_demo` 응답과 함께 시연용으로 표시합니다.

현재 `feat/sumin`에서는 인증 API가 구현되어 있지만 물질 검색·질문·재고 API는 계약만 있고 RAG 서버에는 아직 구현되지 않았습니다. 따라서 해당 화면과 연동 코드는 준비되어 있으며, 실제 질문·출처·재고 E2E 시연은 RAG API 구현 후 가능합니다. 개발 시 `http://localhost:5174`로 접속해야 기본 CORS 허용 주소와 일치합니다.

`VITE_` 변수는 브라우저에 공개되는 설정입니다. JWT 비밀키, DB 비밀번호, LLM API 키를 넣지 않습니다. 빌드 후 환경변수 변경은 정적 파일에 반영되지 않으므로 `release` 이미지는 빌드 인자로 주소를 설정하고 다시 빌드해야 합니다. 동일 출처 프록시를 사용하면 빈 기본 주소에 API 경로를 연결할 수 있습니다.

## Docker 단계

- `development`: Node 24에서 Vite 개발 서버 실행, 내부 포트 `5174`.
- `build`: 타입 검사 후 `dist/` 생성. `VITE_AUTH_BASE_URL`, `VITE_RAG_BASE_URL` 빌드 인자를 받습니다.
- `release`: 생성한 `dist/`를 Nginx로 제공, 내부 포트 `80`. 화면 경로에는 SPA fallback을 적용하고 `/` 응답으로 상태를 확인합니다. API 프록시는 `infra/proxy/`가 담당합니다.

서비스 전체 실행은 저장소 루트의 `README.md`, `compose.dev.yaml`, `compose.demo.yaml`을 따릅니다. 의존성을 변경하면 정확한 버전과 `package-lock.json`을 함께 업데이트합니다.

참고: [Vite 시작 안내](https://vite.dev/guide/), [Node 공식 Docker 이미지](https://hub.docker.com/_/node), [Nginx 공식 Docker 이미지](https://hub.docker.com/_/nginx).
