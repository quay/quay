import json

import pytest

from app import config_provider
from storage import (
    AkamaiS3Storage,
    CloudFlareS3Storage,
    CloudFrontedS3Storage,
    MultiCDNStorage,
    StorageContext,
)
from storage.basestorage import InvalidStorageConfigurationException
from test.fixtures import *
from util.ipresolver import IPResolver

_TEST_CONFIG_JSON = """{
  "storage_config": {
    "s3_access_key": "test-access-key",
    "s3_secret_key": "test-secret-key",
    "s3_region": "us-east-1",
    "s3_bucket": "test-bucket",
    "storage_path": "/images"
  },
  "providers": {
    "CloudFlare": [
      "CloudFlareStorage",
      {
        "cloudflare_domain": "test-domain",
        "cloudflare_privatekey_filename": "test/data/test.pem"
      }
    ],
    "AWSCloudFront": [
      "CloudFrontedS3Storage",
      {
        "cloudfront_distribution_domain": "test-cloud",
        "cloudfront_key_id": "test-cloudfront-key",
        "cloudfront_privatekey_filename": "test/data/test.pem",
        "cloudfront_distribution_org_overrides": {}
      }
    ],
    "Akamai": [
      "AkamaiS3Storage",
      {
        "akamai_domain": "test-akamai",
        "akamai_shared_secret": "test-akamai-key"
      }
    ]
  },
  "default_provider": "AWSCloudFront",
  "rules": []
}"""


@pytest.fixture()
def context(app):
    return StorageContext("nyc", None, config_provider, IPResolver(app))


def test_should_pass_config_no_rules(context, app):
    test_config = json.loads(_TEST_CONFIG_JSON)

    engine = MultiCDNStorage(context, **test_config)

    assert len(engine.providers.keys()) == 3


def test_should_fail_config_no_storage_config(context, app):
    test_config = json.loads(_TEST_CONFIG_JSON)
    test_config["storage_config"] = {}

    with pytest.raises(InvalidStorageConfigurationException) as exc_info:
        engine = MultiCDNStorage(context, **test_config)

    assert "invalid storage_config" in str(exc_info.value)


def test_should_fail_config_no_default_provider(context, app):
    test_config = json.loads(_TEST_CONFIG_JSON)
    test_config["default_provider"] = None

    with pytest.raises(InvalidStorageConfigurationException) as exc_info:
        engine = MultiCDNStorage(context, **test_config)

    assert "default provider not provided" in str(exc_info.value)


def test_should_fail_no_providers(context, app):
    test_config = json.loads(_TEST_CONFIG_JSON)
    test_config["providers"] = []

    with pytest.raises(InvalidStorageConfigurationException) as exc_info:
        engine = MultiCDNStorage(context, **test_config)

    assert "providers should be a dict of storage providers with their configs" in str(
        exc_info.value
    )


def test_should_fail_bad_default_provider(context, app):
    test_config = json.loads(_TEST_CONFIG_JSON)
    test_config["default_provider"] = "BAD_PROVIDER"

    with pytest.raises(InvalidStorageConfigurationException) as exc_info:
        engine = MultiCDNStorage(context, **test_config)

    assert "Default provider not found in configured providers" in str(exc_info.value)


def test_should_pass_namespace_rule(context, app):
    test_config = json.loads(_TEST_CONFIG_JSON)
    test_config["rules"] = [{"namespace": "test", "target": "AWSCloudFront"}]

    MultiCDNStorage(context, **test_config)


def test_should_fail_bad_target_in_rule(context, app):
    test_config = json.loads(_TEST_CONFIG_JSON)
    test_config["rules"] = [{"namespace": "test", "target": "bad-provider"}]

    with pytest.raises(InvalidStorageConfigurationException) as exc_info:
        engine = MultiCDNStorage(context, **test_config)

    assert "not in the configured targets" in str(exc_info.value)


@pytest.mark.parametrize(
    "rule, namespace, ip, host, expected",
    [
        pytest.param(
            {"continent": "NA", "target": "CloudFlare"},
            "test",
            "8.8.8.8",
            None,
            CloudFlareS3Storage,
        ),
        pytest.param(
            {"namespace": "test", "target": "CloudFlare"},
            "test",
            "8.8.8.8",
            "quay.io",
            CloudFlareS3Storage,
        ),
        pytest.param(
            {"namespace": "test", "host": "quay.io", "target": "CloudFlare"},
            "test",
            "8.8.8.8",
            "quay.io",
            CloudFlareS3Storage,
        ),
        pytest.param(
            {"continent": "AF", "namespace": "test", "target": "CloudFlare"},
            "test",
            "8.8.8.8",
            None,
            CloudFrontedS3Storage,
        ),  # no rule match
        pytest.param(
            {"continent": "NA", "target": "Akamai"},
            "test",
            "8.8.8.8",
            None,
            AkamaiS3Storage,
        ),
        pytest.param(
            {"namespace": "test", "target": "Akamai"},
            "test",
            "8.8.8.8",
            "quay.io",
            AkamaiS3Storage,
        ),
        pytest.param(
            {"namespace": "test", "host": "quay.io", "target": "Akamai"},
            "test",
            "8.8.8.8",
            "quay.io",
            AkamaiS3Storage,
        ),
        pytest.param(
            {"continent": "AF", "namespace": "test", "target": "Akamai"},
            "test",
            "8.8.8.8",
            None,
            CloudFrontedS3Storage,
        ),  # no rule match
    ],
)
def test_rule_match(rule, namespace, ip, host, expected):
    test_config = json.loads(_TEST_CONFIG_JSON)
    test_config["rules"] = [rule]

    context = StorageContext("nyc", None, config_provider, IPResolver(app))

    engine = MultiCDNStorage(context, **test_config)

    provider = engine.find_matching_provider(namespace, ip, host)
    assert isinstance(provider, expected)
