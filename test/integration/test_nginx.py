import pytest
import requests

host = "http://localhost:8080"


@pytest.mark.parametrize(
    "path, status",
    [
        ("/repository/", 200),
        ("/repository/projectquay/clair-jwt", 200),
        ("/organization/projectquay/", 200),
        ("/user/user1/?tab=settings", 200),
        ("/search?q=", 200),
    ],
)
def test_nginx_ok(path, status):
    r = requests.head(f"{host}{path}", allow_redirects=False)
    assert r.status_code == status
