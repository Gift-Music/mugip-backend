from __future__ import annotations

import uuid
from typing import Any, Callable, NamedTuple

from sqlalchemy.sql import expression as sql_exp
from sqlalchemy.sql.elements import BooleanClauseList
from sqlalchemy.sql.expression import ClauseElement


class FilterExpr(NamedTuple):
    schema: dict[str, Any]
    to_query: Callable[
        [dict[str, Any], dict[str, Callable[[Any], BooleanClauseList]]], ClauseElement
    ]
    description: str


def _filter_expr_to_query(
    filter_expr: dict[str, Any],
    key_func_dict: dict[str, Callable[[Any], BooleanClauseList]],
) -> ClauseElement:
    expr_list = []
    for key, value_or_exprs in filter_expr.items():
        if key == "$and":
            assert isinstance(value_or_exprs, list)
            expr_list.append(
                sql_exp.and_(
                    *[
                        _filter_expr_to_query(expr, key_func_dict)
                        for expr in value_or_exprs
                        if expr
                    ]
                )
            )
        elif key == "$or":
            assert isinstance(value_or_exprs, list)
            expr_list.append(
                sql_exp.or_(
                    *[
                        _filter_expr_to_query(expr, key_func_dict)
                        for expr in value_or_exprs
                        if expr
                    ]
                )
            )
        elif key == "$not":
            assert isinstance(value_or_exprs, dict)
            expr_list.append(
                sql_exp.not_(
                    _filter_expr_to_query(value_or_exprs, key_func_dict)
                )  # type: ignore
            )
        elif key in key_func_dict:
            expr_list.append(key_func_dict[key](value_or_exprs))
        else:
            raise RuntimeError("Func for the key is not defined", key)

    if not expr_list:
        return sql_exp.true()

    return sql_exp.and_(*expr_list)


def _filter_expr_to_schema(
    filter_key_to_schema: dict[str, dict[str, Any]]
) -> dict[str, Any]:
    random_scheme_id = uuid.uuid4().hex

    return {
        "$id": random_scheme_id,
        "type": "object",
        "properties": {
            "$and": {
                "type": "array",
                "items": {"$ref": random_scheme_id},
            },
            "$or": {
                "type": "array",
                "items": {"$ref": random_scheme_id},
            },
            "$not": {"$ref": random_scheme_id},
            **filter_key_to_schema,
        },
        "additionalProperties": False,
    }


def build_filter_expr(filter_key_to_schema: dict[str, dict[str, Any]]) -> FilterExpr:
    return FilterExpr(
        schema=_filter_expr_to_schema(filter_key_to_schema),
        to_query=_filter_expr_to_query,
        description="filtering on %s"
        % ", ".join(
            f'`{key}:{expr.get("type", "any")}`'
            for key, expr in filter_key_to_schema.items()
        ),
    )
