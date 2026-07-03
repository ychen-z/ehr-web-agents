"""添加 HITL 检查点字段

Revision ID: 0004
Revises: 0003
Create Date: 2026-07-03

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("agent_runs", sa.Column("checkpoint_state", sa.JSON, nullable=True))
    op.add_column("skills", sa.Column("checkpoints", sa.Text, nullable=True))


def downgrade() -> None:
    op.drop_column("agent_runs", "checkpoint_state")
    op.drop_column("skills", "checkpoints")
