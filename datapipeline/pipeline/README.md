# 문서 적재 파이프라인

`pipeline.py`는 KOSHA API 수집, NIOSH PDF 수집, 청킹·임베딩·FAISS 생성 및 검색 함수를 제공합니다. `niosh_pdf.py`는 PDF에서 물질별 항목을 추출하고 `niosh_codes.py`는 관련 공식 코드 설명을 연결합니다. `test_msds_api.py`에는 공단 API 연결 함수가 있습니다.

설치, 실행 및 산출물 제한 사항은 상위 `README.md`를 참고하세요. 생성 인덱스와 원본 PDF는 팀이 정한 산출물 저장 위치를 통해 별도 전달합니다.
