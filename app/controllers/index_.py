import logging

from fastapi import APIRouter, Depends, Request
from fastapi.responses import JSONResponse
from sqlalchemy.orm import Session

from app.context import AppContext
from app.utils.fastapi import get_db_session

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get('/_ping', include_in_schema=False)
def ping_get_api(
    request: Request,
    db_session: Session = Depends(get_db_session),
) -> JSONResponse:
    app_context = AppContext.from_app(request.app)

    try:
        if db_session.execute('SELECT 1').scalar() != 1:
            raise RuntimeError('postgresql ping failure')

        if not app_context.redis.ping():
            raise RuntimeError('redis ping failure')

    except Exception:
        logger.warning('Faild to ping backend services', exc_info=True)
        return JSONResponse({'ok': False}, status_code=502)

    return JSONResponse({'ok': True})
