from sqlalchemy.exc import IntegrityError

from app.ctx import AppCtx
from app.models import postgres as m
from app.utils import fastapi as fastapi_util


async def create_tag() -> None:
    tag = m.Tag(name='test_tag', icon='test_tag_icon')
    AppCtx.current.db.session.add(tag)
    try:
        await AppCtx.current.db.session.commit()
    except IntegrityError as ex:
        print(ex)
        raise fastapi_util.LogicError(
            code="try_again",
            message="there is a race condition. try again.",
        )