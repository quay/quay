import pytest
from io import StringIO, BytesIO

from app import app, config_provider
from util.security.signing import Signer


@pytest.fixture(params=["gpg2"])
def signer(request):
    app.config["SIGNING_ENGINE"] = request.param
    return Signer(app, config_provider)


@pytest.mark.parametrize(
    "data, expected_exception",
    [
        ("Unicode strings not allowed", AttributeError),
        (StringIO("Not OK, because this does not implement buffer protocol"), TypeError),
        (b"bytes are not ok. It should be wrapped in a file-like object", AttributeError),
        (BytesIO(b"Thisisfine"), None),
    ],
)
def test_detached_sign(data, expected_exception, signer):
    if expected_exception is not None:
        with pytest.raises(expected_exception):
            signer.detached_sign(data)
    else:
        signer.detached_sign(data)
