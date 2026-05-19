"""chat tables

Revision ID: 230518000001
Revises: 23010155f2dd
Create Date: 2026-05-18 00:00:01.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = "230518000001"
down_revision: Union[str, Sequence[str], None] = "23010155f2dd"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "chat_rooms",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("room_id", sa.UUID(), nullable=True),
        sa.Column("tenant_id", sa.UUID(), nullable=False),
        sa.Column("landlord_id", sa.UUID(), nullable=False),
        sa.Column("last_message_id", sa.UUID(), nullable=True),
        sa.Column("last_message", sa.Text(), nullable=True),
        sa.Column("last_message_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["landlord_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["room_id"], ["rooms.id"]),
        sa.ForeignKeyConstraint(["tenant_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("tenant_id", "landlord_id", "room_id", name="uq_chat_rooms_tenant_landlord_room"),
    )
    op.create_index("ix_chat_rooms_last_message_at", "chat_rooms", ["last_message_at"], unique=False)
    op.create_index(
        "uq_chat_rooms_tenant_landlord_null_room",
        "chat_rooms",
        ["tenant_id", "landlord_id"],
        unique=True,
        postgresql_where=sa.text("room_id IS NULL"),
    )

    op.create_table(
        "chat_participants",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("chat_room_id", sa.UUID(), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("last_read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("joined_at", sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(["chat_room_id"], ["chat_rooms.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("chat_room_id", "user_id", name="uq_chat_participants_room_user"),
    )
    op.create_index("ix_chat_participants_chat_room_id", "chat_participants", ["chat_room_id"], unique=False)
    op.create_index("ix_chat_participants_user_id", "chat_participants", ["user_id"], unique=False)

    op.create_table(
        "chat_messages",
        sa.Column("id", sa.UUID(), nullable=False),
        sa.Column("chat_room_id", sa.UUID(), nullable=False),
        sa.Column("sender_id", sa.UUID(), nullable=False),
        sa.Column("message_type", sa.String(length=20), nullable=False),
        sa.Column("message", sa.Text(), nullable=True),
        sa.Column("image_url", sa.String(length=2048), nullable=True),
        sa.Column("metadata", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("is_read", sa.Boolean(), nullable=True),
        sa.Column("read_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint("message_type IN ('TEXT', 'IMAGE', 'SYSTEM')", name="ck_chat_messages_message_type"),
        sa.ForeignKeyConstraint(["chat_room_id"], ["chat_rooms.id"]),
        sa.ForeignKeyConstraint(["sender_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_chat_messages_room_created_at", "chat_messages", ["chat_room_id", "created_at"], unique=False)

    op.create_foreign_key(
        "fk_chat_rooms_last_message_id",
        "chat_rooms",
        "chat_messages",
        ["last_message_id"],
        ["id"],
    )


def downgrade() -> None:
    op.drop_constraint("fk_chat_rooms_last_message_id", "chat_rooms", type_="foreignkey")
    op.drop_index("ix_chat_messages_room_created_at", table_name="chat_messages")
    op.drop_table("chat_messages")

    op.drop_index("ix_chat_participants_user_id", table_name="chat_participants")
    op.drop_index("ix_chat_participants_chat_room_id", table_name="chat_participants")
    op.drop_table("chat_participants")

    op.drop_index("uq_chat_rooms_tenant_landlord_null_room", table_name="chat_rooms")
    op.drop_index("ix_chat_rooms_last_message_at", table_name="chat_rooms")
    op.drop_table("chat_rooms")
