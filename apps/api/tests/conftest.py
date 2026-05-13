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

    # Tool call returns structured JSON; summary call returns text
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
    }

    class FakeChatAdapter:
        def invoke(self, messages, **kwargs):
            full_text = " ".join(m.get("content", "") for m in messages)
            # If system prompt asks for structured JSON output, return tool JSON
            if "Output ONLY valid JSON" in full_text or "structured data generator" in full_text:
                # Match tool name precisely: check for the tool description marker
                for tool_name in ("screen_resume", "generate_interview_questions", "summarize_interview_feedback", "generate_jd"):
                    # _build_tool_prompt puts "Your task: <description>" where description comes from TOOL_SCHEMAS
                    if f'"{tool_name}"' in full_text or f"Screen and evaluate" in full_text and tool_name == "screen_resume":
                        return _json.dumps(_TOOL_OUTPUTS[tool_name])
                    # Also check via output field names unique to each tool
                    if tool_name == "screen_resume" and "screening_dimensions" in full_text:
                        return _json.dumps(_TOOL_OUTPUTS["screen_resume"])
                    if tool_name == "generate_interview_questions" and "question_groups" in full_text:
                        return _json.dumps(_TOOL_OUTPUTS["generate_interview_questions"])
                    if tool_name == "summarize_interview_feedback" and "feedback_summary" in full_text:
                        return _json.dumps(_TOOL_OUTPUTS["summarize_interview_feedback"])
                return _json.dumps(_TOOL_OUTPUTS["generate_jd"])
            else:
                return "This is a summary of the tool output for the HRBP user."

    return FakeChatAdapter()

@pytest.fixture(autouse=True)
def _inject_fake_chat_adapter(monkeypatch, fake_chat_adapter):
    def _fake_resolve(provider_id, settings):
        return fake_chat_adapter

    monkeypatch.setattr("app.agents.router.resolve_chat_adapter", _fake_resolve)
    monkeypatch.setattr("app.agents.service.resolve_chat_adapter", _fake_resolve)
