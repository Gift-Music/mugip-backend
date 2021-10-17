'''initial migration

Revision ID: 90c24b4176ac
Revises:
Create Date: 2021-10-17 23:36:21.954492

'''

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision = '90c24b4176ac'
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
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
        sa.Column('requester_id', sa.Integer(), nullable=False),
        sa.Column('acceptor_id', sa.Integer(), nullable=False),
        sa.PrimaryKeyConstraint(
            'requester_id', 'acceptor_id', name=op.f('pk_user_friends_relation')
        ),
    )
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
        sa.Column('password', sa.String(), nullable=False),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_user_model')),
        sa.UniqueConstraint('email', name=op.f('uq_df9611602afc57819460c930e80d5eda')),
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
        sa.PrimaryKeyConstraint(
            'user_id', 'provider_type', name=op.f('pk_user_oauth_relation')
        ),
        sa.UniqueConstraint(
            'uid', 'provider_type', name=op.f('uq_0df791716f6e56aca5c843b20d2716c5')
        ),
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
        sa.PrimaryKeyConstraint('id', name=op.f('pk_user_profile_image_log_model')),
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
        sa.PrimaryKeyConstraint('id', name=op.f('pk_user_profile_model')),
    )


def downgrade() -> None:
    op.drop_table('user_profile_model')
    op.drop_table('user_profile_image_log_model')
    op.drop_table('user_oauth_relation')
    op.drop_table('user_model')
    op.drop_table('user_friends_relation')
