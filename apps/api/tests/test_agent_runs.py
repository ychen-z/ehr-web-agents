import time

from app.agents.service import resolve_chat_adapter
from app.auth.models import User
from app.shared.config import Settings
from app.shared.errors import AppError
from app.skills.models import Skill, UserSkill
from app.skills.service import seed_builtin_skills
from app.models.service import seed_model_configs
from app.shared.seed import seed_local_users


def _install_skill(db_session, user_email: str, skill_id_str: str) -> tuple[str, str]:
    seed_local_users(db_session)
    seed_builtin_skills(db_session)
    seed_model_configs(db_session)
    user = db_session.query(User).filter(User.email == user_email).first()
    skill = db_session.query(Skill).filter(Skill.skill_id == skill_id_str).first()
    existing = db_session.query(UserSkill).filter(
        UserSkill.user_id == user.id, UserSkill.skill_id == skill.id
    ).first()
    if not existing:
        us = UserSkill(user_id=user.id, skill_id=skill.id)
        db_session.add(us)
        db_session.commit()
    return user.id, skill.skill_id


def _wait_for_completion(client, run_data, token):
    while run_data["status"] in ("running", "pending"):
        time.sleep(0.1)
        check = client.get(
            f"/api/agent/runs/{run_data['id']}",
            headers={"Authorization": f"Bearer {token}"},
        )
        run_data = check.json()
    return run_data


def test_create_run_rejects_uninstalled_skill(client, db_session, hrbp_token):
    seed_local_users(db_session)
    seed_builtin_skills(db_session)
    seed_model_configs(db_session)
    resp = client.post(
        "/api/agent/runs",
        json={
            "skill_id": "generate_jd",
            "user_message": "We need a senior Python developer",
            "conversation_id": None,
            "model_provider_id": "deepseek",
        },
        headers={"Authorization": f"Bearer {hrbp_token}"},
    )
    assert resp.status_code == 400
    data = resp.json()
    assert "installed" in str(data).lower() or "INSTALLED" in data.get("code", "")


def test_create_run_requires_auth(client, db_session):
    resp = client.post(
        "/api/agent/runs",
        json={"skill_id": "generate_jd", "user_message": "test", "conversation_id": None},
    )
    assert resp.status_code == 401


def test_create_run_succeeds_for_installed_skill(client, db_session, hrbp_token):
    seed_local_users(db_session)
    seed_builtin_skills(db_session)
    _install_skill(db_session, "hrbp@example.com", "generate_jd")

    resp = client.post(
        "/api/agent/runs",
        json={
            "skill_id": "generate_jd",
            "user_message": "We need a senior Python developer with AWS experience",
            "conversation_id": None,
            "model_provider_id": "deepseek",
        },
        headers={"Authorization": f"Bearer {hrbp_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "id" in data
    assert data["status"] in ("completed", "running", "pending")

    data = _wait_for_completion(client, data, hrbp_token)
    assert data["status"] == "completed"
    assert data["structured_output"] is not None
    assert "job_title" in data["structured_output"]


def test_create_run_rejects_nonexistent_skill(client, db_session, hrbp_token):
    seed_local_users(db_session)
    seed_builtin_skills(db_session)
    resp = client.post(
        "/api/agent/runs",
        json={
            "skill_id": "nonexistent_skill",
            "user_message": "test",
            "conversation_id": None,
        },
        headers={"Authorization": f"Bearer {hrbp_token}"},
    )
    assert resp.status_code == 400


def test_run_stores_user_and_assistant_messages(client, db_session, hrbp_token):
    seed_local_users(db_session)
    seed_builtin_skills(db_session)
    _install_skill(db_session, "hrbp@example.com", "generate_jd")

    from app.conversations.service import create_conversation

    conv = create_conversation(db_session, db_session.query(User).filter(User.email == "hrbp@example.com").first().id)

    resp = client.post(
        "/api/agent/runs",
        json={
            "skill_id": "generate_jd",
            "user_message": "We need a senior Python developer",
            "conversation_id": conv.id,
            "model_provider_id": "deepseek",
        },
        headers={"Authorization": f"Bearer {hrbp_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()

    data = _wait_for_completion(client, data, hrbp_token)
    assert data["status"] == "completed"

    from app.conversations.models import Message

    messages = (
        db_session.query(Message)
        .filter(Message.conversation_id == conv.id)
        .order_by(Message.created_at.asc())
        .all()
    )
    roles = [m.role for m in messages]
    assert "user" in roles
    assert "assistant" in roles

    user_msg = next(m for m in messages if m.role == "user")
    assert "senior Python developer" in user_msg.content

    assistant_msg = next(m for m in messages if m.role == "assistant")
    assert len(assistant_msg.content) > 0


def test_run_streams_expected_events(client, db_session, hrbp_token):
    seed_local_users(db_session)
    seed_builtin_skills(db_session)
    _install_skill(db_session, "hrbp@example.com", "generate_jd")

    resp = client.post(
        "/api/agent/runs",
        json={
            "skill_id": "generate_jd",
            "user_message": "We need a senior Python developer",
            "conversation_id": None,
            "model_provider_id": "deepseek",
        },
        headers={"Authorization": f"Bearer {hrbp_token}"},
    )
    assert resp.status_code == 200
    run_data = resp.json()
    assert run_data["status"] in ("running", "pending")

    run_data = _wait_for_completion(client, run_data, hrbp_token)
    assert run_data["status"] == "completed"

    events_resp = client.get(
        f"/api/agent/runs/{run_data['id']}/events?token={hrbp_token}",
    )
    assert events_resp.status_code == 200

    body = events_resp.text
    assert "run_started" in body
    assert "skill_selected" in body
    assert "tool_started" in body
    assert "tool_completed" in body
    assert "structured_result" in body
    assert "model_delta" in body
    assert "run_completed" in body
    assert "stream_closed" in body


def test_sse_replay_works_for_multiple_clients(client, db_session, hrbp_token):
    seed_local_users(db_session)
    seed_builtin_skills(db_session)
    _install_skill(db_session, "hrbp@example.com", "generate_jd")

    resp = client.post(
        "/api/agent/runs",
        json={
            "skill_id": "generate_jd",
            "user_message": "Senior developer needed",
            "conversation_id": None,
            "model_provider_id": "deepseek",
        },
        headers={"Authorization": f"Bearer {hrbp_token}"},
    )
    assert resp.status_code == 200
    run_data = resp.json()
    run_data = _wait_for_completion(client, run_data, hrbp_token)
    assert run_data["status"] == "completed"

    events1 = client.get(f"/api/agent/runs/{run_data['id']}/events?token={hrbp_token}")
    assert events1.status_code == 200
    assert "run_started" in events1.text

    events2 = client.get(f"/api/agent/runs/{run_data['id']}/events?token={hrbp_token}")
    assert events2.status_code == 200
    assert "run_started" in events2.text


def test_post_returns_immediately_with_running_status(client, db_session, hrbp_token):
    seed_local_users(db_session)
    seed_builtin_skills(db_session)
    _install_skill(db_session, "hrbp@example.com", "generate_jd")

    resp = client.post(
        "/api/agent/runs",
        json={
            "skill_id": "generate_jd",
            "user_message": "Build a JD for a data engineer",
            "conversation_id": None,
            "model_provider_id": "deepseek",
        },
        headers={"Authorization": f"Bearer {hrbp_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert "id" in data
    assert "created_at" in data
    assert "updated_at" in data
    assert data["status"] in ("running", "pending")


def test_sse_auth_requires_token(client, db_session):
    resp = client.get("/api/agent/runs/some-run-id/events")
    assert resp.status_code == 401


def test_sse_rejects_invalid_token(client, db_session):
    resp = client.get("/api/agent/runs/some-run-id/events?token=invalid-token")
    assert resp.status_code == 401


def test_sse_rejects_cross_user_token(client, db_session, hrbp_token, admin_token):
    seed_local_users(db_session)
    seed_builtin_skills(db_session)
    _install_skill(db_session, "hrbp@example.com", "generate_jd")

    resp = client.post(
        "/api/agent/runs",
        json={
            "skill_id": "generate_jd",
            "user_message": "We need a senior Python developer",
            "conversation_id": None,
            "model_provider_id": "deepseek",
        },
        headers={"Authorization": f"Bearer {hrbp_token}"},
    )
    assert resp.status_code == 200
    run_data = resp.json()

    run_data = _wait_for_completion(client, run_data, hrbp_token)

    events_resp = client.get(
        f"/api/agent/runs/{run_data['id']}/events?token={admin_token}",
    )
    assert events_resp.status_code == 403


def test_create_run_with_conversation_and_model(client, db_session, hrbp_token):
    seed_local_users(db_session)
    seed_builtin_skills(db_session)
    _install_skill(db_session, "hrbp@example.com", "screen_resume")

    from app.conversations.service import create_conversation
    from app.skills.models import Skill

    user = db_session.query(User).filter(User.email == "hrbp@example.com").first()
    skill = db_session.query(Skill).filter(Skill.skill_id == "screen_resume").first()
    conv = create_conversation(db_session, user.id, "Test Resume Screening")

    resp = client.post(
        "/api/agent/runs",
        json={
            "skill_id": "screen_resume",
            "user_message": "Candidate has 5 years of React and TypeScript experience",
            "conversation_id": conv.id,
            "model_provider_id": "deepseek",
        },
        headers={"Authorization": f"Bearer {hrbp_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()

    data = _wait_for_completion(client, data, hrbp_token)
    assert data["status"] == "completed"
    assert data["conversation_id"] == conv.id
    assert data["skill_id"] == skill.id
    assert data["model_provider_id"] == "deepseek"
    assert data["structured_output"] is not None
    assert "screening_dimensions" in data["structured_output"]


def test_get_run_requires_auth(client, db_session):
    resp = client.get("/api/agent/runs/some-run-id")
    assert resp.status_code == 401


def test_get_run_rejects_cross_user(client, db_session, hrbp_token, admin_token):
    seed_local_users(db_session)
    seed_builtin_skills(db_session)
    _install_skill(db_session, "hrbp@example.com", "generate_jd")

    resp = client.post(
        "/api/agent/runs",
        json={
            "skill_id": "generate_jd",
            "user_message": "test",
            "conversation_id": None,
            "model_provider_id": "deepseek",
        },
        headers={"Authorization": f"Bearer {hrbp_token}"},
    )
    assert resp.status_code == 200
    run_data = resp.json()

    run_data = _wait_for_completion(client, run_data, hrbp_token)

    cross_check = client.get(
        f"/api/agent/runs/{run_data['id']}",
        headers={"Authorization": f"Bearer {admin_token}"},
    )
    assert cross_check.status_code == 403


def test_run_handles_empty_input_gracefully(client, db_session, hrbp_token):
    seed_local_users(db_session)
    seed_builtin_skills(db_session)
    _install_skill(db_session, "hrbp@example.com", "generate_jd")

    resp = client.post(
        "/api/agent/runs",
        json={
            "skill_id": "generate_jd",
            "user_message": "",
            "conversation_id": None,
            "model_provider_id": "deepseek",
        },
        headers={"Authorization": f"Bearer {hrbp_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()

    data = _wait_for_completion(client, data, hrbp_token)
    assert data["status"] == "completed"


def test_unconfigured_provider_rejected():
    settings = Settings(
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

    try:
        resolve_chat_adapter(None, settings)
        assert False, "Expected AppError but no exception raised"
    except AppError as e:
        assert e.code == "NO_MODEL_CONFIGURED"

    try:
        resolve_chat_adapter("deepseek", settings)
        assert False, "Expected AppError but no exception raised"
    except AppError as e:
        assert e.code == "PROVIDER_NOT_CONFIGURED"

    try:
        resolve_chat_adapter("openai", settings)
        assert False, "Expected AppError but no exception raised"
    except AppError as e:
        assert e.code == "PROVIDER_NOT_CONFIGURED"

    try:
        resolve_chat_adapter("minimax", settings)
        assert False, "Expected AppError but no exception raised"
    except AppError as e:
        assert e.code == "PROVIDER_NOT_CONFIGURED"

    try:
        resolve_chat_adapter("unknown_provider", settings)
        assert False, "Expected AppError but no exception raised"
    except AppError as e:
        assert e.code == "UNKNOWN_PROVIDER"


def test_create_run_rejects_cross_user_conversation(client, db_session, hrbp_token, admin_token):
    seed_local_users(db_session)
    seed_builtin_skills(db_session)
    _install_skill(db_session, "hrbp@example.com", "generate_jd")

    from app.conversations.service import create_conversation

    admin = db_session.query(User).filter(User.email == "admin@example.com").first()
    admin_conv = create_conversation(db_session, admin.id, "Admin's conversation")

    resp = client.post(
        "/api/agent/runs",
        json={
            "skill_id": "generate_jd",
            "user_message": "test message",
            "conversation_id": admin_conv.id,
            "model_provider_id": "deepseek",
        },
        headers={"Authorization": f"Bearer {hrbp_token}"},
    )
    assert resp.status_code == 403
    data = resp.json()
    assert "another user" in str(data).lower() or "FORBIDDEN" in data.get("code", "")


def test_invoke_mock_mcp_uses_mock_tool_name_from_skill(client, db_session, hrbp_token):
    seed_local_users(db_session)
    seed_builtin_skills(db_session)
    seed_model_configs(db_session)

    from app.skills.models import Skill, UserSkill
    from app.auth.models import User
    import uuid

    skill = Skill(
        id=str(uuid.uuid4()),
        skill_id="custom_branded_skill",
        name="Custom Branded Skill",
        description="A skill using generate_jd under the hood",
        category="recruitment",
        mock_tool_name="generate_jd",
    )
    db_session.add(skill)
    db_session.commit()

    user = db_session.query(User).filter(User.email == "hrbp@example.com").first()
    us = UserSkill(user_id=user.id, skill_id=skill.id)
    db_session.add(us)
    db_session.commit()

    resp = client.post(
        "/api/agent/runs",
        json={
            "skill_id": "custom_branded_skill",
            "user_message": "Senior Python Developer needed",
            "conversation_id": None,
            "model_provider_id": "deepseek",
        },
        headers={"Authorization": f"Bearer {hrbp_token}"},
    )
    assert resp.status_code == 200
    data = resp.json()
    data = _wait_for_completion(client, data, hrbp_token)
    assert data["status"] == "completed"
    assert "job_title" in data["structured_output"]

    from app.agents.models import ToolInvocation

    invocations = (
        db_session.query(ToolInvocation)
        .filter(ToolInvocation.agent_run_id == data["id"])
        .all()
    )
    assert len(invocations) == 1
    assert invocations[0].tool_name == "generate_jd"


def test_generate_html_skill_returns_html_in_structured_output(client, db_session, hrbp_token):
    seed_local_users(db_session)
    seed_builtin_skills(db_session)
    seed_model_configs(db_session)
    _install_skill(db_session, "hrbp@example.com", "generate_html")

    resp = client.post(
        "/api/agent/runs",
        json={
            "skill_id": "generate_html",
            "user_message": "Build a landing page for a SaaS product",
            "conversation_id": None,
            "model_provider_id": "deepseek",
        },
        headers={"Authorization": f"Bearer {hrbp_token}"},
    )
    assert resp.status_code == 200
    data = _wait_for_completion(client, resp.json(), hrbp_token)
    assert data["status"] == "completed"

    output = data["structured_output"]
    # Python 渲染器产出的 HTML 必须包含 LLM 提取的标题
    assert "<title>Test Landing</title>" in output["html"]
    assert output["title"] == "Test Landing"
    assert output["theme"] == "light"
    assert output["primary_color"] == "#2563eb"
    # 旧字段已移除
    assert "artifact_path" not in output
    assert "preview_url" not in output
    # 渲染器把 hero/features section 都画上
    assert 'class="hero"' in output["html"]
    assert 'class="features"' in output["html"]
    # XSS 防御：spec 字段被 HTML 转义
    assert "<script>" not in output["html"]


def test_generate_html_emits_tool_name_in_structured_result_event(client, db_session, hrbp_token):
    """前端依赖 structured_result 事件的 tool_name 字段路由到 HtmlPreviewCard。"""
    seed_local_users(db_session)
    seed_builtin_skills(db_session)
    seed_model_configs(db_session)
    _install_skill(db_session, "hrbp@example.com", "generate_html")

    resp = client.post(
        "/api/agent/runs",
        json={
            "skill_id": "generate_html",
            "user_message": "Landing page",
            "conversation_id": None,
            "model_provider_id": "deepseek",
        },
        headers={"Authorization": f"Bearer {hrbp_token}"},
    )
    run_data = _wait_for_completion(client, resp.json(), hrbp_token)

    events_resp = client.get(
        f"/api/agent/runs/{run_data['id']}/events?token={hrbp_token}",
    )
    assert events_resp.status_code == 200
    body = events_resp.text
    assert "structured_result" in body
    assert '"tool_name": "generate_html"' in body or '"tool_name":"generate_html"' in body
