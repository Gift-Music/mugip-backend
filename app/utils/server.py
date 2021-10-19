from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, Callable, Dict, Literal, Optional, get_type_hints

from fastapi import APIRouter, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel

if TYPE_CHECKING:
    from starlette.types import ASGIApp, Message, Receive, Scope, Send


logger = logging.getLogger(__name__)


class _ManagedError(Exception):
    def __init__(self, code: str, message: str, detail: dict[str, Any] | None = None) -> None:
        self.code = code
        self.message = message
        self.detail = detail


class AuthError(_ManagedError):
    pass


class LogicError(_ManagedError):
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


class _ServerErrorResponseModel(BaseModel):
    code: Literal['server_error']
    message: str


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
        'description': 'Unexpected server error',
        'model': _ServerErrorResponseModel,
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
        except Exception:
            logger.exception('Internal server error')

            err_response = JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    'code': 'server_error',
                    'message': 'unexpected server error',
                    'detail': None,
                }
            )

        if not response_started:
            await err_response(scope, receive, send)


class CustomAPIRouter(APIRouter):
    def add_api_route(self, path: str, endpoint: Callable[..., Any], **kwargs: Any) -> None:
        if kwargs.get('response_model') is None:
            kwargs['response_model'] = get_type_hints(endpoint).get('return')
        return super().add_api_route(path, endpoint, **kwargs)
