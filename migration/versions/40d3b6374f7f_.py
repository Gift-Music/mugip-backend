"""empty message

Revision ID: 40d3b6374f7f
Revises: 07d73b46059e
Create Date: 2022-08-21 19:15:55.455873

"""

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision = "40d3b6374f7f"
down_revision = "07d73b46059e"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("user", sa.Column("username", sa.String(), nullable=True))
    op.alter_column("user", "username", existing_type=sa.String(), nullable=False)
    op.add_column("user", sa.Column("gender", sa.String(), nullable=True))
    op.add_column("user", sa.Column("birthday", sa.Date(), nullable=True))
    op.add_column("user", sa.Column("phone", sa.String(), nullable=True))
    op.alter_column("user", "nickname", existing_type=sa.VARCHAR(), nullable=False)
    op.create_unique_constraint(
        op.f("uq_89297565adc75f8db936ec64fd2cf791"), "user", ["username"]
    )
    op.alter_column(
        "user_oauth_login",
        "provider_type",
        existing_type=sa.INTEGER(),
        type_=sa.String(),
        existing_nullable=False,
    )


def downgrade() -> None:
    op.alter_column(
        "user_oauth_login",
        "provider_type",
        existing_type=sa.String(),
        type_=sa.INTEGER(),
        existing_nullable=False,
    )
    op.drop_constraint(
        op.f("uq_89297565adc75f8db936ec64fd2cf791"), "user", type_="unique"
    )
    op.alter_column("user", "nickname", existing_type=sa.VARCHAR(), nullable=True)
    op.drop_column("user", "phone")
    op.drop_column("user", "birthday")
    op.drop_column("user", "gender")
    op.drop_column("user", "username")
