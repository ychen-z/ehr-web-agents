from app.skills.service import seed_builtin_skills
from app.shared.seed import seed_local_users


def test_list_skills_returns_four_recruitment_skills(client, db_session):
    seed_local_users(db_session)
    seed_builtin_skills(db_session)
    login_resp = client.post("/api/auth/login", json={"email": "hrbp@example.com", "password": "password123"})
    token = login_resp.json()["access_token"]

    response = client.get("/api/skills", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 4

    skill_ids = {s["skill_id"] for s in data}
    assert skill_ids == {"generate_jd", "screen_resume", "generate_interview_questions", "summarize_interview_feedback"}

    for skill in data:
        assert "id" in skill
        assert "skill_id" in skill
        assert "name" in skill
        assert "description" in skill
        assert "category" in skill
        assert "installed" in skill
        assert skill["installed"] is False


def test_list_skills_requires_auth(client, db_session):
    response = client.get("/api/skills")
    assert response.status_code == 401


def test_install_skill_marks_as_installed(client, db_session):
    seed_local_users(db_session)
    seed_builtin_skills(db_session)
    login_resp = client.post("/api/auth/login", json={"email": "hrbp@example.com", "password": "password123"})
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    list_before = client.get("/api/skills", headers=headers)
    before_data = list_before.json()
    jd_before = next(s for s in before_data if s["skill_id"] == "generate_jd")
    assert jd_before["installed"] is False

    install_resp = client.post("/api/skills/generate_jd/install", headers=headers)
    assert install_resp.status_code == 200
    install_data = install_resp.json()
    assert install_data["installed"] is True

    list_after = client.get("/api/skills", headers=headers)
    after_data = list_after.json()
    jd_after = next(s for s in after_data if s["skill_id"] == "generate_jd")
    assert jd_after["installed"] is True


def test_uninstall_skill_marks_as_not_installed(client, db_session):
    seed_local_users(db_session)
    seed_builtin_skills(db_session)
    login_resp = client.post("/api/auth/login", json={"email": "hrbp@example.com", "password": "password123"})
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    client.post("/api/skills/generate_jd/install", headers=headers)

    list_installed = client.get("/api/skills", headers=headers)
    jd_installed = next(s for s in list_installed.json() if s["skill_id"] == "generate_jd")
    assert jd_installed["installed"] is True

    uninstall_resp = client.delete("/api/skills/generate_jd/install", headers=headers)
    assert uninstall_resp.status_code == 200
    uninstall_data = uninstall_resp.json()
    assert uninstall_data["installed"] is False

    list_after = client.get("/api/skills", headers=headers)
    jd_after = next(s for s in list_after.json() if s["skill_id"] == "generate_jd")
    assert jd_after["installed"] is False


def test_install_requires_auth(client, db_session):
    response = client.post("/api/skills/generate_jd/install")
    assert response.status_code == 401


def test_uninstall_requires_auth(client, db_session):
    response = client.delete("/api/skills/generate_jd/install")
    assert response.status_code == 401


def test_install_state_is_per_user(client, db_session):
    seed_local_users(db_session)
    seed_builtin_skills(db_session)
    hrbp_resp = client.post("/api/auth/login", json={"email": "hrbp@example.com", "password": "password123"})
    hrbp_token = hrbp_resp.json()["access_token"]
    admin_resp = client.post("/api/auth/login", json={"email": "admin@example.com", "password": "password123"})
    admin_token = admin_resp.json()["access_token"]

    client.post("/api/skills/generate_jd/install", headers={"Authorization": f"Bearer {hrbp_token}"})

    hrbp_list = client.get("/api/skills", headers={"Authorization": f"Bearer {hrbp_token}"})
    jd_hrbp = next(s for s in hrbp_list.json() if s["skill_id"] == "generate_jd")
    assert jd_hrbp["installed"] is True

    admin_list = client.get("/api/skills", headers={"Authorization": f"Bearer {admin_token}"})
    jd_admin = next(s for s in admin_list.json() if s["skill_id"] == "generate_jd")
    assert jd_admin["installed"] is False


def test_duplicate_install_is_idempotent(client, db_session):
    seed_local_users(db_session)
    seed_builtin_skills(db_session)
    login_resp = client.post("/api/auth/login", json={"email": "hrbp@example.com", "password": "password123"})
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    first = client.post("/api/skills/generate_jd/install", headers=headers)
    assert first.status_code == 200
    assert first.json()["installed"] is True

    second = client.post("/api/skills/generate_jd/install", headers=headers)
    assert second.status_code == 200
    assert second.json()["installed"] is True

    from app.auth.models import User
    from app.skills.models import UserSkill

    user = db_session.query(User).filter(User.email == "hrbp@example.com").first()
    rows = db_session.query(UserSkill).filter(UserSkill.user_id == user.id).all()
    assert len(rows) == 1


def test_install_unknown_skill_returns_404(client, db_session):
    seed_local_users(db_session)
    seed_builtin_skills(db_session)
    login_resp = client.post("/api/auth/login", json={"email": "hrbp@example.com", "password": "password123"})
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    response = client.post("/api/skills/nonexistent_skill/install", headers=headers)
    assert response.status_code == 404


def test_uninstall_unknown_skill_returns_404(client, db_session):
    seed_local_users(db_session)
    seed_builtin_skills(db_session)
    login_resp = client.post("/api/auth/login", json={"email": "hrbp@example.com", "password": "password123"})
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    response = client.delete("/api/skills/nonexistent_skill/install", headers=headers)
    assert response.status_code == 404
