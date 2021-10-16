import fastapi

from app.utils.fastapi import FASTAPI_RESPONSES

__all__ = ['subapp']

subapp = fastapi.FastAPI(responses=FASTAPI_RESPONSES)

_ALL_ROUTERS = []

for router in _ALL_ROUTERS:
    subapp.include_router(router)
