# 서비스 간 확인

개발 Compose를 실행한 뒤 프로젝트 루트에서 다음 명령을 실행합니다.

    python3 infra/tests/e2e/smoke.py

포트를 바꿨다면 --frontend, --backend, --rag 인자로 전체 기본 주소를 전달하세요.
이 검사는 화면 제공·프로세스 생존·미구현 기능의 503·알 수 없는 경로의 404를 확인합니다.
로그인·RAG·재고 기능에 대한 통합 테스트는 해당 기능 구현과 함께 추가합니다.

데모 Compose를 실행했다면 프록시를 통한 release 화면과 서비스별 전달 경로를 확인합니다.

    python3 infra/tests/e2e/proxy_smoke.py

포트를 바꿨다면 --base http://localhost:변경포트를 전달하세요.
아직 없는 기능 API의 404를 예상하므로, 실제 기능 구현 시 이 검사도 갱신해야 합니다.
