from typing import Optional

from fastapi import Depends
from pydantic import BaseModel, EmailStr, Field, SecretStr
from sqlalchemy.orm import Session
from sqlalchemy.sql import expression as sql_exp

from app import models as m
from app.utils import server as server_utils
from app.utils.misc import get_db_session

router = server_utils.CustomAPIRouter(prefix='/user', tags=['user'])
