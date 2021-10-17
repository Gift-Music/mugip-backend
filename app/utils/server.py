from __future__ import annotations

import logging
from typing import Any, Callable, Dict, Literal, Optional, get_type_hints

from fastapi import APIRouter
from pydantic import BaseModel

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


class CustomAPIRouter(APIRouter):
    def add_api_route(self, path: str, endpoint: Callable[..., Any], **kwargs: Any) -> None:
        if kwargs.get('response_model') is None:
            kwargs['response_model'] = get_type_hints(endpoint).get('return')
        return super().add_api_route(path, endpoint, **kwargs)
