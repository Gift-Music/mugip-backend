from typing import Any, Dict, List, Literal, Optional

import jsonschema
from fastapi import Depends, Response
from pydantic import BaseModel, Field, validator
from sqlalchemy.orm import Session
from sqlalchemy.sql import expression as sql_exp

from app.models import postgres as m
from app.utils import fastapi as fastapi_util
from app.utils.auth import user_auth_required
from app.utils.fastapi import get_db_session
from app.utils.filter_expr import build_filter_expr

router = fastapi_util.CustomAPIRouter(prefix="/tag", tags=["tag"])


class _TagPostRequest(BaseModel):
    name: str
    icon: str


@router.post("/")
def tag_post_api(
    q: _TagPostRequest,
    db_session: Session = Depends(get_db_session),
    _: int = Depends(user_auth_required),
) -> None:
    is_tag_exists: bool = db_session.scalar(
        sql_exp.exists().where(m.Tag.name == q.name).select()
    )

    if is_tag_exists:
        raise fastapi_util.LogicError(
            code="model_already_eixsts",
            message="model is already exists",
        )

    db_session.add(
        m.Tag(
            name=q.name,
            icon=q.icon,
        )
    )

    db_session.commit()


_TagSearchRequestFilterExpr = build_filter_expr(
    {
        "name": {"type": "string"},
    }
)


class _TagSearchRequest(BaseModel):
    filter_expr: Optional[Dict[str, Any]] = Field(
        description=_TagSearchRequestFilterExpr.description
    )
    sort_by_key: Optional[Literal["name", "created", "updated"]]
    sort_by_order: Optional[Literal["asc", "desc"]]
    offset: int = Field(ge=0)
    count: int = Field(ge=1, le=100)

    @validator("filter_expr")
    def validator_filter_expr(
        cls, value: Optional[Dict[str, Any]]
    ) -> Optional[Dict[str, Any]]:
        if value is not None:
            try:
                jsonschema.validate(
                    value,
                    _TagSearchRequestFilterExpr.schema,
                    format_checker=jsonschema.draft7_format_checker,
                )
            except jsonschema.exceptions.ValidationError as err:
                raise ValueError(err.message)
        return value


class _TagSearchResponse(BaseModel):
    name: str
    icon: str

    class Config:
        orm_mode = True


@router.post("/search")
def tag_search_api(
    q: _TagSearchRequest,
    response: Response,
    db_session: Session = Depends(get_db_session),
    _: int = Depends(user_auth_required),
) -> List[_TagSearchResponse]:
    tags_query = db_session.query(m.Tag)

    if q.filter_expr is not None:
        tags_query = tags_query.filter(
            _TagSearchRequestFilterExpr.to_query(
                q.filter_expr,
                {
                    "name": m.Tag.name.ilike,
                },
            )
        )

    sort_by_col = {
        "name": m.Tag.name,
        "created": m.Tag.created,
        "updated": m.Tag.updated,
    }[q.sort_by_key or "id"]

    sort_by_order_exp = {
        "asc": sql_exp.asc,
        "desc": sql_exp.desc,
    }[q.sort_by_order or "asc"]

    tags_count = tags_query.count()
    response.headers["x-total"] = str(tags_count)

    tags = (
        tags_query.order_by(sort_by_order_exp(sort_by_col))  # type: ignore
        .slice(q.offset, q.offset + q.count)
        .all()
    )

    return [_TagSearchResponse.from_orm(tag) for tag in tags]
