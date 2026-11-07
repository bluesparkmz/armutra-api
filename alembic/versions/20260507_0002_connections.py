"""connections (seguir utilizadores)

Revision ID: 20260507_0002
Revises: 20260418_0001
Create Date: 2026-05-07

"""

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "20260507_0002"
down_revision: Union[str, None] = "20260418_0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # A migração inicial usa create_all; numa BD nova a tabela já pode existir.
    if "connections" in sa.inspect(op.get_bind()).get_table_names():
        return
    op.create_table(
        "connections",
        sa.Column("id", postgresql.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "follower_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "following_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "criado_em",
            sa.DateTime(timezone=True),
            server_default=sa.func.now(),
            nullable=False,
        ),
        sa.UniqueConstraint("follower_id", "following_id", name="uq_connection_follower_following"),
        sa.CheckConstraint("follower_id <> following_id", name="ck_connection_not_self"),
    )
    op.create_index("ix_connections_follower_id", "connections", ["follower_id"])
    op.create_index("ix_connections_following_id", "connections", ["following_id"])


def downgrade() -> None:
    op.drop_index("ix_connections_following_id", table_name="connections")
    op.drop_index("ix_connections_follower_id", table_name="connections")
    op.drop_table("connections")
