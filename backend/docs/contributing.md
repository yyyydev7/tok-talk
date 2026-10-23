# 팀 협업 규칙

| 담당 | 주 작업 위치 | 공유 산출물 |
| --- | --- | --- |
| 이연주 | datapipeline/pipeline, datapipeline/data | 카탈로그·청크·인덱스·출처표 |
| 김대훈 | rag/app/services | 검색·답변·프롬프트·RAG 평가 |
| 정수민 | backend/src, backend/contracts, backend/db, rag/app/api·security·repositories | 인증·API·재고 조회 계약과 구현 |
| 강도희 | frontend | 로그인 연동·질문·출처·재고 화면 |
| 손연우 | backend/deploy, backend/scripts, 루트 compose.*.yaml | 실행 환경·DB 적용 절차·배포 |

폴더는 소유권 경계가 아니라 주 담당 범위입니다. 연관 변경은 함께 검토합니다.

## Git 작업

- 이 프로젝트 디렉터리를 팀 저장소 루트로 사용합니다.
- feat/작업명 등의 짧은 브랜치에서 작업하고 PR로 병합합니다.
- 다른 팀원 1명 검토를 병합 조건으로 설정합니다. CI 활성화 후에는 검사 통과도 조건에 추가합니다.
- PR에 변경 목적, API·데이터 변경, 확인 결과를 적습니다.
- 계약을 바꾸면 backend/contracts와 호출하는 화면을 같은 PR에서 수정합니다.
- dependency manifest와 lock 파일은 같이 변경합니다.
- 개인 .env, 비밀키, DB 볼륨, 생성 인덱스를 커밋하지 않습니다.

## 테스트 위치와 기준

서비스 내부 검사는 각 서비스의 tests 또는 src/test에 둡니다.
서비스 간 검사는 backend/tests/e2e에 둡니다.
외부 LLM을 호출하지 않는 검사를 기본 CI로 사용합니다.
실제 LLM 평가는 별도 실행하고 모델·프롬프트·인덱스 버전을 결과와 함께 기록합니다.

목표 평가셋은 5종 x 근거 질문 3개 + 실패 사례 5개 = 최소 20쌍입니다.
JWT 오류, 다른 물질 근거 미노출, 복수·미인식, 재고 빈 목록·DB 장애,
재고 장애 중 RAG 화면 유지도 별도로 확인합니다.
현재 smoke 검사는 개발 골격의 기동만 검사하며 이 기능들의 완료를 보장하지 않습니다.

최상위 폴더 4개를 유지하기 위해 CI 설정은 backend/deploy/github-actions.yml에 템플릿으로 보관합니다.
이 위치에서는 자동 실행되지 않습니다. 추후 활성화하려면 .github/workflows/ci.yml로 옮겨야 합니다.
