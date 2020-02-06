import pytest
import os
import base64

from backports.tempfile import TemporaryDirectory

from config_app.config_util.config import get_config_as_kube_secret
from util.config.validator import EXTRA_CA_DIRECTORY


def _create_temp_file_structure(file_structure):
    temp_dir = TemporaryDirectory()

    for filename, data in file_structure.items():
        if filename == EXTRA_CA_DIRECTORY:
            extra_ca_dir_path = os.path.join(temp_dir.name, EXTRA_CA_DIRECTORY)
            os.mkdir(extra_ca_dir_path)

            for name, cert_value in data:
                with open(os.path.join(extra_ca_dir_path, name), "w") as f:
                    f.write(cert_value)
        else:
            with open(os.path.join(temp_dir.name, filename), "w") as f:
                f.write(data)

    return temp_dir


@pytest.mark.parametrize(
    "file_structure, expected_secret",
    [
        pytest.param(
            {"config.yaml": "test:true",},
            {"config.yaml": "dGVzdDp0cnVl",},
            id="just a config value",
        ),
        pytest.param(
            {"config.yaml": "test:true", "otherfile.ext": "im a file"},
            {"config.yaml": "dGVzdDp0cnVl", "otherfile.ext": base64.b64encode(b"im a file")},
            id="config and another file",
        ),
        pytest.param(
            {"config.yaml": "test:true", "extra_ca_certs": [("cert.crt", "im a cert!"),]},
            {
                "config.yaml": "dGVzdDp0cnVl",
                "extra_ca_certs_cert.crt": base64.b64encode(b"im a cert!"),
            },
            id="config and an extra cert",
        ),
        pytest.param(
            {
                "config.yaml": "test:true",
                "otherfile.ext": "im a file",
                "extra_ca_certs": [
                    ("cert.crt", "im a cert!"),
                    ("another.crt", "im a different cert!"),
                ],
            },
            {
                "config.yaml": "dGVzdDp0cnVl",
                "otherfile.ext": base64.b64encode(b"im a file"),
                "extra_ca_certs_cert.crt": base64.b64encode(b"im a cert!"),
                "extra_ca_certs_another.crt": base64.b64encode(b"im a different cert!"),
            },
            id="config, files, and extra certs!",
        ),
        pytest.param(
            {"config.yaml": "First line\nSecond line"},
            {"config.yaml": "Rmlyc3QgbGluZQpTZWNvbmQgbGluZQo="},
            id="certificate includes newline characters",
        ),
    ],
)
def test_get_config_as_kube_secret(file_structure, expected_secret):
    temp_dir = _create_temp_file_structure(file_structure)

    secret = get_config_as_kube_secret(temp_dir.name)
    assert secret == expected_secret

    temp_dir.cleanup()
