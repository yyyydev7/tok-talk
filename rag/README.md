# RAG · FastAPI

## 김대훈 RAG 서비스 초기 구성

`app/services/rag.py`는 데이터 담당자가 전달한 FAISS 인덱스를 **읽기 전용**으로
로드합니다. `RAG_INDEX_PATH`는 `config.json`, `index.faiss`, `index.pkl`이 있는
디렉터리를 가리켜야 합니다. 예: 개발 환경에서는
`/Users/daehun/Desktop/Mini-Project_f/data_pipeline/faiss_db/all_five`.
인덱스의 `index.pkl`은 pickle이므로 팀에서 직접 만든 신뢰할 수 있는 파일만
로드하세요. 운영 환경에는 검증된 산출물을 별도 볼륨으로 전달하세요.

인덱스 설정과 동일한 `BAAI/bge-m3` 정규화 임베딩을 사용합니다. 검색은 CAS와
`CDC/NIOSH` 출처를 함께 제한합니다. 현재 전달된 통합 인덱스에는 KOSHA 자료도
포함돼 있지만 서비스 검색 결과에는 넣지 않습니다. `retrieved_at`의 날짜 부분을
`checked_at`으로 표시하며 원문 개정일로 간주하지 않습니다.

```python
from app.services.rag import RagService

service = RagService.from_environment()
result = service.answer("acetone", "아세톤의 노출 경로는?", top_k=5)
```

답변 생성에는 `OPENAI_API_KEY`가 필요합니다. `RAG_LLM_MODEL`로 모델을 변경할 수
있고 기본값은 `gpt-4o-mini`입니다. LLM은 검색된 근거만 전달받으며 유효한 근거
번호가 없으면 `needs_review=true`를 반환합니다. 검색만 확인하려면
`service.search(...)`를 호출하면 됩니다. 이 서비스 모듈에는 HTTP 라우터나 JWT
검증을 넣지 않았습니다. API 담당자가 인증 후 선택형·자동형 엔드포인트에서
호출하도록 연결할 수 있습니다.

새 의존성을 `pyproject.toml`에 선언했습니다. 이 환경에서는 패키지 레지스트리에
접근할 수 없어 `uv.lock`을 갱신하지 못했습니다. 설치 가능한 환경에서
`uv lock && uv sync`를 실행한 뒤 잠금 파일을 함께 반영해야 합니다.

Python 3.11과 uv를 사용하는 개발 시작점입니다. HTTP 서버는 아직 상태 확인만 제공하며, 물질별 NIOSH 검색과 근거 답변은 `app/services/rag.py`의 독립 서비스로 구현했습니다. JWT 검증, 업무 API, 재고 조회는 아직 연결되지 않았습니다.

## 로컬 실행

Python 3.11과 uv를 준비한 뒤 저장소 루트에서 실행합니다.

```sh
cd rag
uv sync --locked
uv run --locked uvicorn app.main:app --host 0.0.0.0 --port 8001 --reload
```

`uv.lock`은 전이 의존성까지 고정합니다. 의존성을 변경할 때 `uv add` 또는 `uv remove`를 사용하고 `pyproject.toml`과 `uv.lock`을 함께 검토합니다. Docker의 uv 버전은 `0.12.19`입니다.

| 경로 | 현재 응답 |
| --- | --- |
| `GET /health/live` | HTTP 200, `{"status":"alive"}` |
| `GET /health` | HTTP 503, `{"status":"degraded","index_ready":false,"inventory_db_ready":false}` |
| `/docs` | 구현된 API의 Swagger UI |
| `/openapi.json` | 구현된 API의 OpenAPI 문서 |

`/health`의 503은 현재 인덱스와 DB가 구현되지 않았다는 뜻입니다. 컨테이너 생존 확인에는 `/health/live`를 사용합니다. 구현 후에는 실제 의존성 상태를 검사하도록 변경하고, 재고 DB 장애가 RAG 요청까지 차단하지 않도록 처리합니다.

## Docker

서비스 실행 진입점은 `app.main:app`입니다. 두 target 모두 `0.0.0.0:8001`에서 실행하며, 현재 필수 환경변수는 없습니다.

Compose에서 전달하는 `CORS_ORIGINS`, `DB_HOST`, `LLM_API_KEY` 등은 향후 연결을 위한 설정 이름입니다. 현재 HTTP 앱은 해당 값을 읽지 않으며, CORS 허용·DB 접속·LLM 호출도 수행하지 않습니다. 독립 RAG 서비스는 `RAG_INDEX_PATH`, `OPENAI_API_KEY`, `RAG_LLM_MODEL`을 사용합니다. `PORT`로 내부 포트를 변경하지 않고 실행 명령에서 `8001`로 고정합니다.

```sh
docker build --target development -t tok-talk-rag:dev rag
docker run --rm -p 8001:8001 tok-talk-rag:dev
```

위 Docker 명령은 저장소 루트에서 실행합니다. `development` target은 자동 재시작을 사용합니다. Compose에서 `rag/app`을 `/app/app`에 마운트하면 로컬 소스 변경을 반영할 수 있습니다. `release` target은 자동 재시작 없이 실행합니다.

## 작업 위치

- `app/api/`: 엔드포인트와 요청·응답 스키마
- `app/security/`: Java와 합의한 JWT 검증
- `app/services/`: 물질 식별, 검색, 프롬프트와 답변 생성
- `app/repositories/`: 재고 DB 접근
- `tests/`: 서비스 단위 검사와 RAG 평가

업무 API는 [`../backend/contracts/`](../backend/contracts/)의 계약과 맞춰 구현합니다. 보호된 업무 API를 추가할 때 인증 검증도 함께 연결해야 합니다. FAISS·임베딩·LLM·DB 라이브러리는 구현 시 선정하여 추가합니다.

문서 수집·정제·청킹·임베딩·인덱스 생성은 독립된 형제 폴더 [`../datapipeline/`](../datapipeline/)에서 담당합니다. RAG 서버는 [`../datapipeline/data/`](../datapipeline/data/)로 전달받은 물질 카탈로그·출처·인덱스를 읽어 검색과 답변을 제공합니다. 서버 시작 시 데이터 수집이나 인덱스 생성을 실행하지 않습니다. 현재 골격에는 이 데이터 연결도 아직 구현되어 있지 않습니다.

RAG 코드의 기본 구문 확인은 저장소 루트에서 다음과 같이 실행합니다.

```sh
python3 -m compileall -q rag/app
```

다음 구현 범위는 물질 목록·검색, 선택형 질문과 질문 내 물질 인식, 출처가 포함된 RAG 답변, 물질별 재고 조회입니다. JWT 쿠키의 이름·알고리즘·발급자·만료 조건을 Java 서버와 합의하고 검증한 뒤 보호된 업무 라우터를 연결합니다. 재고 조회는 LLM이 만든 값 대신 MariaDB의 조회 결과를 반환하도록 구현합니다.

구성 참고: [FastAPI Docker 배포](https://fastapi.tiangolo.com/deployment/docker/), [uv Docker 통합](https://docs.astral.sh/uv/guides/integration/docker/).
