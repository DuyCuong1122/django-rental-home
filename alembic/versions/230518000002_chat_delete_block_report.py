"""chat delete block report

Revision ID: 230518000002
Revises: 230518000001
Create Date: 2026-05-18 00:00:02.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "230518000002"
down_revision: Union[str, Sequence[str], None] = "230518000001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "chat_room_deletions",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("chat_room_id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["chat_room_id"], ["chat_rooms.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("chat_room_id", "user_id", name="uq_chat_room_deletions_room_user"),
    )
    op.create_index("ix_chat_room_deletions_user_id", "chat_room_deletions", ["user_id"], unique=False)
    op.create_index("ix_chat_room_deletions_chat_room_id", "chat_room_deletions", ["chat_room_id"], unique=False)

    op.create_table(
        "chat_room_blocks",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("chat_room_id", sa.UUID(), nullable=False),
        sa.Column("blocker_id", sa.UUID(), nullable=False),
        sa.Column("blocked_id", sa.UUID(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["chat_room_id"], ["chat_rooms.id"]),
        sa.ForeignKeyConstraint(["blocker_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["blocked_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("chat_room_id", "blocker_id", "blocked_id", name="uq_chat_room_blocks_room_blocker_blocked"),
    )
    op.create_index("ix_chat_room_blocks_chat_room_id", "chat_room_blocks", ["chat_room_id"], unique=False)
    op.create_index("ix_chat_room_blocks_blocker_id", "chat_room_blocks", ["blocker_id"], unique=False)
    op.create_index("ix_chat_room_blocks_blocked_id", "chat_room_blocks", ["blocked_id"], unique=False)

    op.create_table(
        "chat_reports",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("chat_room_id", sa.UUID(), nullable=False),
        sa.Column("reporter_id", sa.UUID(), nullable=False),
        sa.Column("reason", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["chat_room_id"], ["chat_rooms.id"]),
        sa.ForeignKeyConstraint(["reporter_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_chat_reports_chat_room_id", "chat_reports", ["chat_room_id"], unique=False)
    op.create_index("ix_chat_reports_reporter_id", "chat_reports", ["reporter_id"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_chat_reports_reporter_id", table_name="chat_reports")
    op.drop_index("ix_chat_reports_chat_room_id", table_name="chat_reports")
    op.drop_table("chat_reports")

    op.drop_index("ix_chat_room_blocks_blocked_id", table_name="chat_room_blocks")
    op.drop_index("ix_chat_room_blocks_blocker_id", table_name="chat_room_blocks")
    op.drop_index("ix_chat_room_blocks_chat_room_id", table_name="chat_room_blocks")
    op.drop_table("chat_room_blocks")

    op.drop_index("ix_chat_room_deletions_chat_room_id", table_name="chat_room_deletions")
    op.drop_index("ix_chat_room_deletions_user_id", table_name="chat_room_deletions")
    op.drop_table("chat_room_deletions")

