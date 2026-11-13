"""estado de vagas e candidaturas

Revision ID: 20261113_0004
Revises: 20260507_0003
Create Date: 2026-11-13

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "20261113_0004"
down_revision: Union[str, None] = "20260507_0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())
    if "jobs" in tables and "estado" not in {c["name"] for c in inspector.get_columns("jobs")}:
        op.add_column(
            "jobs",
            sa.Column("estado", sa.String(20), nullable=False, server_default="aberta"),
        )
    if "job_applications" in tables and "estado" not in {
        c["name"] for c in inspector.get_columns("job_applications")
    }:
        op.add_column(
            "job_applications",
            sa.Column("estado", sa.String(20), nullable=False, server_default="pendente"),
        )


def downgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())
    if "job_applications" in tables and "estado" in {
        c["name"] for c in inspector.get_columns("job_applications")
    }:
        op.drop_column("job_applications", "estado")
    if "jobs" in tables and "estado" in {c["name"] for c in inspector.get_columns("jobs")}:
        op.drop_column("jobs", "estado")
