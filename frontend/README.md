# 톡talk 프론트엔드

Vue 3 + Vite + TypeScript 기반 시작 프로젝트입니다. 현재는 준비 중 화면만 제공하며 로그인, 물질 검색, 질문, 출처, 재고 화면은 이후 API 계약에 맞춰 구현합니다.

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

현재 준비 화면은 API를 호출하지 않습니다. API 연결 시 이 설정을 사용하고 쿠키가 필요한 호출에는 `credentials: 'include'`를 적용합니다. 화면의 기본 주소에는 개별 API 경로를 붙이지 않습니다.

`VITE_` 변수는 브라우저에 공개되는 설정입니다. JWT 비밀키, DB 비밀번호, LLM API 키를 넣지 않습니다. 빌드 후 환경변수 변경은 정적 파일에 반영되지 않으므로 `release` 이미지는 빌드 인자로 주소를 설정하고 다시 빌드해야 합니다. 동일 출처 프록시를 사용하면 빈 기본 주소에 API 경로를 연결할 수 있습니다.

## Docker 단계

- `development`: Node 24에서 Vite 개발 서버 실행, 내부 포트 `5174`.
- `build`: 타입 검사 후 `dist/` 생성. `VITE_AUTH_BASE_URL`, `VITE_RAG_BASE_URL` 빌드 인자를 받습니다.
- `release`: 생성한 `dist/`를 Nginx로 제공, 내부 포트 `80`. 화면 경로에는 SPA fallback을 적용하고 `/` 응답으로 상태를 확인합니다. API 프록시는 `backend/deploy/proxy/`가 담당합니다.

서비스 전체 실행은 저장소 루트의 `README.md`, `compose.dev.yaml`, `compose.demo.yaml`을 따릅니다. 의존성을 변경하면 정확한 버전과 `package-lock.json`을 함께 업데이트합니다.

참고: [Vite 시작 안내](https://vite.dev/guide/), [Node 공식 Docker 이미지](https://hub.docker.com/_/node), [Nginx 공식 Docker 이미지](https://hub.docker.com/_/nginx).
