# 데이터 파이프라인

KOSHA MSDS API와 NIOSH Pocket Guide PDF를 사용해 5개 물질을 수집·정제하고 BGE-M3 및 FAISS 인덱스를 생성합니다. NIOSH 웹페이지는 수집하지 않습니다. 파이프라인과 RAG 서버는 독립적으로 실행하며, 서버 시작 시 수집 또는 인덱싱을 수행하지 않습니다.

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

`resources/NIOSH.pdf`에 원본 PDF를 둡니다. 제공된 다섯 물질 페이지에 맞춘 2007년판 PDF가 필요합니다. API 수집 시 `datapipeline/.env`에 `KOSHA_API_KEY`를 설정합니다. `answer` 명령에는 `OPENAI_API_KEY`도 필요합니다. 실제 키는 Git에 포함하지 않습니다.

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
