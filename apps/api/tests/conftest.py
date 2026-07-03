import os

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import Session, sessionmaker

from app.main import create_app
from app.shared.config import Settings
from app.shared.database import Base, get_db

import app.auth.models as _  # noqa: F401
import app.skills.models as _  # noqa: F401
import app.conversations.models as _  # noqa: F401
import app.models.models as _  # noqa: F401
import app.agents.models as _  # noqa: F401
import app.quota as _  # noqa: F401

_TEST_DB_PATH = "/tmp/ehr_agents_test.db"


def _get_test_settings() -> Settings:
    return Settings(
        mysql_host="localhost",
        mysql_port=3306,
        mysql_database="ehr_agents_test",
        mysql_user="test",
        mysql_password="test",
        jwt_secret="test-secret",
        cors_origins="http://localhost:5173",
        deepseek_api_key="",
        openai_api_key="",
        minimax_api_key="",
    )


@pytest.fixture
def test_settings() -> Settings:
    return _get_test_settings()


@pytest.fixture
def db_session():
    db_path = _TEST_DB_PATH
    if os.path.exists(db_path):
        os.remove(db_path)

    engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
    event.listen(engine, "connect", lambda conn, _: conn.execute("PRAGMA foreign_keys=ON"))
    Base.metadata.create_all(bind=engine)

    TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    db: Session = TestingSessionLocal()
    try:
        yield db
    finally:
        db.close()
        Base.metadata.drop_all(bind=engine)
        if os.path.exists(db_path):
            os.remove(db_path)


@pytest.fixture
def client(db_session):
    import app.shared.config as config_mod
    import app.shared.database as db_mod

    settings = _get_test_settings()
    config_mod._settings = settings
    app = create_app(settings=settings)

    def _override_get_settings():
        return settings

    def _override_get_db():
        yield db_session

    app.dependency_overrides[get_db] = _override_get_db
    from app.shared.config import get_settings

    app.dependency_overrides[get_settings] = _override_get_settings

    with TestClient(app) as c:
        sqlite_engine = db_session.get_bind()
        with sqlite_engine.connect() as conn:
            conn.execute(text("PRAGMA journal_mode=WAL"))
            conn.execute(text("PRAGMA foreign_keys=ON"))
            conn.commit()
        db_mod._engine = sqlite_engine
        db_mod._SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=sqlite_engine)
        yield c
    config_mod._settings = None
    db_mod._engine = None
    db_mod._SessionLocal = None


@pytest.fixture
def hrbp_token(db_session, client):
    from app.shared.seed import seed_local_users

    seed_local_users(db_session)
    response = client.post("/api/auth/login", json={"email": "hrbp@example.com", "password": "password123"})
    assert response.status_code == 200
    return response.json()["access_token"]


@pytest.fixture
def admin_token(db_session, client):
    from app.shared.seed import seed_local_users

    seed_local_users(db_session)
    response = client.post("/api/auth/login", json={"email": "admin@example.com", "password": "password123"})
    assert response.status_code == 200
    return response.json()["access_token"]


@pytest.fixture
def auth_headers(hrbp_token):
    return {"Authorization": f"Bearer {hrbp_token}"}


@pytest.fixture
def fake_chat_adapter():
    import json as _json

    # 工具调用返回结构化 JSON；总结调用返回文本
    _TOOL_OUTPUTS = {
        "generate_jd": {
            "job_title": "Senior Developer",
            "responsibilities": ["Design systems", "Code review"],
            "requirements": ["5+ years experience", "Strong CS fundamentals"],
            "interview_focus": ["System design", "Problem solving"],
            "selling_points": ["Remote work", "Competitive salary"],
        },
        "screen_resume": {
            "screening_dimensions": [
                {"dimension": "Technical Skills", "score": "Strong", "notes": "Good match"},
                {"dimension": "Experience", "score": "Adequate", "notes": "Sufficient years"},
            ],
            "strengths": ["Relevant experience", "Strong portfolio"],
            "risks": ["Limited leadership experience"],
            "recommended_next_step": "Proceed to technical interview",
        },
        "generate_interview_questions": {
            "question_groups": [
                {"competency": "Technical", "questions": ["Describe a complex project", "How do you debug?"]},
                {"competency": "Behavioral", "questions": ["Tell me about a conflict", "Why this role?"]},
            ],
        },
        "summarize_interview_feedback": {
            "feedback_summary": "Strong candidate overall",
            "evidence": ["Good technical answers", "Clear communication"],
            "concerns": ["Limited management experience"],
            "decision_recommendation": "Hire - recommend advancing to final round",
        },
        "generate_html": {
            "title": "Test Landing",
            "description": "A test landing page",
            "theme": "light",
            "primary_color": "#2563eb",
            "sections": [
                {"type": "hero", "heading": "Welcome", "body": "Hello world", "items": []},
                {"type": "features", "heading": "Why us", "body": "Because", "items": ["fast", "safe"]},
            ],
        },
    }

    class FakeTokenUsage:
        prompt_tokens = 100
        completion_tokens = 50
        total_tokens = 150
        model_name = "fake-model"

    class FakeChatAdapter:
        def __init__(self):
            self.last_usage = FakeTokenUsage()
            self._plan_call_count = 0

        def invoke(self, messages, **kwargs):
            full_text = " ".join(m.get("content", "") for m in messages)

            # Agent Loop planning prompt（含"决定你的下一步 action"）
            if "决定你的下一步 action" in full_text or "action.*call_tool" in full_text:
                self._plan_call_count += 1

                # 检查点恢复后 或 已有工具调用结果：直接回复
                if "用户在检查点选择了" in full_text or "[已调用]" in full_text:
                    return _json.dumps({"action": "respond", "content": "根据工具执行结果，已完成处理。"})

                # 第一次规划：调用 skill 绑定的主工具
                if self._plan_call_count == 1:
                    # 优先匹配 "主工具：xxx" 标记
                    import re as _re
                    primary_match = _re.search(r"主工具：(\w+)", full_text)
                    if primary_match:
                        tool_name = primary_match.group(1)
                        return _json.dumps({"action": "call_tool", "tool_name": tool_name, "tool_input": "test input"})
                    # fallback: 逐个检测
                    for tool_name in ("generate_jd", "screen_resume", "generate_interview_questions", "summarize_interview_feedback", "generate_html"):
                        if tool_name in full_text:
                            return _json.dumps({"action": "call_tool", "tool_name": tool_name, "tool_input": "test input"})
                    return _json.dumps({"action": "call_tool", "tool_name": "generate_jd", "tool_input": "test"})
                # 后续规划：直接回复
                return _json.dumps({"action": "respond", "content": "Based on the tool results, here is my summary."})

            # LLM 工具执行 prompt（含 "Output ONLY valid JSON" 或 "structured data generator"）
            if "Output ONLY valid JSON" in full_text or "structured data generator" in full_text:
                for tool_name in ("screen_resume", "generate_interview_questions", "summarize_interview_feedback", "generate_jd", "generate_html"):
                    if f'"{tool_name}"' in full_text or f"Screen and evaluate" in full_text and tool_name == "screen_resume":
                        return _json.dumps(_TOOL_OUTPUTS[tool_name])
                    if tool_name == "screen_resume" and "screening_dimensions" in full_text:
                        return _json.dumps(_TOOL_OUTPUTS["screen_resume"])
                    if tool_name == "generate_interview_questions" and "question_groups" in full_text:
                        return _json.dumps(_TOOL_OUTPUTS["generate_interview_questions"])
                    if tool_name == "summarize_interview_feedback" and "feedback_summary" in full_text:
                        return _json.dumps(_TOOL_OUTPUTS["summarize_interview_feedback"])
                    if tool_name == "generate_html" and "page specification" in full_text:
                        return _json.dumps(_TOOL_OUTPUTS["generate_html"])
                return _json.dumps(_TOOL_OUTPUTS["generate_jd"])

            # 强制总结 / 其他
            return "This is a summary of the tool output for the HRBP user."

    return FakeChatAdapter()

@pytest.fixture(autouse=True)
def _inject_fake_chat_adapter(monkeypatch, fake_chat_adapter):
    def _fake_resolve(provider_id, settings):
        return fake_chat_adapter

    monkeypatch.setattr("app.agents.router.resolve_chat_adapter", _fake_resolve)
    monkeypatch.setattr("app.agents.service.resolve_chat_adapter", _fake_resolve)
