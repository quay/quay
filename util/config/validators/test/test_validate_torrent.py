import pytest

from config import build_requests_session
from httmock import urlmatch, HTTMock

from app import instance_keys
from util.config.validator import ValidatorContext
from util.config.validators import ConfigValidationException
from util.config.validators.validate_torrent import BittorrentValidator

from test.fixtures import *


@pytest.mark.parametrize(
    "unvalidated_config,expected",
    [
        ({}, ConfigValidationException),
        ({"BITTORRENT_ANNOUNCE_URL": "http://faketorrent/announce"}, None),
    ],
)
def test_validate_torrent(unvalidated_config, expected, app):
    announcer_hit = [False]

    @urlmatch(netloc=r"faketorrent", path="/announce")
    def handler(url, request):
        announcer_hit[0] = True
        return {"status_code": 200, "content": ""}

    with HTTMock(handler):
        validator = BittorrentValidator()
        if expected is not None:
            with pytest.raises(expected):
                config = ValidatorContext(unvalidated_config, instance_keys=instance_keys)
                config.http_client = build_requests_session()

                validator.validate(config)
            assert not announcer_hit[0]
        else:
            config = ValidatorContext(unvalidated_config, instance_keys=instance_keys)
            config.http_client = build_requests_session()

            validator.validate(config)
            assert announcer_hit[0]
