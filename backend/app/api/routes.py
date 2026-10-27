"""Router layer: HTTP only — validation, status codes, streaming. No business logic."""

import logging

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse

from app.api.rate_limit import rate_limit
from app.api.schemas import ExtractTextRequest, ExtractTextResponse, ScanRequest
from app.services.extract_service import BadImageError, ExtractService
from app.services.scan_service import ScanService

log = logging.getLogger(__name__)
router = APIRouter(prefix="/api")


@router.get("/health")
async def health() -> dict:
    return {"status": "ok"}


@router.post("/scan", dependencies=[Depends(rate_limit)])
async def scan(req: ScanRequest) -> StreamingResponse:
    service = ScanService()
    return StreamingResponse(
        service.scan_stream(req),
        media_type="text/event-stream",
        headers={"X-Accel-Buffering": "no", "Cache-Control": "no-cache"},
    )


@router.post("/extract-text", dependencies=[Depends(rate_limit)])
async def extract_text(req: ExtractTextRequest) -> ExtractTextResponse:
    try:
        text = await ExtractService().extract_text(req.image)
    except BadImageError as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    except Exception as e:
        log.exception("extract-text failed")
        raise HTTPException(status_code=502, detail="อ่านภาพไม่สำเร็จ ลองใหม่อีกครั้ง") from e
    return ExtractTextResponse(text=text)
