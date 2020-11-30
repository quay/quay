import pytest
import time
import uuid

from buildman.build_token import (
    build_token,
    verify_build_token,
    ANONYMOUS_SUB,
    BUILD_JOB_REGISTRATION_TYPE,
    BUILD_JOB_TOKEN_TYPE,
    InvalidBuildTokenException,
)

from test.fixtures import *

from app import app, instance_keys


@pytest.mark.parametrize(
    "token_type, expected_exception",
    [
        pytest.param(BUILD_JOB_REGISTRATION_TYPE, None, id="valid"),
        pytest.param(
            BUILD_JOB_TOKEN_TYPE,
            "Build token type in JWT does not match expected type: %s" % BUILD_JOB_TOKEN_TYPE,
            id="Invalid token type",
        ),
    ],
)
def test_registration_build_token(initialized_db, token_type, expected_exception):
    build_id = str(uuid.uuid4())
    job_id = "building/" + build_id
    token = build_token(
        app.config["SERVER_HOSTNAME"],
        BUILD_JOB_REGISTRATION_TYPE,
        build_id,
        job_id,
        int(time.time()) + 360,
        instance_keys,
    )

    if expected_exception is not None:
        with pytest.raises(InvalidBuildTokenException) as ibe:
            payload = verify_build_token(
                token,
                app.config["SERVER_HOSTNAME"],
                token_type,
                instance_keys,
            )
        assert ibe.match(expected_exception)
    else:
        payload = verify_build_token(
            token,
            app.config["SERVER_HOSTNAME"],
            token_type,
            instance_keys,
        )

        assert payload["aud"] == app.config["SERVER_HOSTNAME"]
        assert payload["sub"] == ANONYMOUS_SUB
        assert payload["iss"] == instance_keys.service_name
        assert payload["context"]["build_id"] == build_id
        assert payload["context"]["job_id"] == job_id
        assert payload["context"]["token_type"] == BUILD_JOB_REGISTRATION_TYPE
