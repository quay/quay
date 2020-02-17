from data import model
from endpoints.api import api
from endpoints.api.repository import Repository
from endpoints.test.shared import conduct_call
from test.fixtures import *


@pytest.mark.parametrize(
    "user_agent, include_header, expected_code",
    [
        ("curl/whatever", True, 200),
        ("curl/whatever", False, 200),
        ("Mozilla/whatever", True, 200),
        ("Mozilla/5.0", True, 200),
        ("Mozilla/5.0 (Windows NT 5.1; Win64; x64)", False, 400),
    ],
)
def test_require_xhr_from_browser(user_agent, include_header, expected_code, app, client):
    # Create a public repo with a dot in its name.
    user = model.user.get_user("devtable")
    model.repository.create_repository("devtable", "somerepo.bat", user, "public")

    # Retrieve the repository and ensure we either allow it through or fail, depending on the
    # user agent and header.
    params = {"repository": "devtable/somerepo.bat"}

    headers = {
        "User-Agent": user_agent,
    }

    if include_header:
        headers["X-Requested-With"] = "XMLHttpRequest"

    conduct_call(
        client, Repository, api.url_for, "GET", params, headers=headers, expected_code=expected_code
    )
