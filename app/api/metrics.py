"""
Prometheus metrics endpoint for monitoring
"""
from fastapi import APIRouter, Depends, Request
from fastapi.responses import Response
from prometheus_fastapi_instrumentator import Instrumentator
from app.config import settings
from loguru import logger

router = APIRouter(prefix="/metrics", tags=["monitoring"])


# Initialize Prometheus instrumentator
instrumentator = Instrumentator(
    should_group_status_codes=False,
    should_ignore_untemplated=True,
    should_instrument_requests_inprogress=True,
    excluded_handlers=["/metrics", "/health", "/docs", "/openapi.json"],
    inprogress_name="http_requests_inprogress",
    inprogress_labels=True,
)


def setup_metrics(app):
    """Setup Prometheus metrics instrumentation"""
    instrumentator.instrument(app).expose(app)
    logger.info("Prometheus metrics endpoint configured at /metrics")


@router.get("")
async def get_metrics():
    """
    Prometheus metrics endpoint
    Returns metrics in Prometheus format
    """
    # The instrumentator handles the actual metrics collection
    # This endpoint is exposed by instrumentator.expose()
    pass
