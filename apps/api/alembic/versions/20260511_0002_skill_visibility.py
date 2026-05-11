"""add skill ownership and visibility

Revision ID: 0002
Revises: 0001
Create Date: 2026-05-11

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("skills", sa.Column("owner_user_id", sa.String(36), nullable=True))
    op.add_column("skills", sa.Column("visibility", sa.String(20), nullable=False, server_default="shared"))
    op.add_column("skills", sa.Column("source", sa.String(20), nullable=False, server_default="system"))
    op.create_index("ix_skills_owner_user_id", "skills", ["owner_user_id"])
    op.create_index("ix_skills_visibility", "skills", ["visibility"])
    op.create_index("ix_skills_source", "skills", ["source"])
    op.create_foreign_key("fk_skills_owner_user_id_users", "skills", "users", ["owner_user_id"], ["id"])


def downgrade() -> None:
    op.drop_constraint("fk_skills_owner_user_id_users", "skills", type_="foreignkey")
    op.drop_index("ix_skills_source", table_name="skills")
    op.drop_index("ix_skills_visibility", table_name="skills")
    op.drop_index("ix_skills_owner_user_id", table_name="skills")
    op.drop_column("skills", "source")
    op.drop_column("skills", "visibility")
    op.drop_column("skills", "owner_user_id")
