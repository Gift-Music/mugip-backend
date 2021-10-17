from sqlalchemy import func as sql_func
from sqlalchemy import orm as sql_orm
from sqlalchemy.orm import relationship
from sqlalchemy.schema import Column
from sqlalchemy.sql import expression as sql_exp
from sqlalchemy.sql import sqltypes
from sqlalchemy.sql.schema import UniqueConstraint

from ._base import ModelBase


class UserModel(ModelBase):
    __tablename__ = 'user_model'

    id = Column(sqltypes.Integer, primary_key=True)

    email = Column(sqltypes.String, unique=True, nullable=False)
    password = Column(sqltypes.String, nullable=False)

    user_profiles = relationship(
        'UserProfileModel',
        uselist=True,
        back_populates='user',
        cascade='all',
        primaryjoin='foreign(UserModel.id) == UserProfileModel.user_id',
    )

    user_oauth_logins = relationship(
        'UserOauthLoginRelation',
        uselist=True,
        back_populates='user',
        cascade='all',
        primaryjoin='foreign(UserModel.id) == UserOauthLoginRelation.user_id',
    )

    user_friends = relationship(
        'UserFriendsRelation',
        uselist=True,
        cascade='all',
        primaryjoin='foreign(UserModel.id) == UserFriendsRelation.requester_id',
    )


class UserProfileModel(ModelBase):
    __tablename__ = 'user_profile_model'

    id = Column(sqltypes.Integer, primary_key=True)

    user_id = Column(sqltypes.Integer, nullable=False)
    user = relationship(
        'UserModel',
        uselist=False,
        primaryjoin='foreign(UserProfileModel.user_id) == UserModel.id',
    )

    profile_images = relationship(
        'UserProfileImageLogModel',
        uselist=True,
        back_populates='user_profile',
        primaryjoin='foreign(UserProfileModel.id) == UserProfileImageLogModel.user_profile_id',
    )

    last_profile_image_url: sql_orm.ColumnProperty


class UserProfileImageLogModel(ModelBase):
    __tablename__ = 'user_profile_image_log_model'

    id = Column(sqltypes.Integer, primary_key=True)

    profile_image_url = Column(sqltypes.String, nullable=False)

    user_profile_id = Column(sqltypes.Integer, nullable=False)


class UserFriendsRelation(ModelBase):
    __tablename__ = 'user_friends_relation'

    requester_id = Column(sqltypes.Integer, nullable=False, primary_key=True)

    acceptor_id = Column(sqltypes.Integer, nullable=False, primary_key=True)
    acceptor = relationship(
        'UserModel',
        uselist=False,
        primaryjoin='foreign(UserModel.id) == UserFriendsRelation.acceptor_id',
    )


class UserOauthLoginRelation(ModelBase):
    __tablename__ = 'user_oauth_relation'

    user_id = Column(sqltypes.Integer, nullable=False, primary_key=True)

    uid = Column(sqltypes.String, nullable=False)
    provider_type = Column(sqltypes.Integer, nullable=False, primary_key=True)


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
            .as_scalar(),
            '',
        )
        .label('last_profile_image_url')
    ),
    deferred=True,
)
