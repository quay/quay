from app import app
from endpoints.csrf import generate_csrf_token


def test_generate_csrf_token():
    with app.test_request_context():
        token = generate_csrf_token()
        assert isinstance(token, str)
