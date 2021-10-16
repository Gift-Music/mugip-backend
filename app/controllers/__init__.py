from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from starlette.types import ASGIApp

__all__ = ['SUBAPP_LIST']

from .account import subapp as account_subapp
from .auth import subapp as auth_subapp
from .music import subapp as music_subapp
from .post import subapp as post_subapp

SUBAPP_LIST: list[tuple[str, ASGIApp]] = [
    ('/account', account_subapp),
    ('/auth', auth_subapp),
    ('/music', music_subapp),
    ('/post', post_subapp),
]
