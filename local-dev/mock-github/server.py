"""
Mock GitHub OAuth server for Playwright E2E testing.

Implements the GitHub OAuth API endpoints that Quay's GithubOAuthService
calls during login, attach, and CLI token flows. Designed to run alongside
Quay in docker-compose for CI testing.
"""

import secrets
from flask import Flask, request, redirect, jsonify, Response
from urllib.parse import urlencode

app = Flask(__name__)

MOCK_USERS = {
    "admin_github": {
        "id": 1001,
        "login": "admin_github",
        "email": "admin_github@example.com",
        "orgs": ["quay-dev"],
    },
    "testuser_github": {
        "id": 1002,
        "login": "testuser_github",
        "email": "testuser_github@example.com",
        "orgs": ["quay-dev"],
    },
}

EXPECTED_CLIENT_ID = "mock-github-client-id"
EXPECTED_CLIENT_SECRET = "mock-github-client-secret"

# In-memory stores: code -> username, token -> username
pending_codes = {}
active_tokens = {}


@app.route("/login/oauth/authorize")
def authorize():
    client_id = request.args.get("client_id", "")
    redirect_uri = request.args.get("redirect_uri", "")
    state = request.args.get("state", "")
    force_error = request.args.get("force_error", "")

    if force_error:
        params = {"error": force_error, "state": state}
        return redirect(f"{redirect_uri}?{urlencode(params)}")

    users_options = "".join(
        f'<option value="{u}">{u}</option>' for u in MOCK_USERS
    )

    return Response(
        f"""<!DOCTYPE html>
<html>
<head><title>Mock GitHub Login</title></head>
<body>
  <h1>Mock GitHub OAuth</h1>
  <form method="POST" action="/login/oauth/authorize/decision">
    <input type="hidden" name="client_id" value="{client_id}">
    <input type="hidden" name="redirect_uri" value="{redirect_uri}">
    <input type="hidden" name="state" value="{state}">
    <label for="username">User:</label>
    <select name="username" id="username">{users_options}</select>
    <br><br>
    <button type="submit" name="action" value="approve">Login</button>
    <button type="submit" name="action" value="deny">Deny</button>
  </form>
</body>
</html>""",
        content_type="text/html",
    )


@app.route("/login/oauth/authorize/decision", methods=["POST"])
def authorize_decision():
    redirect_uri = request.form.get("redirect_uri", "")
    state = request.form.get("state", "")
    action = request.form.get("action", "")
    username = request.form.get("username", "")

    if action == "deny":
        params = {
            "error": "access_denied",
            "error_description": "User denied access",
            "state": state,
        }
        return redirect(f"{redirect_uri}?{urlencode(params)}")

    code = secrets.token_urlsafe(16)
    pending_codes[code] = username

    params = {"code": code, "state": state}
    return redirect(f"{redirect_uri}?{urlencode(params)}")


@app.route("/login/oauth/access_token", methods=["POST"])
def access_token():
    code = request.args.get("code") or request.form.get("code", "")
    client_id = request.args.get("client_id") or request.form.get("client_id", "")
    client_secret = request.args.get("client_secret") or request.form.get(
        "client_secret", ""
    )

    if client_id != EXPECTED_CLIENT_ID or client_secret != EXPECTED_CLIENT_SECRET:
        return jsonify({"error": "bad_credentials"}), 401

    username = pending_codes.pop(code, None)
    if not username:
        return jsonify({"error": "bad_verification_code"}), 400

    token = secrets.token_urlsafe(32)
    active_tokens[token] = username

    return jsonify({"access_token": token, "token_type": "bearer", "scope": "user:email"})


def _get_user_from_token():
    auth = request.headers.get("Authorization", "")
    token = auth.replace("Bearer ", "").replace("token ", "")
    username = active_tokens.get(token)
    if not username or username not in MOCK_USERS:
        return None
    return MOCK_USERS[username]


@app.route("/api/v3/user")
def user_info():
    user = _get_user_from_token()
    if not user:
        return jsonify({"message": "Bad credentials"}), 401
    return jsonify({"id": user["id"], "login": user["login"]})


@app.route("/api/v3/user/emails")
def user_emails():
    user = _get_user_from_token()
    if not user:
        return jsonify({"message": "Bad credentials"}), 401
    return jsonify([{"email": user["email"], "verified": True, "primary": True}])


@app.route("/api/v3/user/orgs")
def user_orgs():
    user = _get_user_from_token()
    if not user:
        return jsonify({"message": "Bad credentials"}), 401
    return jsonify([{"login": org} for org in user["orgs"]])


@app.route("/api/v3/")
def api_root():
    resp = jsonify({"message": "Mock GitHub API"})
    resp.headers["X-GitHub-Request-Id"] = "mock-request-id"
    return resp


@app.route("/api/v3/applications/<client_id>/tokens/foo")
def validate_credentials(client_id):
    auth = request.authorization
    if not auth or auth.username != EXPECTED_CLIENT_ID or auth.password != EXPECTED_CLIENT_SECRET:
        return jsonify({"message": "Bad credentials"}), 401
    return jsonify({"message": "Not Found"}), 404


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=9090)
