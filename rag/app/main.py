"""FastAPI 실행 진입점. 업무 API는 계약을 확정한 뒤 연결한다."""

from fastapi import FastAPI

from app.api.health import router as health_router


def create_app() -> FastAPI:
    application = FastAPI(
        title="톡talk API",
        version="0.1.0",
        description="팀 개발 환경의 시작점. 현재 생존 및 준비 상태 API만 제공한다.",
    )
    application.include_router(health_router)
    return application


app = create_app()
