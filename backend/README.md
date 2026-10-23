# Java 인증 서버

JDK 21과 Gradle Application Plugin으로 실행하는 인증 서비스의 시작 골격입니다. Spring과 외부 인증 라이브러리는 아직 추가하지 않았습니다.

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

`PORT`만 현재 코드가 소비하는 환경변수입니다. 생략하면 `8080`을 사용하며 유효 범위는 `1..65535`입니다. DB와 JWT 환경변수는 실제 인증 구현 단계에서 연결합니다.

## 현재 확인 가능한 경로

| 요청 | 상태 | 의미 |
| --- | --- | --- |
| `GET /health/live` | `200` | HTTP 프로세스가 응답함 |
| `GET /health` | `503` | 인증 기능 미구현, `auth_ready: false` |
| 위 두 경로의 GET 이외 메서드 | `405` | `Allow: GET` 반환 |
| 그 외 경로 | `404` | 아직 제공하지 않는 API |

```sh
curl -i http://localhost:8080/health/live
curl -i http://localhost:8080/health
```

로그인, 회원가입, 로그아웃, JWT 발급·검증, DB 연결, CORS는 아직 구현하지 않았습니다. 정상 응답하는 생존 확인 경로를 로그인 성공이나 통합 준비 완료로 해석하지 마십시오. 현재 테스트 소스는 비어 있으므로 `build` 성공만으로 인증 검증이 완료되지는 않습니다.

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

공통 API 계약을 먼저 합의한 뒤 계정 저장·비밀번호 해시, 인증 API, JWT 쿠키 속성, CSRF·CORS를 구현합니다. 로그인 완료 후 Vue 화면으로 돌아가는 경로도 함께 확정합니다. RAG 호출의 JWT 검증은 `../rag/`의 책임입니다.

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
