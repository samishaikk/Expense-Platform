import logging

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse, Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest
from sqlalchemy import text
from sqlalchemy.orm import Session
from app.db import get_db

logger = logging.getLogger("app.ops")
router = APIRouter(tags=["ops"])

@router.get("/health")
def health():
    return {"status": "ok"}

@router.get("/ready")
def ready(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
    except Exception:
        logger.error("database readiness check failed", exc_info=True)
        return JSONResponse(
            {"status": "unavailable", "database": "down"}, status_code=503
        )
    return {"status": "ready", "database": "up"}


@router.get("/metrics", include_in_schema=False)
def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)