'''initial migration

Revision ID: 67c418ad84cf
Revises:
Create Date: 2021-10-19 23:12:32.474155

'''

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision = '67c418ad84cf'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        'user_model',
        sa.Column(
            'created',
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text('CURRENT_TIMESTAMP'),
            nullable=False,
        ),
        sa.Column(
            'updated',
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text('CURRENT_TIMESTAMP'),
            nullable=False,
        ),
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('email', sa.String(), nullable=False),
        sa.Column('password', sa.String(), nullable=True),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_user_model')),
        sa.UniqueConstraint('email', name=op.f('uq_df9611602afc57819460c930e80d5eda')),
    )
    op.create_table(
        'user_friends_relation',
        sa.Column(
            'created',
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text('CURRENT_TIMESTAMP'),
            nullable=False,
        ),
        sa.Column(
            'updated',
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text('CURRENT_TIMESTAMP'),
            nullable=False,
        ),
        sa.Column('request_user_id', sa.Integer(), nullable=False),
        sa.Column('accept_user_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ['request_user_id'],
            ['user_model.id'],
            name=op.f('fk_ce78e86d62e35ac18a94456d4fb4046c'),
        ),
        sa.PrimaryKeyConstraint(
            'request_user_id', 'accept_user_id', name=op.f('pk_user_friends_relation')
        ),
    )
    op.create_index(
        op.f('ix_ce78e86d62e35ac18a94456d4fb4046c'),
        'user_friends_relation',
        ['request_user_id'],
        unique=False,
    )
    op.create_table(
        'user_oauth_relation',
        sa.Column(
            'created',
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text('CURRENT_TIMESTAMP'),
            nullable=False,
        ),
        sa.Column(
            'updated',
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text('CURRENT_TIMESTAMP'),
            nullable=False,
        ),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('uid', sa.String(), nullable=False),
        sa.Column('provider_type', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ['user_id'],
            ['user_model.id'],
            name=op.f('fk_46a4058838f15d869d2af3e12bf6afae'),
        ),
        sa.PrimaryKeyConstraint(
            'user_id', 'provider_type', name=op.f('pk_user_oauth_relation')
        ),
        sa.UniqueConstraint(
            'uid', 'provider_type', name=op.f('uq_0df791716f6e56aca5c843b20d2716c5')
        ),
    )
    op.create_index(
        op.f('ix_46a4058838f15d869d2af3e12bf6afae'),
        'user_oauth_relation',
        ['user_id'],
        unique=False,
    )
    op.create_table(
        'user_profile_model',
        sa.Column(
            'created',
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text('CURRENT_TIMESTAMP'),
            nullable=False,
        ),
        sa.Column(
            'updated',
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text('CURRENT_TIMESTAMP'),
            nullable=False,
        ),
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=False),
        sa.Column('nickname', sa.String(), nullable=False),
        sa.ForeignKeyConstraint(
            ['user_id'],
            ['user_model.id'],
            name=op.f('fk_1358fba8b5475ca6ba5279a270266315'),
        ),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_user_profile_model')),
    )
    op.create_index(
        op.f('ix_1358fba8b5475ca6ba5279a270266315'),
        'user_profile_model',
        ['user_id'],
        unique=False,
    )
    op.create_table(
        'user_profile_image_log_model',
        sa.Column(
            'created',
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text('CURRENT_TIMESTAMP'),
            nullable=False,
        ),
        sa.Column(
            'updated',
            sa.TIMESTAMP(timezone=True),
            server_default=sa.text('CURRENT_TIMESTAMP'),
            nullable=False,
        ),
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('profile_image_url', sa.String(), nullable=False),
        sa.Column('user_profile_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(
            ['user_profile_id'],
            ['user_profile_model.id'],
            name=op.f('fk_00dc9d024b75588197c956342cfc473c'),
        ),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_user_profile_image_log_model')),
    )
    op.create_index(
        op.f('ix_00dc9d024b75588197c956342cfc473c'),
        'user_profile_image_log_model',
        ['user_profile_id'],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index(
        op.f('ix_00dc9d024b75588197c956342cfc473c'),
        table_name='user_profile_image_log_model',
    )
    op.drop_table('user_profile_image_log_model')
    op.drop_index(
        op.f('ix_1358fba8b5475ca6ba5279a270266315'), table_name='user_profile_model'
    )
    op.drop_table('user_profile_model')
    op.drop_index(
        op.f('ix_46a4058838f15d869d2af3e12bf6afae'), table_name='user_oauth_relation'
    )
    op.drop_table('user_oauth_relation')
    op.drop_index(
        op.f('ix_ce78e86d62e35ac18a94456d4fb4046c'), table_name='user_friends_relation'
    )
    op.drop_table('user_friends_relation')
    op.drop_table('user_model')
