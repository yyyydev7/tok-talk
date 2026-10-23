"""프로세스 생존과 업무 준비 상태를 구분한다."""

from typing import Literal

from fastapi import APIRouter, status
from pydantic import BaseModel

from app.services.rag import index_path_from_environment, validate_index

router = APIRouter(tags=["health"])


class Liveness(BaseModel):
    status: Literal["alive"] = "alive"


class Readiness(BaseModel):
    status: Literal["degraded"] = "degraded"
    index_ready: bool = False
    inventory_db_ready: bool = False


@router.get("/health/live", response_model=Liveness)
def liveness() -> Liveness:
    """서버 프로세스가 HTTP 요청에 응답할 수 있는지 확인한다."""
    return Liveness()


@router.get(
    "/health",
    response_model=Readiness,
    status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
)
def readiness() -> Readiness:
    """Report index files separately from the still-unimplemented inventory DB."""
    try:
        validate_index(index_path_from_environment())
        index_ready = True
    except (OSError, ValueError):
        index_ready = False
    return Readiness(index_ready=index_ready)
