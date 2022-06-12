from .auth import router as auth_router
from .digging_log import router as digging_log_router
from .index_ import router as index__router
from .music import router as music_router
from .tag import router as tag_router
from .user import router as user_router

__all__ = ['ALL_ROUTERS']

ALL_ROUTERS = [
    auth_router,
    index__router,
    user_router,
    music_router,
    digging_log_router,
    tag_router,
]
