from typing import Optional

from fastapi import Depends
from pydantic import BaseModel, EmailStr, Field, SecretStr
from sqlalchemy.orm import Session
from sqlalchemy.sql import expression as sql_exp

from app.utils import fastapi as fastapi_util

router = fastapi_util.CustomAPIRouter(prefix='/user', tags=['user'])



