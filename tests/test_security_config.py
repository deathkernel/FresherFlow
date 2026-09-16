import importlib


def test_admin_credentials_are_not_default(monkeypatch):
    monkeypatch.delenv("ADMIN_EMAIL", raising=False)
    monkeypatch.delenv("ADMIN_PASSWORD", raising=False)

    import admin_config
    importlib.reload(admin_config)

    assert admin_config.get_admin_credentials() == (None, None)


def test_admin_credentials_are_loaded_from_environment(monkeypatch):
    monkeypatch.setenv("ADMIN_EMAIL", "Admin@Example.com")
    monkeypatch.setenv("ADMIN_PASSWORD", "a-strong-test-password")

    import admin_config
    importlib.reload(admin_config)

    assert admin_config.get_admin_credentials() == (
        "admin@example.com",
        "a-strong-test-password",
    )
