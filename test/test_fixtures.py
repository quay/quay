from test.fixtures import _database_uri_for_schema, _test_database_schema


def test_test_database_schema_uses_xdist_worker(monkeypatch):
    monkeypatch.setenv("TEST_DATABASE_URI", "postgresql://quay:quay@localhost/quay_ci")
    monkeypatch.setenv("PYTEST_XDIST_WORKER", "gw3")

    assert _test_database_schema() == "quay_test_gw3"


def test_test_database_schema_uses_main_without_xdist(monkeypatch):
    monkeypatch.setenv("TEST_DATABASE_URI", "postgresql://quay:quay@localhost/quay_ci")
    monkeypatch.delenv("PYTEST_XDIST_WORKER", raising=False)

    assert _test_database_schema() == "quay_test_main"


def test_test_database_schema_is_disabled_for_mysql(monkeypatch):
    monkeypatch.setenv("TEST_DATABASE_URI", "mysql://quay:quay@localhost/quay_ci")

    assert _test_database_schema() is None


def test_database_uri_for_schema_sets_postgresql_search_path():
    uri = "postgresql://quay:quay@localhost/quay_ci?connect_timeout=5"

    isolated_uri = _database_uri_for_schema(uri, "quay_test_gw0")

    assert "connect_timeout=5" in isolated_uri
    assert "options=-c+search_path%3Dquay_test_gw0" in isolated_uri
