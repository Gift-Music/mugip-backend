from sqlalchemy import func as sql_func
from sqlalchemy import orm as sql_orm
from sqlalchemy.orm import relationship
from sqlalchemy.schema import Column
from sqlalchemy.sql import expression as sql_exp
from sqlalchemy.sql import sqltypes
from sqlalchemy.sql.schema import ForeignKey, UniqueConstraint

from .base_ import ModelBase


class User(ModelBase):
    __tablename__ = 'user'

    id = Column(sqltypes.Integer, primary_key=True)

    email = Column(sqltypes.String, unique=True, nullable=True)
    email_verified_dt = Column(sqltypes.TIMESTAMP(timezone=True), nullable=True)

    nickname = Column(sqltypes.String, nullable=True)
    password = Column(sqltypes.String, nullable=True)

    user_oauth_logins = relationship(
        'UserOauthLogin',
        uselist=True,
        back_populates='user',
        cascade='all',
    )

    followers = relationship(
        'UserFollow',
        uselist=True,
        back_populates='target_user',
        cascade='all',
        primaryjoin='(User.id==UserFollow.target_user_id)',
    )

    followings = relationship(
        'UserFollow',
        uselist=True,
        back_populates='request_user',
        cascade='all',
        primaryjoin='(User.id==UserFollow.request_user_id)',
    )

    profile_images = relationship(
        'UserProfileImageLog',
        uselist=True,
        back_populates='user',
        cascade='all',
    )

    last_profile_image_url: sql_orm.ColumnProperty


class UserProfileImageLog(ModelBase):
    __tablename__ = 'user_profile_image_log'

    id = Column(sqltypes.Integer, primary_key=True)

    profile_image_url = Column(sqltypes.String, nullable=False)

    user_id = Column(sqltypes.Integer, ForeignKey(User.id), nullable=False, index=True)
    user = relationship('User', uselist=False)


class UserFollow(ModelBase):
    __tablename__ = 'user_follow'

    request_user_id = Column(sqltypes.Integer, ForeignKey(User.id), nullable=False, primary_key=True, index=True)
    request_user = relationship('User', uselist=False, foreign_keys=[request_user_id])

    target_user_id = Column(sqltypes.Integer, ForeignKey(User.id), nullable=False, primary_key=True)
    target_user = relationship('User', uselist=False, foreign_keys=[target_user_id])


class UserOauthLogin(ModelBase):
    __tablename__ = 'user_oauth_login'

    user_id = Column(sqltypes.Integer, ForeignKey(User.id), nullable=False, primary_key=True, index=True)
    user = relationship('User', uselist=False)

    uid = Column(sqltypes.String, nullable=False, primary_key=True)
    provider_type = Column(sqltypes.Integer, nullable=False)


UniqueConstraint(
    UserOauthLogin.uid,
    UserOauthLogin.provider_type,
)


User.last_profile_image_url = sql_orm.column_property(
    (
        sql_func
        .coalesce(
            sql_exp
            .select([UserProfileImageLog.profile_image_url])
            .correlate_except(UserProfileImageLog)  # type: ignore
            .where(User.id == UserProfileImageLog.user_id)
            .order_by(User.created.desc())
            .limit(1)
            .scalar_subquery(),
            '',
        )
        .label('last_profile_image_url')
    ),
    deferred=True,
)
