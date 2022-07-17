"""image

Revision ID: 7ef56eef8c53
Revises: dc9649a1a451
Create Date: 2022-05-19 20:58:08.075907

"""

import sqlalchemy as sa
from alembic import op


# revision identifiers, used by Alembic.
revision = "7ef56eef8c53"
down_revision = "dc9649a1a451"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "image", sa.Column("id", sa.Integer(), nullable=False, primary_key=True)
    )
    op.drop_constraint("pk_image", "image")
    op.create_primary_key("pk_image", "image", ["id"])


def downgrade() -> None:
    op.drop_column("image", "id")
