from .auth import router as auth_router
from .index_ import router as index__router
from .music import router as music_router
from .post import router as post_router
from .user import router as user_router

__all__ = ['ALL_ROUTERS']

ALL_ROUTERS = [
    auth_router,
    index__router,
    user_router,
    music_router,
    post_router, 
]
