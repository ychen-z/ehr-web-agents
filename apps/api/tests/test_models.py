from unittest.mock import MagicMock, patch

from app.models.adapters import ChatModelAdapter, DeepSeekChatAdapter, MinimaxChatAdapter, OpenAIChatAdapter
from app.models.service import list_models, seed_model_configs
from app.shared.config import Settings
from app.shared.seed import seed_local_users


def test_list_models_returns_three_providers(client, db_session):
    seed_local_users(db_session)
    seed_model_configs(db_session)
    login_resp = client.post("/api/auth/login", json={"email": "hrbp@example.com", "password": "password123"})
    token = login_resp.json()["access_token"]

    response = client.get("/api/models", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    data = response.json()
    assert isinstance(data, list)
    assert len(data) == 3

    provider_ids = {m["provider_id"] for m in data}
    assert provider_ids == {"deepseek", "openai", "minimax"}


def test_model_entry_structure(client, db_session):
    seed_local_users(db_session)
    seed_model_configs(db_session)
    login_resp = client.post("/api/auth/login", json={"email": "hrbp@example.com", "password": "password123"})
    token = login_resp.json()["access_token"]

    response = client.get("/api/models", headers={"Authorization": f"Bearer {token}"})
    data = response.json()

    for model in data:
        assert "provider_id" in model
        assert "display_name" in model
        assert "default_model_name" in model
        assert "configured" in model
        assert "enabled" in model
        assert isinstance(model["configured"], bool)
        assert isinstance(model["enabled"], bool)
        assert "api_key" not in model


def test_models_requires_auth(client, db_session):
    response = client.get("/api/models")
    assert response.status_code == 401


def test_configured_is_false_without_api_keys(client, db_session):
    seed_local_users(db_session)
    seed_model_configs(db_session)
    login_resp = client.post("/api/auth/login", json={"email": "hrbp@example.com", "password": "password123"})
    token = login_resp.json()["access_token"]

    response = client.get("/api/models", headers={"Authorization": f"Bearer {token}"})
    data = response.json()

    for model in data:
        assert model["configured"] is False


def test_list_models_requires_db():
    settings = Settings(
        mysql_host="localhost",
        mysql_port=3306,
        mysql_database="ehr_agents",
        mysql_user="test",
        mysql_password="test",
        jwt_secret="test",
        cors_origins="http://localhost:5173",
        deepseek_api_key="sk-test",
    )
    try:
        list_models(settings)
        raise AssertionError("Expected TypeError for missing db argument")
    except TypeError:
        pass


def test_list_models_from_db(db_session):
    seed_model_configs(db_session)
    settings = Settings(
        mysql_host="localhost",
        mysql_port=3306,
        mysql_database="ehr_agents",
        mysql_user="test",
        mysql_password="test",
        jwt_secret="test",
        cors_origins="http://localhost:5173",
        deepseek_api_key="sk-test",
        openai_api_key="",
        minimax_api_key="",
    )

    models = list_models(settings, db_session)
    assert len(models) == 3

    ds = next(m for m in models if m["provider_id"] == "deepseek")
    oa = next(m for m in models if m["provider_id"] == "openai")
    mm = next(m for m in models if m["provider_id"] == "minimax")
    assert ds["configured"] is True
    assert oa["configured"] is False
    assert mm["configured"] is False


def test_seed_models_is_idempotent(db_session):
    from app.models.models import ModelConfig

    seed_model_configs(db_session)
    seed_model_configs(db_session)

    rows = db_session.query(ModelConfig).all()
    assert len(rows) == 3


def test_deepseek_adapter_follows_protocol():
    settings = Settings(
        mysql_host="localhost",
        mysql_port=3306,
        mysql_database="test",
        mysql_user="test",
        mysql_password="test",
        jwt_secret="test",
        cors_origins="http://localhost:5173",
        deepseek_api_key="sk-test",
    )
    adapter = DeepSeekChatAdapter(settings)
    assert isinstance(adapter, ChatModelAdapter)


def test_openai_adapter_follows_protocol():
    settings = Settings(
        mysql_host="localhost",
        mysql_port=3306,
        mysql_database="test",
        mysql_user="test",
        mysql_password="test",
        jwt_secret="test",
        cors_origins="http://localhost:5173",
        openai_api_key="sk-test",
    )
    adapter = OpenAIChatAdapter(settings)
    assert isinstance(adapter, ChatModelAdapter)


def test_minimax_adapter_follows_protocol():
    settings = Settings(
        mysql_host="localhost",
        mysql_port=3306,
        mysql_database="test",
        mysql_user="test",
        mysql_password="test",
        jwt_secret="test",
        cors_origins="http://localhost:5173",
        minimax_api_key="sk-test",
    )
    adapter = MinimaxChatAdapter(settings)
    assert isinstance(adapter, ChatModelAdapter)


def test_adapter_requires_api_key():
    settings = Settings(
        mysql_host="localhost",
        mysql_port=3306,
        mysql_database="test",
        mysql_user="test",
        mysql_password="test",
        jwt_secret="test",
        cors_origins="http://localhost:5173",
        deepseek_api_key="",
    )
    adapter = DeepSeekChatAdapter(settings)
    try:
        adapter.invoke([{"role": "user", "content": "hello"}])
    except RuntimeError as e:
        assert "API key not configured" in str(e)
    else:
        raise AssertionError("Expected RuntimeError for missing API key")


def _make_mock_completion(content: str):
    mock_choice = MagicMock()
    mock_choice.message.content = content
    mock_completion = MagicMock()
    mock_completion.choices = [mock_choice]
    return mock_completion


def test_deepseek_adapter_returns_text():
    settings = Settings(
        mysql_host="localhost",
        mysql_port=3306,
        mysql_database="test",
        mysql_user="test",
        mysql_password="test",
        jwt_secret="test",
        cors_origins="http://localhost:5173",
        deepseek_api_key="sk-test-key",
        deepseek_model="deepseek-chat",
    )
    adapter = DeepSeekChatAdapter(settings)

    with patch("app.models.adapters.OpenAI") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = _make_mock_completion("Hello from DeepSeek")
        mock_client_cls.return_value = mock_client

        result = adapter.invoke([{"role": "user", "content": "Hi"}])
        assert result == "Hello from DeepSeek"
        mock_client_cls.assert_called_once_with(api_key="sk-test-key", base_url="https://api.deepseek.com")
        mock_client.chat.completions.create.assert_called_once_with(
            model="deepseek-chat",
            messages=[{"role": "user", "content": "Hi"}],
        )


def test_openai_adapter_returns_text():
    settings = Settings(
        mysql_host="localhost",
        mysql_port=3306,
        mysql_database="test",
        mysql_user="test",
        mysql_password="test",
        jwt_secret="test",
        cors_origins="http://localhost:5173",
        openai_api_key="sk-test-key",
        openai_model="gpt-4o-mini",
    )
    adapter = OpenAIChatAdapter(settings)

    with patch("app.models.adapters.OpenAI") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = _make_mock_completion("Hello from OpenAI")
        mock_client_cls.return_value = mock_client

        result = adapter.invoke([{"role": "user", "content": "Hi"}])
        assert result == "Hello from OpenAI"
        mock_client_cls.assert_called_once_with(api_key="sk-test-key")
        mock_client.chat.completions.create.assert_called_once_with(
            model="gpt-4o-mini",
            messages=[{"role": "user", "content": "Hi"}],
        )


def test_minimax_adapter_returns_text():
    settings = Settings(
        mysql_host="localhost",
        mysql_port=3306,
        mysql_database="test",
        mysql_user="test",
        mysql_password="test",
        jwt_secret="test",
        cors_origins="http://localhost:5173",
        minimax_api_key="sk-test-key",
        minimax_base_url="https://api.minimax.chat/v1",
        minimax_model="MiniMax-M1",
    )
    adapter = MinimaxChatAdapter(settings)

    with patch("app.models.adapters.OpenAI") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = _make_mock_completion("Hello from Minimax")
        mock_client_cls.return_value = mock_client

        result = adapter.invoke([{"role": "user", "content": "Hi"}])
        assert result == "Hello from Minimax"
        mock_client_cls.assert_called_once_with(api_key="sk-test-key", base_url="https://api.minimax.chat/v1")
        mock_client.chat.completions.create.assert_called_once_with(
            model="MiniMax-M1",
            messages=[{"role": "user", "content": "Hi"}],
        )


def test_deepseek_adapter_raises_on_empty_content():
    settings = Settings(
        mysql_host="localhost",
        mysql_port=3306,
        mysql_database="test",
        mysql_user="test",
        mysql_password="test",
        jwt_secret="test",
        cors_origins="http://localhost:5173",
        deepseek_api_key="sk-test",
    )
    adapter = DeepSeekChatAdapter(settings)

    with patch("app.models.adapters.OpenAI") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = _make_mock_completion("")
        mock_client_cls.return_value = mock_client

        try:
            adapter.invoke([{"role": "user", "content": "Hi"}])
        except RuntimeError as e:
            assert "no content" in str(e).lower()
        else:
            raise AssertionError("Expected RuntimeError for empty content")


def test_openai_adapter_raises_on_empty_content():
    settings = Settings(
        mysql_host="localhost",
        mysql_port=3306,
        mysql_database="test",
        mysql_user="test",
        mysql_password="test",
        jwt_secret="test",
        cors_origins="http://localhost:5173",
        openai_api_key="sk-test",
    )
    adapter = OpenAIChatAdapter(settings)

    with patch("app.models.adapters.OpenAI") as mock_client_cls:
        mock_client = MagicMock()
        mock_client.chat.completions.create.return_value = _make_mock_completion("")
        mock_client_cls.return_value = mock_client

        try:
            adapter.invoke([{"role": "user", "content": "Hi"}])
        except RuntimeError as e:
            assert "no content" in str(e).lower()
        else:
            raise AssertionError("Expected RuntimeError for empty content")
