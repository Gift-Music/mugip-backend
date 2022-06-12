from __future__ import annotations

from functools import cached_property
from typing import TYPE_CHECKING

from fastapi import FastAPI

from .auth import AuthAppUtil
from .email import EmailAppUtil
from .oauth import SocialAppUtil
from .remote_file import RemoteFileAppUtil
from .spotify import SpotifyAppUtil

if TYPE_CHECKING:
    from app.context import AppContext


class AppUtils:
    def __init__(self, app: FastAPI) -> None:
        self.app = app

    @property
    def _app_context(self) -> AppContext:
        from app.context import AppContext
        return AppContext.from_app(self.app)

    @cached_property
    def auth(self) -> AuthAppUtil:
        return AuthAppUtil(self._app_context)

    @cached_property
    def email(self) -> EmailAppUtil:
        return EmailAppUtil(self._app_context)

    @cached_property
    def social(self) -> SocialAppUtil:
        return SocialAppUtil(self._app_context)

    @cached_property
    def spotify(self) -> SpotifyAppUtil:
        return SpotifyAppUtil(self._app_context)

    @cached_property
    def remote_file(self) -> RemoteFileAppUtil:
        return RemoteFileAppUtil(self._app_context)
