import time
from fastapi import APIRouter, HTTPException, Query

router = APIRouter(prefix="/debug", tags=["fault-injection"])

@router.get("/fault")
def inject_fault(
    delay_ms: int = Query(0, ge=0, le=5000),
    fail: bool = False,
):
    if delay_ms:
        time.sleep(delay_ms / 1000)
    if fail:
        raise HTTPException(status_code=500, detail="injected fault")
    return {"delay_ms": delay_ms, "fail": fail}