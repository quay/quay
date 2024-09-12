# Mock OIDC discovery and token endpoint data
import datetime
import json
import uuid

import jwt

MOCK_DISCOVERY_RESPONSE = {
    "issuer": "https://mock-oidc-server.com",
    "authorization_endpoint": "https://mock-oidc-server.com/authorize",
    "token_endpoint": "https://mock-oidc-server.com/token",
    "jwks_uri": "https://mock-oidc-server.com/.well-known/jwks.json",
    "userinfo_endpoint": "https://mock-oidc-server.com/userinfo",
    "response_types_supported": ["code", "id_token", "token id_token"],
    "subject_types_supported": ["public"],
    "id_token_signing_alg_values_supported": ["RS256"],
}

MOCK_PRIVATE_KEY = """
-----BEGIN RSA PRIVATE KEY-----
MIICXwIBAAKBgQDHd3NJdianKlLgzUmuc/fqYr/xFEDV7Ud3bPnO1N2r5UST7Rlj
XkY2aEf6EL/4FvFZlKW/W6vwFelPMuAZGlZR717IABtj2YLpH8HnO53HqofezZHw
QsahHwxmPJLXAl7Q4sdEg+/06bzsrFlYPWBftWpWKtUiPPK2KtmGdPFEEQIDAQAB
AoGBAKIYNj36oAq04EkDSt9UKqH0wdqeBNpUSwGIM7GbVtD8LbCwuzL/R7urHuLe
fcKUkmmj3NYXHzCp/cF4rJh5yK6317oim3MJjELYyY9K8eAZ2QRO/66JhphZqOD0
XJ6iYqxvX62vxqoixvlXDhWLm3Gtv/57dKGgy5jkjhZUYHphAkEA+haxmLvTKgDD
9yDVOjv2iEPrn1IBDeYRrGcl4byZPzwXmtp7RuXtxdB1irtkoagdjySeYglIdOJ6
+EqKtP/bPQJBAMwucEeQYAHaIHFpYORaY+VlgCT97gcj08BHZByDm5YA0oQxIi+W
jMz0NCdDT9eqUAGszZ6T5PvsOtnFvPOfKWUCQQDzujYuwa4UG1bge7ES5eln97mk
NYktgHDs8kGq8+DuDaR7mD3YZLELvhMvt11lZrAYFvn8VUu2DhsF66+uokOJAkEA
vw14/E2ouDLthpFvG11E+iJWnMaKUl4AxntGvrObAuo0EYOUFGlPyHt8zXxbmlZ/
1IFoSUjjy6KIkrtHCcLVTQJBAJB0NIhj1E8PdES5+s9XfqnMttK4V8lc46bb/3+U
2H0hVBT7vR5sr+QjzEYSATW14c/9QBskZgsbtSEz6zf9+qU=
-----END RSA PRIVATE KEY-----
"""

MOCK_PUBLIC_KEY = """
-----BEGIN PUBLIC KEY-----
MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQDHd3NJdianKlLgzUmuc/fqYr/x
FEDV7Ud3bPnO1N2r5UST7RljXkY2aEf6EL/4FvFZlKW/W6vwFelPMuAZGlZR717I
ABtj2YLpH8HnO53HqofezZHwQsahHwxmPJLXAl7Q4sdEg+/06bzsrFlYPWBftWpW
KtUiPPK2KtmGdPFEEQIDAQAB
-----END PUBLIC KEY-----
"""

MOCK_JWKS_RESPONSE = {
    "keys": [
        {
            "kty": "RSA",
            "n": "x3dzSXYmpypS4M1JrnP36mK_8RRA1e1Hd2z5ztTdq-VEk-0ZY15GNmhH-hC_-BbxWZSlv1ur8BXpTzLgGRpWUe9eyAAbY9mC6R_B5zudx6qH3s2R8ELGoR8MZjyS1wJe0OLHRIPv9Om87KxZWD1gX7VqVirVIjzytirZhnTxRBE",
            "e": "AQAB",
            "kid": "mock-key-id",
        }
    ]
}


# Mock for discovery, JWKS, and token endpoints
def mock_get(obj, url, *args, **kwargs):
    if url == "https://mock-oidc-server.com/.well-known/openid-configuration":
        return MockResponse(MOCK_DISCOVERY_RESPONSE, 200)
    elif url == "https://mock-oidc-server.com/.well-known/jwks.json":
        return MockResponse(MOCK_JWKS_RESPONSE, 200)
    return MockResponse({}, 404)


def mock_request(obj, method, url, *args, **kwargs):
    return mock_get(None, url, *args, **kwargs)


class MockResponse:
    def __init__(self, json_data, status_code):
        self.json_data = json_data
        self.status_code = status_code

    def json(self):
        return self.json_data

    @property
    def text(self):
        return json.dumps(self.json_data)


def generate_mock_oidc_token(
    issuer="https://mock-oidc-server.com",
    subject="mock-subject",
    audience="mock-client-id",
    expiry_seconds=3600,
    issued_at=None,
):
    now = datetime.datetime.now()
    iat = now - datetime.timedelta(seconds=30)
    if issued_at is not None:
        iat = issued_at

    exp = iat + datetime.timedelta(seconds=expiry_seconds)

    payload = {
        "iss": issuer,
        "sub": subject,
        "aud": audience,
        "exp": int(exp.timestamp()),
        "iat": int(iat.timestamp()),
        "nbf": int(iat.timestamp()),
        "nonce": str(uuid.uuid4()),
        "name": "Mock User",
        "preferred_username": "mockuser",
        "given_name": "Mock",
        "family_name": "User",
        "email": "mockuser@test.com",
        "email_verified": True,
    }

    headers = {"kid": "mock-key-id"}

    return jwt.encode(payload, MOCK_PRIVATE_KEY, algorithm="RS256", headers=headers)
