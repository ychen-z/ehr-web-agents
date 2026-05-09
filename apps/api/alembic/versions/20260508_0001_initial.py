"""initial

Revision ID: 0001
Revises:
Create Date: 2026-05-08

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "users",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("email", sa.String(255), unique=True, nullable=False),
        sa.Column("hashed_password", sa.String(255), nullable=False),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("display_name", sa.String(100), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        mysql_engine="InnoDB",
        mysql_charset="utf8mb4",
    )
    op.create_index("ix_users_email", "users", ["email"])

    op.create_table(
        "skills",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("skill_id", sa.String(100), unique=True, nullable=False),
        sa.Column("name", sa.String(200), nullable=False),
        sa.Column("description", sa.String(1000)),
        sa.Column("category", sa.String(100)),
        sa.Column("prompt_template", sa.String(5000)),
        sa.Column("mock_tool_name", sa.String(100)),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        mysql_engine="InnoDB",
        mysql_charset="utf8mb4",
    )
    op.create_index("ix_skills_skill_id", "skills", ["skill_id"])

    op.create_table(
        "model_configs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("provider_id", sa.String(50), unique=True, nullable=False),
        sa.Column("display_name", sa.String(200), nullable=False),
        sa.Column("default_model_name", sa.String(200), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False, server_default=sa.text("1")),
        sa.Column("metadata", sa.JSON()),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        mysql_engine="InnoDB",
        mysql_charset="utf8mb4",
    )
    op.create_index("ix_model_configs_provider_id", "model_configs", ["provider_id"])

    op.create_table(
        "conversations",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("user_id", sa.String(36), nullable=False),
        sa.Column("title", sa.String(500)),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        mysql_engine="InnoDB",
        mysql_charset="utf8mb4",
    )
    op.create_index("ix_conversations_user_id", "conversations", ["user_id"])
    op.create_foreign_key("fk_conversations_user_id", "conversations", "users", ["user_id"], ["id"])

    op.create_table(
        "messages",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("conversation_id", sa.String(36), nullable=False),
        sa.Column("role", sa.String(20), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        mysql_engine="InnoDB",
        mysql_charset="utf8mb4",
    )
    op.create_index("ix_messages_conversation_id", "messages", ["conversation_id"])
    op.create_foreign_key("fk_messages_conversation_id", "messages", "conversations", ["conversation_id"], ["id"])

    op.create_table(
        "user_skills",
        sa.Column("user_id", sa.String(36), primary_key=True),
        sa.Column("skill_id", sa.String(36), primary_key=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        mysql_engine="InnoDB",
        mysql_charset="utf8mb4",
    )
    op.create_foreign_key("fk_user_skills_user_id", "user_skills", "users", ["user_id"], ["id"])
    op.create_foreign_key("fk_user_skills_skill_id", "user_skills", "skills", ["skill_id"], ["id"])

    op.create_table(
        "agent_runs",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("conversation_id", sa.String(36), nullable=True),
        sa.Column("user_id", sa.String(36), nullable=False),
        sa.Column("skill_id", sa.String(36), nullable=False),
        sa.Column("model_provider_id", sa.String(50)),
        sa.Column("status", sa.String(30), nullable=False, server_default="pending"),
        sa.Column("input_message_id", sa.String(36)),
        sa.Column("structured_output", sa.JSON()),
        sa.Column("error_message", sa.Text()),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        mysql_engine="InnoDB",
        mysql_charset="utf8mb4",
    )
    op.create_index("ix_agent_runs_conversation_id", "agent_runs", ["conversation_id"])
    op.create_index("ix_agent_runs_user_id", "agent_runs", ["user_id"])
    op.create_index("ix_agent_runs_status", "agent_runs", ["status"])
    op.create_foreign_key("fk_agent_runs_conversation_id", "agent_runs", "conversations", ["conversation_id"], ["id"])
    op.create_foreign_key("fk_agent_runs_user_id", "agent_runs", "users", ["user_id"], ["id"])
    op.create_foreign_key("fk_agent_runs_skill_id", "agent_runs", "skills", ["skill_id"], ["id"])
    op.create_foreign_key("fk_agent_runs_model_provider_id", "agent_runs", "model_configs", ["model_provider_id"], ["provider_id"])

    op.create_table(
        "tool_invocations",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("agent_run_id", sa.String(36), nullable=False),
        sa.Column("tool_name", sa.String(200), nullable=False),
        sa.Column("input_params", sa.JSON()),
        sa.Column("output", sa.JSON()),
        sa.Column("status", sa.String(30), nullable=False, server_default="pending"),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("finished_at", sa.DateTime()),
        mysql_engine="InnoDB",
        mysql_charset="utf8mb4",
    )
    op.create_index("ix_tool_invocations_agent_run_id", "tool_invocations", ["agent_run_id"])
    op.create_foreign_key("fk_tool_invocations_agent_run_id", "tool_invocations", "agent_runs", ["agent_run_id"], ["id"])


def downgrade() -> None:
    op.drop_table("tool_invocations")
    op.drop_table("agent_runs")
    op.drop_table("user_skills")
    op.drop_table("messages")
    op.drop_table("conversations")
    op.drop_table("model_configs")
    op.drop_table("skills")
    op.drop_table("users")
