import logging

from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from sqlalchemy.sql import text

from app.ctx import AppCtx

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get("/_ping", include_in_schema=False)
async def ping_get_api(
    request: Request,
) -> JSONResponse:
    try:
        if (
            await AppCtx.current.db.session.execute(text("SELECT 1"))
        ).scalar() != 1:
            raise RuntimeError("postgresql ping failure")

        if not await AppCtx.current.redis.ping():
            raise RuntimeError("redis ping failure")

    except Exception:
        logger.warning("Faild to ping backend services", exc_info=True)
        return JSONResponse({"ok": False}, status_code=502)

    return JSONResponse({"ok": True})
