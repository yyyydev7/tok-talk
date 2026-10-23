# 파이프라인 데이터

프로젝트 루트 기준 `datapipeline/data/`입니다.

catalog.example.json은 API v0.3에 제시된 아세톤 항목을 옮긴 형식 예시입니다.
실제로 수집·확인한 카탈로그나 적재된 인덱스가 아니며 서버는 이 파일을 읽지 않습니다.

데이터 담당자가 NIOSH 5종(아세톤·에탄올·메탄올·톨루엔·아세트산)을 확인하고
공통 material_id, CAS, 한글명, 동의어, 공식 원문 URL을 확정해야 합니다.
선정 페이지의 이용조건·권리표시 확인 기록도 남깁니다.

## 산출물

- 원문 보관: `datapipeline/data/raw/` (생성 파일은 Git 제외)
- 생성 인덱스: `datapipeline/data/indexes/` (생성 파일은 Git 제외)
- 출처표: 원문 URL, 항목, 팀의 수집·확인일 checked_at
- 청크: chunk_id, material_id, cas_number, title, section, url, checked_at
- 인덱스 명세: 버전, 원문 해시, 청킹 규칙, 임베딩 모델·차원·검색 거리, 생성 명령

checked_at은 팀의 확인일이며 원문 개정일이 아닙니다.
확인하지 않은 날짜를 채워 넣지 않습니다.
`rag/` 런타임은 적재를 마친 인덱스를 읽기 전용으로 사용합니다.
재고는 DB에서 직접 조회하며 이 폴더나 LLM 근거에 넣지 않습니다.
