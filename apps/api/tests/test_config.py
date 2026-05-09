from app.shared.config import Settings


def test_database_url_is_built_from_mysql_settings():
    settings = Settings(
        mysql_host="db",
        mysql_port=3306,
        mysql_database="ehr_agents",
        mysql_user="user",
        mysql_password="pass",
        jwt_secret="secret",
        cors_origins="http://localhost:5173",
    )
    assert settings.database_url == "mysql+pymysql://user:pass@db:3306/ehr_agents"
    assert settings.cors_origin_list == ["http://localhost:5173"]
