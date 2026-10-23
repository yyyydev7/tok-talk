# Java 인증 서버

JDK 21로 실행하는 계정·JWT 인증 서비스입니다. 계정은 MariaDB에 저장하고 비밀번호는 BCrypt로 해시합니다.

## 실행

JDK 21을 설치한 후 이 폴더에서 실행합니다. Gradle Wrapper가 고정한 Gradle 버전을 최초 실행 시 내려받으므로 처음에는 인터넷 연결이 필요합니다.

```sh
./gradlew --no-daemon run
```

기본 주소는 `http://localhost:8080`이며, 서버는 컨테이너 접근을 위해 `0.0.0.0`에 바인딩합니다.

```sh
PORT=18080 ./gradlew --no-daemon run
./gradlew --no-daemon clean build installDist
./build/install/tok-talk-auth/bin/tok-talk-auth
```

실행 중인 서버의 생존 여부는 배포 실행 파일의 `--healthcheck`로도 확인할 수 있습니다. 같은 `PORT`로 `/health/live`를 요청하고 성공 시 종료 코드 `0`, 통신 실패 또는 다른 상태 코드에는 `1`을 반환합니다. Gradle을 실행하지 않는 JDK 기본 HTTP 클라이언트 방식입니다.

```sh
./build/install/tok-talk-auth/bin/tok-talk-auth --healthcheck
```

실행에는 `JWT_SECRET`(최소 32바이트), `DB_USER`, `DB_PASSWORD`가 필요합니다. `JWT_ISSUER`,
`JWT_AUDIENCE`, `JWT_ACCESS_TTL_SECONDS`, `COOKIE_SECURE`, DB 접속 변수와 `CORS_ORIGINS`를 설정할 수 있습니다.

## 현재 확인 가능한 경로

| 요청 | 상태 | 의미 |
| --- | --- | --- |
| `GET /health/live` | `200` | HTTP 프로세스가 응답함 |
| `GET /health` | `200` | 인증 기능 준비, `auth_ready: true` |
| `POST /api/signup` | `302` | 계정 생성 후 `/login` 이동 |
| `POST /api/login` | `200` | JWT 쿠키 발급 |
| `GET /api/auth/check` | `200/401` | JWT 쿠키 검증 |
| `POST /api/logout` | `302` | JWT 쿠키 삭제 |
| 위 두 경로의 GET 이외 메서드 | `405` | `Allow: GET` 반환 |
| 그 외 경로 | `404` | 아직 제공하지 않는 API |

```sh
curl -i http://localhost:8080/health/live
curl -i http://localhost:8080/health
```

회원가입과 로그인은 `application/x-www-form-urlencoded` 요청을 받습니다. 사용자명은 영문자·숫자·점·밑줄·하이픈 3~64자,
비밀번호는 8~128자입니다. JWT는 HS256으로 서명하며 `sub`, `iss`, `aud`, `iat`, `exp`, `jti`를 검증합니다.
로그아웃은 브라우저 쿠키를 삭제하지만 이미 발급된 JWT를 서버에서 조기 폐기하지는 않습니다.

## 컨테이너

저장소 루트의 개발 Compose는 이 Dockerfile의 `development` target을 사용합니다. 단독 실행도 가능합니다.

```sh
docker build --target development -t tok-talk-auth:dev .
docker run --rm -p 8080:8080 tok-talk-auth:dev
docker build --target release -t tok-talk-auth:release .
```

두 target 모두 이미지 빌드 시 만든 `installDist` 실행 파일로 서버를 시작합니다. Java 코드를 변경하면 이미지를 다시 빌드합니다. Docker 생존 확인은 10초 간격, 5초 제한, 초기 유예 20초로 `/health/live`를 확인합니다. 이는 `/health`의 인증 준비 상태와 구분됩니다.

`release` target은 `installDist` 산출물과 JRE만 포함하고 UID/GID `10001`로 실행합니다. 현재 상태는 배포 가능한 인증 기능의 완성이 아닌 실행 골격입니다.

## 다음 구현 범위

다음 범위는 로그인 Vue 화면 연결, 요청 제한, 계정 관리, 토큰 조기 폐기 여부와 운영 환경의 HTTPS입니다.
RAG 보호 라우터는 `../rag/app/security/`의 `CurrentUser` 의존성을 사용합니다.

## 공통 개발 자료

API·DB·협업 자료는 backend에, 배포 설정·도구·기동 검사는 infra에 둡니다.
경로는 저장소 루트 기준입니다.

- `backend/contracts/`: API 명세와 응답 예시
- `backend/docs/`: 협업 규칙과 설계 결정
- `backend/db/`: 마이그레이션·시연 시드
- `infra/`: 프록시 설정과 비활성 CI 템플릿
- `infra/scripts/init_env.py`: 루트 `.env` 또는 `.env.demo` 생성
- `infra/tests/e2e/`: 서비스 간 기동 검사

개발·데모 실행 구성은 루트 `compose.dev.yaml`, `compose.demo.yaml`에 있습니다.
CI 템플릿은 `infra/github-actions.yml`에 보관하며 현재 자동 실행되지 않습니다.
활성화하려면 GitHub가 자동 탐색하는 `.github/workflows/ci.yml`로 옮겨야 합니다.
