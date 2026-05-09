from app.auth.models import User
from app.skills.models import Skill, UserSkill
from app.conversations.models import Conversation, Message
from app.models.models import ModelConfig
from app.agents.models import AgentRun, ToolInvocation


def test_all_models_define_tables():
    assert User.__tablename__ == "users"
    assert Skill.__tablename__ == "skills"
    assert UserSkill.__tablename__ == "user_skills"
    assert Conversation.__tablename__ == "conversations"
    assert Message.__tablename__ == "messages"
    assert ModelConfig.__tablename__ == "model_configs"
    assert AgentRun.__tablename__ == "agent_runs"
    assert ToolInvocation.__tablename__ == "tool_invocations"
