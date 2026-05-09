import time

import pytest

from app.shared.errors import AppError
from app.shared.seed import seed_local_users


def test_create_conversation(client, db_session):
    seed_local_users(db_session)
    login_resp = client.post("/api/auth/login", json={"email": "hrbp@example.com", "password": "password123"})
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    response = client.post("/api/conversations", json={"title": "Recruitment chat"}, headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Recruitment chat"
    assert "id" in data
    assert "user_id" in data
    assert "created_at" in data
    assert "updated_at" in data


def test_create_conversation_requires_auth(client, db_session):
    response = client.post("/api/conversations", json={"title": "Test"})
    assert response.status_code == 401


def test_list_conversations_returns_only_own(client, db_session):
    seed_local_users(db_session)
    hrbp_resp = client.post("/api/auth/login", json={"email": "hrbp@example.com", "password": "password123"})
    hrbp_token = hrbp_resp.json()["access_token"]
    hrbp_headers = {"Authorization": f"Bearer {hrbp_token}"}

    admin_resp = client.post("/api/auth/login", json={"email": "admin@example.com", "password": "password123"})
    admin_token = admin_resp.json()["access_token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    client.post("/api/conversations", json={"title": "HRBP chat"}, headers=hrbp_headers)
    client.post("/api/conversations", json={"title": "Admin chat"}, headers=admin_headers)

    hrbp_list = client.get("/api/conversations", headers=hrbp_headers)
    assert hrbp_list.status_code == 200
    hrbp_data = hrbp_list.json()
    assert isinstance(hrbp_data, list)
    assert len(hrbp_data) == 1
    assert hrbp_data[0]["title"] == "HRBP chat"

    admin_list = client.get("/api/conversations", headers=admin_headers)
    assert admin_list.status_code == 200
    admin_data = admin_list.json()
    assert len(admin_data) == 1
    assert admin_data[0]["title"] == "Admin chat"


def test_list_conversations_requires_auth(client, db_session):
    response = client.get("/api/conversations")
    assert response.status_code == 401


def test_list_messages_for_conversation(client, db_session):
    seed_local_users(db_session)
    login_resp = client.post("/api/auth/login", json={"email": "hrbp@example.com", "password": "password123"})
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    conv_resp = client.post("/api/conversations", json={"title": "Chat"}, headers=headers)
    conversation_id = conv_resp.json()["id"]

    from app.conversations.service import create_message

    create_message(db_session, conversation_id=conversation_id, role="user", content="Hello")
    create_message(db_session, conversation_id=conversation_id, role="assistant", content="Hi there!")

    response = client.get(f"/api/conversations/{conversation_id}/messages", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 2
    assert data[0]["role"] == "user"
    assert data[0]["content"] == "Hello"
    assert data[1]["role"] == "assistant"
    assert data[1]["content"] == "Hi there!"


def test_list_messages_requires_auth(client, db_session):
    seed_local_users(db_session)
    login_resp = client.post("/api/auth/login", json={"email": "hrbp@example.com", "password": "password123"})
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    conv_resp = client.post("/api/conversations", json={"title": "Chat"}, headers=headers)
    conversation_id = conv_resp.json()["id"]

    response = client.get(f"/api/conversations/{conversation_id}/messages")
    assert response.status_code == 401


def test_cannot_access_other_user_conversation(client, db_session):
    seed_local_users(db_session)
    hrbp_resp = client.post("/api/auth/login", json={"email": "hrbp@example.com", "password": "password123"})
    hrbp_token = hrbp_resp.json()["access_token"]
    hrbp_headers = {"Authorization": f"Bearer {hrbp_token}"}

    admin_resp = client.post("/api/auth/login", json={"email": "admin@example.com", "password": "password123"})
    admin_token = admin_resp.json()["access_token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    conv_resp = client.post("/api/conversations", json={"title": "Admin private"}, headers=admin_headers)
    conversation_id = conv_resp.json()["id"]

    response = client.get(f"/api/conversations/{conversation_id}/messages", headers=hrbp_headers)
    assert response.status_code == 404


def test_cannot_access_other_user_messages(client, db_session):
    seed_local_users(db_session)
    hrbp_resp = client.post("/api/auth/login", json={"email": "hrbp@example.com", "password": "password123"})
    hrbp_token = hrbp_resp.json()["access_token"]
    hrbp_headers = {"Authorization": f"Bearer {hrbp_token}"}

    admin_resp = client.post("/api/auth/login", json={"email": "admin@example.com", "password": "password123"})
    admin_token = admin_resp.json()["access_token"]
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    conv_resp = client.post("/api/conversations", json={"title": "Admin private"}, headers=admin_headers)
    conversation_id = conv_resp.json()["id"]

    from app.conversations.service import create_message
    create_message(db_session, conversation_id=conversation_id, role="user", content="Secret message")

    response = client.get(f"/api/conversations/{conversation_id}/messages", headers=hrbp_headers)
    assert response.status_code == 404


def test_create_conversation_without_title_defaults(client, db_session):
    seed_local_users(db_session)
    login_resp = client.post("/api/auth/login", json={"email": "hrbp@example.com", "password": "password123"})
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    response = client.post("/api/conversations", json={}, headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert "id" in data


def test_messages_list_returns_empty_for_new_conversation(client, db_session):
    seed_local_users(db_session)
    login_resp = client.post("/api/auth/login", json={"email": "hrbp@example.com", "password": "password123"})
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    conv_resp = client.post("/api/conversations", json={"title": "Empty chat"}, headers=headers)
    conversation_id = conv_resp.json()["id"]

    response = client.get(f"/api/conversations/{conversation_id}/messages", headers=headers)
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 0


def test_create_message_bumps_conversation_updated_at(db_session):
    from app.conversations.service import create_conversation, create_message, get_conversation
    from app.auth.models import User
    from app.shared.seed import seed_local_users

    seed_local_users(db_session)
    user = db_session.query(User).filter(User.email == "hrbp@example.com").first()

    conv = create_conversation(db_session, user.id, title="Before message")
    original_updated_at = conv.updated_at

    time.sleep(0.1)

    create_message(db_session, conv.id, role="user", content="Hello world")

    refreshed = get_conversation(db_session, conv.id, user.id)
    assert refreshed is not None
    assert refreshed.updated_at > original_updated_at


def test_create_message_rejects_invalid_role(db_session):
    from app.conversations.service import create_conversation, create_message
    from app.auth.models import User
    from app.shared.seed import seed_local_users

    seed_local_users(db_session)
    user = db_session.query(User).filter(User.email == "hrbp@example.com").first()
    conv = create_conversation(db_session, user.id, title="Role test")

    with pytest.raises(AppError) as exc_info:
        create_message(db_session, conv.id, role="invalid_role", content="Bad role")
    assert exc_info.value.code == "INVALID_MESSAGE_ROLE"


def test_create_message_accepts_valid_roles(db_session):
    from app.conversations.service import create_conversation, create_message
    from app.auth.models import User
    from app.shared.seed import seed_local_users

    seed_local_users(db_session)
    user = db_session.query(User).filter(User.email == "hrbp@example.com").first()
    conv = create_conversation(db_session, user.id, title="Role test")

    for role in ("user", "assistant", "system"):
        msg = create_message(db_session, conv.id, role=role, content=f"Message as {role}")
        assert msg.role == role


def test_list_conversations_respects_limit_and_offset(client, db_session):
    seed_local_users(db_session)
    login_resp = client.post("/api/auth/login", json={"email": "hrbp@example.com", "password": "password123"})
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    for i in range(5):
        client.post("/api/conversations", json={"title": f"Chat {i}"}, headers=headers)

    all_resp = client.get("/api/conversations?limit=10", headers=headers)
    assert all_resp.status_code == 200
    assert len(all_resp.json()) == 5

    limited = client.get("/api/conversations?limit=2&offset=0", headers=headers)
    assert limited.status_code == 200
    assert len(limited.json()) == 2

    offset_resp = client.get("/api/conversations?limit=10&offset=3", headers=headers)
    assert offset_resp.status_code == 200
    assert len(offset_resp.json()) == 2


def test_list_messages_respects_limit_and_offset(client, db_session):
    seed_local_users(db_session)
    login_resp = client.post("/api/auth/login", json={"email": "hrbp@example.com", "password": "password123"})
    token = login_resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}

    conv_resp = client.post("/api/conversations", json={"title": "Paginated"}, headers=headers)
    conversation_id = conv_resp.json()["id"]

    from app.conversations.service import create_message
    for i in range(5):
        create_message(db_session, conversation_id=conversation_id, role="user", content=f"Message {i}")

    all_resp = client.get(f"/api/conversations/{conversation_id}/messages?limit=10", headers=headers)
    assert all_resp.status_code == 200
    assert len(all_resp.json()) == 5

    limited = client.get(f"/api/conversations/{conversation_id}/messages?limit=2&offset=1", headers=headers)
    assert limited.status_code == 200
    data = limited.json()
    assert len(data) == 2
    assert data[0]["content"] == "Message 1"
    assert data[1]["content"] == "Message 2"


def test_unauthenticated_list_messages_on_nonexistent_conv_returns_401(client, db_session):
    response = client.get("/api/conversations/nonexistent-id/messages")
    assert response.status_code == 401
