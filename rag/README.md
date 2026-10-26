# 톡talk RAG API

Vue가 FastAPI `:8001`을 직접 호출합니다. Java 인증 서버가 발급한 `ACCESS_TOKEN`
HttpOnly 쿠키를 RAG 서버에서 검증합니다.

## 데이터와 모델

`../datapipeline/data/indexes/current/`의 KOSHA·NIOSH FAISS 인덱스를
읽기 전용으로 사용합니다. Compose의 `indexer`가 인덱스 준비를 확인한 뒤 RAG를
시작합니다. `RAG_INDEX_PATH`로 경로를 바꿀 수 있습니다. 인덱스의
`index.pkl`은 pickle이므로 신뢰하는 팀 산출물만 로드하세요.

검색은 인덱스 생성 때와 같은 `BAAI/bge-m3` 정규화 임베딩을 사용하고,
선택한 CAS 번호와 `KOSHA`·`NIOSH PDF` 출처로 제한합니다. 답변 생성 기본 모델은
`gpt-4o-mini`이며 `RAG_LLM_MODEL`로 변경할 수 있습니다. 서버 환경에
`OPENAI_API_KEY` 또는 `LLM_API_KEY`를 설정합니다. 키는 Vue에 전달하지 않습니다.

복합 질문은 알려진 안전정보 항목(노출 경로, 보관, 보호구, 응급조치, 건강 영향,
노출 감소, 화재 위험·대응)을 각각 검색한 뒤 `top_k` 안에서 근거를 합칩니다.
항목은 기존 인덱스의 `section`·`label` 메타데이터로 제한하므로 인덱스를 다시
만들 필요가 없습니다. 요청 항목 중 근거가 없는 항목은 답을 추측하지 않고
`needs_review=true`로 반환합니다. 단일 항목 질문은 기존 검색을 사용합니다.
일반 단일 항목 검색에서는 NIOSH 공통 코드표를 제외하고, 노출 경로에 약어가
등장하면 해당 약어표를 별도로 가져옵니다.

NIOSH 근거는 PDF 파일명·페이지를, KOSHA 근거는 출처 URL을 반환합니다. PDF의
`url`은 원문 웹 URL이 없어 빈 문자열입니다. `checked_at`은 수집 확인일이며
원문 개정일이 아닙니다. PDF를 브라우저에서 열 수 있는 주소는 별도 정적 파일
배포가 필요합니다.

## Vue에서 호출할 API

| 경로 | 입력 | 결과 |
| --- | --- | --- |
| `GET /chemicals?query=` | 이름·동의어 검색어(선택) | 실제 인덱스에 적재된 물질 목록 |
| `POST /rag-query` | `{material_id, question, top_k?}` | 선택 물질의 답변·출처 |
| `POST /rag-query/auto` | `{question, top_k?}` | 물질 자동 인식 후 답변 또는 후보 |
| `POST /chat-query` | `{question}` | 인덱스 없이 일반 LLM 답변 생성 |
| `POST /speech-to-text` | `multipart/form-data`의 `file` | 녹음 음성을 질문 텍스트로 변환 |
| `POST /text-to-speech` | `{text}` | 답변을 MP3 음성으로 변환 |
| `GET /health/live` | 없음 | 프로세스 생존 |
| `GET /health` | 없음 | 인덱스·재고 DB 상태 |

질문 API의 응답은 `{answer, sources, needs_review, material, resolution}`입니다.
자동 인식 결과가 `ambiguous` 또는 `not_found`이면 LLM을 호출하지 않습니다.
`needs_review`는 근거 부족 또는 유효하지 않은 근거 번호를 뜻합니다. 화학적
정확성을 자동으로 보증하지 않습니다. `top_k` 범위는 1–10이고, 입력 오류는 422,
쿠키 인증 실패는 401, 인덱스·LLM 장애는 503입니다. `/inventory`는 아직
구현되지 않았습니다.

Vue 요청에는 쿠키를 포함해야 합니다.

음성 API는 ElevenLabs를 서버에서만 호출합니다. `ELEVENLABS_API_KEY`와
`ELEVENLABS_VOICE_ID`를 설정하고, 키 권한은 Speech to Text와 Text to Speech만
허용하세요. 모델·언어·출력 형식은 `.env.example`의 기본값을 필요에 따라
바꿀 수 있습니다. 브라우저로 키를 전달하거나 `VITE_*` 변수에 넣지 않습니다.
음성 업로드는 기본 10 MiB, 읽을 텍스트는 5,000자로 제한됩니다.
`/chat-query`는 KOSHA 인덱스를 사용하지 않으며 `LLM_API_KEY` 또는
`OPENAI_API_KEY`가 필요합니다. 프론트의 기본 질문 흐름은 음성 또는 텍스트
질문을 이 API로 보내고, 받은 답변을 `/text-to-speech`로 읽습니다.

```js
const response = await fetch('http://localhost:8001/rag-query/auto', {
  method: 'POST',
  credentials: 'include',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({ question: '아세톤의 노출 경로는?', top_k: 5 }),
});
const result = await response.json();
```

`CORS_ORIGINS`의 기본값은 `http://localhost:5174`입니다. 여러 출처는 쉼표로
구분합니다. 쿠키를 쓰는 API이므로 배포 전 HTTPS·쿠키 설정·CSRF 방어 정책을
함께 정해야 합니다.

## 로컬 실행과 검증

Python 3.11과 uv를 사용합니다. 저장소 루트의 `.env`를 셸이나 실행 환경에
로드하고 `JWT_SECRET`과 LLM 키를 설정하세요. `.env`를 서버가 자동으로 읽지는
않습니다.

```sh
cd rag
uv sync --locked
uv run --locked uvicorn app.main:app --host 0.0.0.0 --port 8001
uv run --locked python -m unittest discover -s tests -p 'test_*.py' -v
```

Swagger UI는 `http://localhost:8001/docs`입니다. 현재 `/health`는 인덱스가
준비돼도 재고 DB가 아직 연결되지 않아 503을 반환하며, `index_ready` 값은
실제 인덱스 파일 상태를 표시합니다. 컨테이너 생존 확인에는 `/health/live`를
사용합니다.
