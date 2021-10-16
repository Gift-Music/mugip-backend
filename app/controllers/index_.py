import logging

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from redis import Redis
from sqlalchemy.orm import Session

from app.utils.misc import get_db_session, get_redis

logger = logging.getLogger(__name__)

router = APIRouter()


@router.get('/_ping', include_in_schema=False)
def ping_get_api(
    db_session: Session = Depends(get_db_session),
    redis: Redis = Depends(get_redis),
) -> JSONResponse:
    try:
        if db_session.execute('SELECT 1').scalar() != 1:
            raise RuntimeError('postgresql ping failure')

        if not redis.ping():
            raise RuntimeError('redis ping failure')

    except Exception:
        logger.warning('Faild to ping backend services', exc_info=True)
        return JSONResponse({'ok': False}, status_code=502)

    return JSONResponse({'ok': True})
