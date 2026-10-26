# 데이터 파이프라인

KOSHA MSDS API와 NIOSH Pocket Guide PDF를 사용해 5개 물질을 수집·정제하고 BGE-M3 및 FAISS 인덱스를 생성합니다. NIOSH 웹페이지는 수집하지 않습니다. Compose의 `indexer`가 RAG 시작 전에 인덱스를 확인하고, 필요할 때만 다시 생성합니다.

청킹은 원본 레코드의 `section`·`label` 경계를 유지합니다. `자료없음` 레코드는 원본
JSON에 보존하되 임베딩에서는 제외하고, 긴 레코드는 약 1,000자(본문 중첩 최대
100자)로 나누면서 모든 청크에 물질명·CAS·출처·항목을 다시 붙입니다. 임베딩
모델은 `BAAI/bge-m3` 그대로입니다. 청킹 코드가 바뀌면 자동 빌더가 새 인덱스를
생성합니다.

같은 질문·CAS 필터·top-5로 두 인덱스를 비교하는 스크립트는 다음과 같습니다.
일반 질문에서 공통 NIOSH 참고표를 제외하고, 약어 질문에서만 해당 표를 검색합니다.

```sh
python -m pipeline.evaluate_chunking \
  --before data/indexes/기존인덱스 --after data/indexes/새인덱스 \
  --output reports/chunking_comparison.md
```

## 구조

- `pipeline/`: 수집·적재·검색 코드와 검증 코드
- `resources/NIOSH.pdf`: NIOSH 원본 PDF
- `data/raw/`: 수집 JSON (Git 제외)
- `data/indexes/`: FAISS 인덱스 (Git 제외)
- `data/catalog.example.json`: 팀 카탈로그 형식 예시이며 실제 데이터가 아닙니다.

## 준비

Python 3.11과 uv가 필요합니다. 이 디렉터리에서 실행합니다. `uv.lock`은 네트워크가 되는 환경에서 생성해 `pyproject.toml`과 함께 검토합니다.

```bash
uv lock
uv sync --locked
```

`resources/NIOSH.pdf`에 원본 PDF를 둡니다. 제공된 다섯 물질 페이지에 맞춘 2007년판 PDF가 필요합니다. 자동 빌더는 저장소 루트 `.env`의 `KOSHA_API_KEY`를 읽습니다. Compose는 키를 `indexer`에만 전달합니다. 첫 인덱스 생성에는 키가 필요합니다. `answer` 명령에는 `OPENAI_API_KEY`도 필요합니다. 실제 키는 Git에 포함하지 않습니다.

## 자동 생성·갱신

`python -m pipeline.build_if_changed`는 `data/indexes/current`에 완성된 인덱스가
있고 입력 파일이 그대로이며 마지막 KOSHA 확인 후 24시간이 지나지 않았다면 즉시
재사용합니다. 인덱스가 없거나 PDF·파이프라인 설정이 바뀌면 새로 생성합니다. 갱신
시점에는 KOSHA를 다시 조회하지만 내용이 같으면 임베딩을 반복하지 않습니다.
`KOSHA_REFRESH_HOURS`로 확인 주기를 바꿀 수 있습니다. API가 일시적으로 실패하면
기존의 유효한 인덱스를 유지합니다. 새 인덱스가 완성되면 `current` 링크를 한 번에
교체하며, 이전 인덱스 폴더도 보존합니다.

```bash
# 저장소 루트에서 처음 실행하거나 Compose를 다시 올릴 때
docker compose --env-file .env -f compose.dev.yaml up --build -d --wait

# KOSHA 변경을 지금 확인하고 싶을 때
docker compose --env-file .env -f compose.dev.yaml run --rm indexer \
  python -m pipeline.build_if_changed --refresh
```

로컬 Python으로 실행할 때는 `datapipeline` 폴더에서 `uv run --locked python -m
pipeline.build_if_changed`를 사용합니다. `docker compose restart`는 완료된 `indexer`
작업을 다시 실행하지 않으므로, 갱신 확인을 포함한 재시작에는 위 `up` 명령이나
수동 갱신 명령을 사용하세요. 새 인덱스가 적용되면 RAG는 다음 요청에서 변경된
`current` 링크를 감지해 새 인덱스를 로드합니다.

## 실행

```bash
# 5개 물질 수집 (기존 파일은 덮어쓰지 않음)
uv run --locked python -m pipeline.pipeline collect --output data/raw/all_five_new.json
# 인덱스 생성 (기존 경로는 덮어쓰지 않음)
uv run --locked python -m pipeline.pipeline index --input data/raw/all_five_new.json --output data/indexes/all_five_new
# 기존 인덱스 검색
uv run --locked python -m pipeline.pipeline search --index data/indexes/all_five --cas 67-64-1 --question '아세톤과 함께 두면 위험한 물질은?' --top-k 5
uv run --locked python -m unittest pipeline.test_pipeline
```

`--pdf`로 PDF 위치를 지정할 수 있습니다. `answer`는 검색 근거를 OpenAI에 전송하고 비용이 발생할 수 있습니다. 신뢰할 수 있는 FAISS 인덱스만 로드하세요.

## 조원과의 연동

```python
from pipeline.pipeline import load_index, search_evidence

store = load_index('data/indexes/all_five')  # 앱에서 한 번 로드 후 재사용
results = search_evidence(store, cas_no='67-64-1', question='함께 두면 위험한 물질은?', intent='incompatibility')
```

`search_evidence`에는 NIOSH 코드 설명을 위해 실제 PDF 경로도 필요합니다. 반환 항목은 `content`, `score`, `metadata`, `selection_reason`, `code_explanations`, `unmatched_codes`입니다. 반응 금기 질문은 관련 항목을 우선 포함하므로 점수 순서와 출력 순서가 다를 수 있습니다.

현재 기존 메타데이터는 `cas_no`, `source`, `section`, `source_url`, `retrieved_at` 등을 사용합니다. 팀에서 제시한 `chunk_id`, `material_id`, `cas_number`, `title`, `url`, `checked_at`과는 다르므로 형식을 합의하고 인덱스를 재생성하기 전까지 동등한 계약으로 가정하지 않습니다. 현재 인덱스는 물질별 분리 대신 5종이 함께 들어 있으며 CAS 필터로 검색합니다. 다섯 물질 이외의 자동 수집은 아직 지원하지 않습니다.
