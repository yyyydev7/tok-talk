# 청킹 변경 전후 검색 평가

같은 BGE-M3 임베딩, 동일 질문·CAS 필터·top-5 기준입니다. 일반 질문은 공통 참고표를 제외하고, 약어 질문만 해당 표를 검색합니다. 출처 항목 적중은 답변의 사실 정확도를 보증하지 않습니다.

- 기존 인덱스: `/Users/daehun/Desktop/mini_team_project/tok-talk/datapipeline/data/indexes/build-1792740406-5e660031`
- 새 인덱스: `/Users/daehun/Desktop/mini_team_project/tok-talk/datapipeline/data/indexes/chunking_v2_candidate_20261026`

## 청크 품질

| 지표 | 변경 전 | 변경 후 |
| --- | ---: | ---: |
| 전체 청크 | 715 | 553 |
| 자료없음 청크 | 107 | 0 |
| 본문 없는 머리글 청크 | 66 | 0 |
| 본문에 CAS가 없는 청크 | 152 | 0 |
| NIOSH 공통 참고표 청크 | 215 | 160 |

## 같은 질문의 검색 결과

`순위`는 기대 항목이 처음 검색된 위치입니다. `-`는 상위 5개에 없음을 뜻합니다.

| 질문 | 기대 항목 | 전 순위 | 후 순위 |
| --- | --- | ---: | ---: |
| 아세톤 노출 경로 | Exposure Routes, Symptoms, Target Organs | 1 | 1 |
| 아세톤 약어 Con | Exposure and symptoms abbreviations | 1 | 1 |
| 아세톤 보관 | 취급 및 저장방법 | 2 | 2 |
| 메탄올 보호구 | 노출방지 및 개인보호구 | 1 | 1 |
| 메탄올 응급조치 | 응급조치요령 | 1 | 1 |
| 톨루엔 건강 영향 | 독성에 관한 정보 | 1 | 1 |
| 톨루엔 노출 감소 | 노출방지 및 개인보호구 | 1 | 1 |
| 에탄올 소화제 | 폭발·화재시 대처방법 | 1 | 1 |
| 아세트산 피부 증상 | 유해성·위험성 | 3 | 3 |

기대 항목 top-5 적중: **9/9 → 9/9**

청킹 변경만으로 이 9개 질문의 항목 적중률이 상승했다고 주장할 수는 없습니다.
이번 개선에서 확인된 효과는 불필요한 청크 제거와 분할 청크의 문맥 보존입니다.
NIOSH 노출·증상 약어표에서 현재 지원하는 **34개 코드와 뜻이 각각 같은 청크에
들어 있는 것**도 확인했습니다. 공통 참고표의 물질별 중복 자체는 남아 있습니다.

## 새 인덱스 실제 답변 확인

동일한 다섯 복합 질문을 새 인덱스와 현재 RAG 코드로 한 번씩 실행했습니다.
아세톤(노출 경로·보관), 메탄올(보호구·응급조치), 톨루엔(건강 영향·노출 감소),
에탄올(화재 위험·대응), 아세트산(피부 증상·응급조치) 모두 두 항목에 답했고
`needs_review=false`였습니다. 이는 시연 질문에 대한 수동 점검이며 전체 답변
정확도나 청킹 단독의 개선율을 뜻하지 않습니다.

## 상세 검색 항목

### 아세톤 노출 경로

- 변경 전: Exposure Routes, Symptoms, Target Organs, 유해성·위험성, 응급조치요령, Personal Protection/Sanitation, 노출방지 및 개인보호구
- 변경 후: Exposure Routes, Symptoms, Target Organs, 유해성·위험성, 응급조치요령, Personal Protection/Sanitation, 노출방지 및 개인보호구

### 아세톤 약어 Con

- 변경 전: Exposure and symptoms abbreviations, Exposure and symptoms abbreviations, Exposure and symptoms abbreviations, Exposure and symptoms abbreviations, Exposure and symptoms abbreviations
- 변경 후: Exposure and symptoms abbreviations, Exposure and symptoms abbreviations, Exposure and symptoms abbreviations, Exposure and symptoms abbreviations

### 아세톤 보관

- 변경 전: 유해성·위험성, 취급 및 저장방법, 취급 및 저장방법, 유해성·위험성, 노출방지 및 개인보호구
- 변경 후: 유해성·위험성, 취급 및 저장방법, 취급 및 저장방법, 유해성·위험성, 노출방지 및 개인보호구

### 메탄올 보호구

- 변경 전: 노출방지 및 개인보호구, 노출방지 및 개인보호구, 노출방지 및 개인보호구, 폭발·화재시 대처방법, 누출사고시 대처방법
- 변경 후: 노출방지 및 개인보호구, 노출방지 및 개인보호구, 노출방지 및 개인보호구, 폭발·화재시 대처방법, 누출사고시 대처방법

### 메탄올 응급조치

- 변경 전: 응급조치요령, 응급조치요령, Personal Protection/Sanitation, 노출방지 및 개인보호구, First Aid
- 변경 후: 응급조치요령, 응급조치요령, Personal Protection/Sanitation, 노출방지 및 개인보호구, First Aid

### 톨루엔 건강 영향

- 변경 전: 독성에 관한 정보, Exposure Routes, Symptoms, Target Organs, 독성에 관한 정보, 그 밖의 참고사항, 독성에 관한 정보
- 변경 후: 독성에 관한 정보, Exposure Routes, Symptoms, Target Organs, 독성에 관한 정보, 그 밖의 참고사항, 독성에 관한 정보

### 톨루엔 노출 감소

- 변경 전: 노출방지 및 개인보호구, 노출방지 및 개인보호구, 취급 및 저장방법, 유해성·위험성, 독성에 관한 정보
- 변경 후: 노출방지 및 개인보호구, 노출방지 및 개인보호구, 취급 및 저장방법, 유해성·위험성, 독성에 관한 정보

### 에탄올 소화제

- 변경 전: 폭발·화재시 대처방법, 폭발·화재시 대처방법, 누출사고시 대처방법, 누출사고시 대처방법, 폭발·화재시 대처방법
- 변경 후: 폭발·화재시 대처방법, 폭발·화재시 대처방법, 누출사고시 대처방법, 누출사고시 대처방법, 폭발·화재시 대처방법

### 아세트산 피부 증상

- 변경 전: Exposure Routes, Symptoms, Target Organs, 응급조치요령, 유해성·위험성, 그 밖의 참고사항, 독성에 관한 정보
- 변경 후: Exposure Routes, Symptoms, Target Organs, 응급조치요령, 유해성·위험성, 그 밖의 참고사항, 독성에 관한 정보
