from sqlalchemy import func as sql_func
from sqlalchemy import orm as sql_orm
from sqlalchemy.orm import relationship
from sqlalchemy.schema import Column
from sqlalchemy.sql import expression as sql_exp
from sqlalchemy.sql import sqltypes
from sqlalchemy.sql.schema import ForeignKey, UniqueConstraint

from .base_ import ModelBase


class UserModel(ModelBase):
    __tablename__ = 'user_model'

    id = Column(sqltypes.Integer, primary_key=True)

    email = Column(sqltypes.String, unique=True, nullable=False)
    email_verified_dt = Column(sqltypes.TIMESTAMP(timezone=True), nullable=True)

    nickname = Column(sqltypes.String, nullable=True)
    password = Column(sqltypes.String, nullable=True)

    user_profiles = relationship(
        'UserProfileModel',
        uselist=True,
        back_populates='user',
        cascade='all',
    )

    user_oauth_logins = relationship(
        'UserOauthLoginRelation',
        uselist=True,
        back_populates='user',
        cascade='all',
    )

    user_friends = relationship(
        'UserFriendsRelation',
        uselist=True,
        back_populates='request_user',
        cascade='all',
    )


class UserProfileModel(ModelBase):
    __tablename__ = 'user_profile_model'

    id = Column(sqltypes.Integer, primary_key=True)

    user_id = Column(sqltypes.Integer, ForeignKey(UserModel.id), nullable=False, index=True)
    user = relationship('UserModel', uselist=False)

    nickname = Column(sqltypes.String, nullable=False)

    profile_images = relationship(
        'UserProfileImageLogModel',
        uselist=True,
        back_populates='user_profile',
        cascade='all',
    )

    last_profile_image_url: sql_orm.ColumnProperty


class UserProfileImageLogModel(ModelBase):
    __tablename__ = 'user_profile_image_log_model'

    id = Column(sqltypes.Integer, primary_key=True)

    profile_image_url = Column(sqltypes.String, nullable=False)

    user_profile_id = Column(sqltypes.Integer, ForeignKey(UserProfileModel.id), nullable=False, index=True)
    user_profile = relationship('UserProfileModel', uselist=False)


class UserFriendsRelation(ModelBase):
    __tablename__ = 'user_friends_relation'

    request_user_id = Column(sqltypes.Integer, ForeignKey(UserModel.id), nullable=False, primary_key=True, index=True)
    request_user = relationship('UserModel', uselist=False)

    accept_user_id = Column(sqltypes.Integer, nullable=False, primary_key=True)


class UserOauthLoginRelation(ModelBase):
    __tablename__ = 'user_oauth_relation'

    user_id = Column(sqltypes.Integer, ForeignKey(UserModel.id), nullable=False, primary_key=True, index=True)
    user = relationship('UserModel', uselist=False)

    uid = Column(sqltypes.String, nullable=False, primary_key=True)
    provider_type = Column(sqltypes.Integer, nullable=False)


UniqueConstraint(
    UserOauthLoginRelation.uid,
    UserOauthLoginRelation.provider_type,
)


UserProfileModel.last_profile_image_url = sql_orm.column_property(
    (
        sql_func
        .coalesce(
            sql_exp
            .select([UserProfileImageLogModel.profile_image_url])
            .correlate_except(UserProfileImageLogModel)  # type: ignore
            .where(UserProfileModel.id == UserProfileImageLogModel.user_profile_id)
            .order_by(UserProfileModel.created.desc())
            .limit(1)
            .scalar_subquery(),
            '',
        )
        .label('last_profile_image_url')
    ),
    deferred=True,
)
