"""
Health Check Endpoint
"""

from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter(tags=["Health"])


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str


@router.get("/health", response_model=HealthResponse)
async def health_check():
    """
    Health check endpoint for Docker healthcheck
    """
    return HealthResponse(
        status="healthy",
        service="Sistema Deus da Saúde",
        version="1.0.0"
    )
