from __future__ import annotations

import asyncio
import dataclasses
import logging
from concurrent.futures import ThreadPoolExecutor
from typing import TYPE_CHECKING, Any, AsyncIterator, Callable, Dict, Optional, get_type_hints

from fastapi import APIRouter, Request, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel
from sqlalchemy.orm import Session
from starlette.types import ASGIApp, Message, Receive, Scope, Send

from app.context import AppContext

if TYPE_CHECKING:
    from app.settings import AppSettings
    from app.utils import AppUtils

logger = logging.getLogger(__name__)

_SQLA_SESSION_CLOSER_THREADPOOL = ThreadPoolExecutor(1)


@dataclasses.dataclass
class _ManagedError(Exception):
    code: str
    message: str
    detail: dict[str, Any] | None = None


class AuthError(_ManagedError):
    pass


class LogicError(_ManagedError):
    pass


class NotFoundError(_ManagedError):
    pass


class _ErrorResponseModel(BaseModel):
    class ErrorDetail(BaseModel):
        code: str
        message: str
        detail: Optional[Dict[str, Any]] = None

    detail: _ErrorResponseModel.ErrorDetail

    @staticmethod
    def from_exc(exc: _ManagedError) -> _ErrorResponseModel:
        return _ErrorResponseModel(
            detail=_ErrorResponseModel.ErrorDetail(
                code=exc.code,
                message=exc.message,
                detail=exc.detail,
            ),
        )


_ErrorResponseModel.update_forward_refs()


FASTAPI_RESPONSES: dict[int | str, dict[str, Any]] = {
    403: {
        'description': 'Auth Error',
        'model': _ErrorResponseModel,
    },
    409: {
        'description': 'Logical error',
        'model': _ErrorResponseModel,
    },
    500: {
        'description': 'Server error',
        'model': _ErrorResponseModel,
    }
}


class ErrorReportAndForgetMiddleware:
    def __init__(self, app: ASGIApp) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        response_started = False

        async def _send(message: Message) -> None:
            nonlocal response_started

            if message['type'] == 'http.response.start':
                response_started = True

            await send(message)

        try:
            await self.app(scope, receive, _send)
            return

        except AuthError as err:
            err_response = JSONResponse(
                status_code=status.HTTP_403_FORBIDDEN,
                content=_ErrorResponseModel.from_exc(err).dict()
            )
        except LogicError as err:
            err_response = JSONResponse(
                status_code=status.HTTP_409_CONFLICT,
                content=_ErrorResponseModel.from_exc(err).dict()
            )
        except NotFoundError as err:
            err_response = JSONResponse(
                status_code=status.HTTP_404_NOT_FOUND,
                content=_ErrorResponseModel.from_exc(err).dict()
            )
        except Exception:
            logger.exception('Internal server error')

            err_response = JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content=_ErrorResponseModel(
                    detail=_ErrorResponseModel.ErrorDetail(
                        code='server_error',
                        message='unexpected server error',
                    )
                ).dict()
            )

        if not response_started:
            await err_response(scope, receive, send)


class CustomAPIRouter(APIRouter):
    def add_api_route(self, path: str, endpoint: Callable[..., Any], **kwargs: Any) -> None:
        if kwargs.get('response_model') is None:
            kwargs['response_model'] = get_type_hints(endpoint).get('return')
        return super().add_api_route(path, endpoint, **kwargs)


async def get_app_settings(request: Request) -> AppSettings:
    return AppContext.from_app(request.app).app_settings


async def get_app_utils(request: Request) -> AppUtils:
    return AppContext.from_app(request.app).app_utils


async def get_db_session(request: Request) -> AsyncIterator[Session]:
    # NOTE : This function is called by `fastapi.Depends` and it is not
    #        guaranteed to be in the same thread to the routing function.
    #        Therefore, we do not use scoped_session with ThreadLocal.
    db_engine = AppContext.from_app(request.app).db_engine

    loop = asyncio.get_event_loop()

    session = Session(db_engine)

    try:
        yield session
    finally:
        await loop.run_in_executor(
            _SQLA_SESSION_CLOSER_THREADPOOL,
            session.close,
        )


async def get_client_ip(request: Request) -> str:
    x_forwarded_for = request.headers.get('X-FORWARDED-FOR')
    return (  # type: ignore
        (x_forwarded_for.split(',')[0]).split(':')[0]
        if x_forwarded_for
        else request.client.host
    )
