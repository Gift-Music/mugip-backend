"""change spotify_id to id

Revision ID: dc9649a1a451
Revises: c97014438f91
Create Date: 2022-05-18 21:46:07.769206

"""

from alembic import op


# revision identifiers, used by Alembic.
revision = "dc9649a1a451"
down_revision = "c97014438f91"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.alter_column("track", "spotify_id", new_column_name="id")
    op.alter_column("artist", "spotify_id", new_column_name="id")
    op.alter_column("album", "spotify_id", new_column_name="id")


def downgrade() -> None:
    raise NotImplementedError()
