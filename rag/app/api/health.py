"""프로세스 생존과 업무 준비 상태를 구분한다."""

from typing import Literal

from fastapi import APIRouter, status
from pydantic import BaseModel

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
    """인덱스와 재고 DB를 연결하기 전까지 준비되지 않은 상태를 반환한다."""
    return Readiness()
