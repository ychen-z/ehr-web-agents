"""Token quota tests: tracking, daily limit, API endpoint."""

from datetime import date

import pytest

from app.auth.models import User
from app.quota import (
    TokenUsageLog,
    check_daily_quota,
    get_daily_usage,
    record_usage,
)
from app.shared.errors import AppError
from app.shared.seed import seed_local_users


def _get_user_id(db_session) -> str:
    seed_local_users(db_session)
    return db_session.query(User).filter(User.email == "hrbp@example.com").first().id


def test_record_usage_creates_log(db_session):
    user_id = _get_user_id(db_session)
    log = record_usage(
        db_session,
        user_id=user_id,
        run_id="run-123",
        provider_id="deepseek",
        model_name="deepseek-chat",
        prompt_tokens=100,
        completion_tokens=50,
    )
    db_session.commit()
    assert log.total_tokens == 150
    assert log.usage_date == date.today()
    assert log.provider_id == "deepseek"


def test_get_daily_usage_sums_tokens(db_session):
    user_id = _get_user_id(db_session)
    record_usage(db_session, user_id=user_id, run_id=None, provider_id="deepseek", model_name="m", prompt_tokens=100, completion_tokens=50)
    record_usage(db_session, user_id=user_id, run_id=None, provider_id="openai", model_name="m", prompt_tokens=200, completion_tokens=100)
    db_session.commit()

    used = get_daily_usage(db_session, user_id)
    assert used == 450  # 150 + 300


def test_get_daily_usage_zero_when_no_records(db_session):
    user_id = _get_user_id(db_session)
    assert get_daily_usage(db_session, user_id) == 0


def test_check_daily_quota_passes_when_under_limit(db_session):
    user_id = _get_user_id(db_session)
    record_usage(db_session, user_id=user_id, run_id=None, provider_id="x", model_name="m", prompt_tokens=50, completion_tokens=50)
    db_session.commit()
    check_daily_quota(db_session, user_id, daily_limit=200)


def test_check_daily_quota_raises_when_exceeded(db_session):
    user_id = _get_user_id(db_session)
    record_usage(db_session, user_id=user_id, run_id=None, provider_id="x", model_name="m", prompt_tokens=500, completion_tokens=500)
    db_session.commit()

    with pytest.raises(AppError) as exc_info:
        check_daily_quota(db_session, user_id, daily_limit=200)
    assert exc_info.value.status_code == 429
    assert "QUOTA_EXCEEDED" in exc_info.value.code


def test_quota_api_returns_usage(client, db_session, hrbp_token):
    seed_local_users(db_session)
    resp = client.get("/api/quota/usage/today", headers={"Authorization": f"Bearer {hrbp_token}"})
    assert resp.status_code == 200
    data = resp.json()
    assert "used_tokens" in data
    assert "daily_limit" in data
    assert "remaining" in data
    assert "percentage" in data
    assert data["remaining"] == data["daily_limit"] - data["used_tokens"]


def test_quota_api_requires_auth(client, db_session):
    resp = client.get("/api/quota/usage/today")
    assert resp.status_code == 401


def test_agent_run_records_token_usage(client, db_session, hrbp_token):
    """Agent run 结束后 token_usage_logs 有记录。"""
    from app.skills.service import seed_builtin_skills
    from app.models.service import seed_model_configs

    seed_local_users(db_session)
    seed_builtin_skills(db_session)
    seed_model_configs(db_session)

    from app.skills.models import Skill, UserSkill
    user_id = db_session.query(User).filter(User.email == "hrbp@example.com").first().id
    skill = db_session.query(Skill).filter(Skill.skill_id == "generate_jd").first()
    us = UserSkill(user_id=user_id, skill_id=skill.id)
    db_session.add(us)
    db_session.commit()

    resp = client.post(
        "/api/agent/runs",
        json={"skill_id": "generate_jd", "user_message": "Python dev", "conversation_id": None, "model_provider_id": "deepseek"},
        headers={"Authorization": f"Bearer {hrbp_token}"},
    )
    assert resp.status_code == 200
    run_data = resp.json()

    import time
    for _ in range(30):
        r = client.get(f"/api/agent/runs/{run_data['id']}", headers={"Authorization": f"Bearer {hrbp_token}"})
        if r.json()["status"] == "completed":
            break
        time.sleep(0.1)

    logs = db_session.query(TokenUsageLog).filter(TokenUsageLog.run_id == run_data["id"]).all()
    assert len(logs) >= 1
    assert all(log.total_tokens > 0 for log in logs)
