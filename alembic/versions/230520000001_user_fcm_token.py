"""user fcm token

Revision ID: 230520000001
Revises: 230518000002
Create Date: 2026-05-20 00:00:01.000000

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "230520000001"
down_revision: Union[str, Sequence[str], None] = "230518000002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("users", sa.Column("fcm_token", sa.String(length=512), nullable=True))
    op.add_column("users", sa.Column("fcm_platform", sa.String(length=32), nullable=True))
    op.create_index("ix_users_fcm_token", "users", ["fcm_token"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_users_fcm_token", table_name="users")
    op.drop_column("users", "fcm_platform")
    op.drop_column("users", "fcm_token")

