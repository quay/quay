from data.database import get_epoch_timestamp_ms
from data.registry_model.datatypes import Tag


class TestTag:
    def test_expired_with_tag_expired_a_minute_ago(self):
        now_ms = get_epoch_timestamp_ms()
        one_hour_ago_ms = now_ms - 3600 * 1000
        one_minute_ago_ms = now_ms - 60 * 1000
        tag = Tag(
            name="latest",
            reversion=False,
            manifest_digest="abc123",
            lifetime_start_ts=one_hour_ago_ms // 1000,
            lifetime_start_ms=one_hour_ago_ms,
            lifetime_end_ts=one_minute_ago_ms // 1000,
            lifetime_end_ms=one_minute_ago_ms,
        )
        assert tag.expired

    def test_expired_with_tag_expired_now(self):
        now_ms = get_epoch_timestamp_ms()
        one_hour_ago_ms = now_ms - 3600 * 1000
        tag = Tag(
            name="latest",
            reversion=False,
            manifest_digest="abc123",
            lifetime_start_ts=one_hour_ago_ms // 1000,
            lifetime_start_ms=one_hour_ago_ms,
            lifetime_end_ts=now_ms // 1000,
            lifetime_end_ms=now_ms,
        )
        assert tag.expired

    def test_expired_before_tag_expiration(self):
        now_ms = get_epoch_timestamp_ms()
        one_hour_ago_ms = now_ms - 3600 * 1000
        one_hour_from_now_ms = now_ms + 3600 * 1000
        tag = Tag(
            name="latest",
            reversion=False,
            manifest_digest="abc123",
            lifetime_start_ts=one_hour_ago_ms // 1000,
            lifetime_start_ms=one_hour_ago_ms,
            lifetime_end_ts=one_hour_from_now_ms // 1000,
            lifetime_end_ms=one_hour_from_now_ms,
        )
        assert not tag.expired

    def test_expired_with_tag_lifetime_end_none(self):
        now_ms = get_epoch_timestamp_ms()
        one_hour_ago_ms = now_ms - 3600 * 1000
        tag = Tag(
            name="latest",
            reversion=False,
            manifest_digest="abc123",
            lifetime_start_ts=one_hour_ago_ms // 1000,
            lifetime_start_ms=one_hour_ago_ms,
            lifetime_end_ts=None,
            lifetime_end_ms=None,
        )
        assert not tag.expired
