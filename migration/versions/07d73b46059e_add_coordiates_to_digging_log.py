"""add coordiates to digging log

Revision ID: 07d73b46059e
Revises: 7ef56eef8c53
Create Date: 2022-07-03 15:21:10.637825

"""

import sqlalchemy as sa
from alembic import op
import geoalchemy2


revision = "07d73b46059e"
down_revision = "7ef56eef8c53"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column(
        "digging_log",
        sa.Column(
            "coordinates",
            geoalchemy2.types.Geography(
                geometry_type="POINT",
                srid=4326,
                from_text="ST_GeogFromText",
                name="geography",
            ),
            nullable=True,
        ),
    )


def downgrade() -> None:
    op.drop_index(
        "idx_digging_log_coordinates",
        table_name="digging_log",
        postgresql_using="gist",
        postgresql_ops={},
    )
    op.drop_column("digging_log", "coordinates")
