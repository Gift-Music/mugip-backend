from pydantic import BaseModel

from app.models.services.music import Track


class DiggingUser(BaseModel):
    id: int
    name: str


class DiggingTag(BaseModel):
    name: str
    icon: str


class DiggingLog(BaseModel):
    track: Track
    tag: DiggingTag
