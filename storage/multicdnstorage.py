import logging
from typing import Dict

from storage.cloudflarestorage import CloudFlareS3Storage
from storage.cloud import CloudFrontedS3Storage
from storage.basestorage import BaseStorageV2, InvalidStorageConfigurationException
from util.ipresolver import GEOIP_CONTINENT_CODES

logger = logging.getLogger(__name__)

from storage.storagecontext import StorageContext

VALID_RULE_KEYS = ["namespace", "continent", "target"]

MULTICDN_STORAGE_PROVIDER_CLASSES = {
    "CloudFrontedS3Storage": CloudFrontedS3Storage,
    "CloudFlareStorage": CloudFlareS3Storage,
}


class MultiCDNStorage(BaseStorageV2):
    """
    Implements a Pseudo storage provider which supports
    multiple CDN based storage providers under it.

    Based on rules defined in the config, this provider
    can select the correct CDN to serve the request

    Currently supported sub providers:
        - CloudFrontedS3Storage
        - CloudFlareS3Storage

    Currently supported rules:
        - namespace (could be an org or a user)
        - continent (Source IP continent. Possible values based on GeoIP Database continent codes)

    Example Config:
        - MultiCDNStorage
        - providers:
            TargetName1:
                - ProviderName1
                - porviderConfig1
            Targetname2:
                - ProviderName2
                - ProviderConfig2
          default_provider: TargetName1
          rules:
          - namespace: test
            continent: APAC
            target: TargetName2

    Rules are evaluated in the order they are defined. For a match, all fields of the rule have to match
    exactly. Partial matches are not supported. Once a rule is matched, we short-circuit the matching process
    and use the provider in the matched rule
    """

    def __init__(self, context, providers: dict, default_provider: str, rules: list):
        super().__init__()

        self.context: StorageContext = context
        self._validate_config(providers, default_provider, rules)
        self.providers = self._init_providers(providers)
        self.default_provider = self.providers.get(default_provider)
        self.rules = rules

    def _validate_config(self, providers, default_provider, rules):
        # validate providers config
        if not providers or not isinstance(providers, dict) or len(providers.keys()) == 0:
            raise InvalidStorageConfigurationException(
                "providers should be a dict of storage providers with their configs"
            )

        # default target must always exist and should be valid
        if not default_provider:
            raise InvalidStorageConfigurationException("default provider not provided")

        if default_provider not in providers.keys():
            raise InvalidStorageConfigurationException(
                "Default provider not found in configured providers"
            )

        for provider_target in providers:
            config = providers.get(provider_target)
            if len(config) != 2:
                raise InvalidStorageConfigurationException(
                    f"Provider {provider_target} invalid. Should contain provider name and config as list"
                )

        # Validate rules
        for rule in rules:
            rule_config_keys = rule.keys()
            for config_key in rule_config_keys:
                if config_key not in VALID_RULE_KEYS:
                    raise InvalidStorageConfigurationException(
                        f"{rule} Invalid: {config_key} bad rule key. Should be one of {VALID_RULE_KEYS}"
                    )

            if not rule.get("target"):
                raise InvalidStorageConfigurationException(
                    f"target not configured for rule {rule}: Add one of the provders as target in the config"
                )

            if rule["target"] not in providers.keys():
                raise InvalidStorageConfigurationException(
                    f'{rule} Invalid: {rule["target"]} not in the configured targets {providers.keys()}'
                )

            if rule.get("continent") and rule["continent"] not in GEOIP_CONTINENT_CODES:
                raise InvalidStorageConfigurationException(
                    f'{rule} Invalid: {rule["continent"]} not a valid continent. Should be on of {GEOIP_CONTINENT_CODES}'
                )

    def _init_providers(self, providers_config):
        providers = {}
        for target_name in providers_config:
            [provider_name, provider_config] = providers_config.get(target_name)
            provider_class = MULTICDN_STORAGE_PROVIDER_CLASSES[provider_name]
            providers[target_name] = provider_class(self.context, **provider_config)

        return providers

    def match_rule(self, rule, continent=None, namespace=None):
        if rule.get("namespace") and namespace != rule.get("namespace"):
            return False

        if rule.get("continent") and continent != rule.get("continent"):
            return False

        return True

    def find_matching_provider(self, namespace, request_ip):
        resolved_ip = self.context.ip_resolver.resolve_ip(request_ip)
        continent = resolved_ip.continent if resolved_ip and resolved_ip.continent else None

        provider = None
        for rule in self.rules:
            if self.match_rule(rule, continent, namespace):
                target_name = rule.get("target")
                provider = self.providers.get(target_name)
                break

        if not provider:
            provider = self.default_provider

        return provider

    def get_direct_download_url(
        self, path, request_ip=None, expires_in=60, requires_cors=False, head=False, **kwargs
    ):
        namespace = kwargs.get("namespace", None)
        provider = self.find_matching_provider(namespace, request_ip)
        return provider.get_direct_download_url(
            path, request_ip, expires_in, requires_cors, head, **kwargs
        )

    def initiate_chunked_upload(self):
        return self.default_provider.initiate_chunked_upload()

    def stream_upload_chunk(self, uuid, offset, length, in_fp, storage_metadata, content_type=None):
        return self.default_provider.stream_upload_chunk(
            uuid, offset, length, in_fp, storage_metadata, content_type
        )

    def complete_chunked_upload(self, uuid, final_path, storage_metadata):
        return self.default_provider.complete_chunked_upload(uuid, final_path, storage_metadata)

    def cancel_chunked_upload(self, uuid, storage_metadata):
        return self.default_provider.cancel_chunked_upload(uuid, storage_metadata)

    def get_content(self, path):
        """
        Used internally to get the manifest from storage
        """
        return self.default_provider.get_content(path)

    def put_content(self, path, content):
        return self.default_provider.put_content(path, content)

    def stream_read(self, path):
        return self.default_provider.stream_read(path)

    def stream_read_file(self, path):
        return self.default_provider.stream_read_file(path)

    def stream_write(self, path, fp, content_type=None, content_encoding=None):
        return self.default_provider.stream_write(path, fp, content_type, content_encoding)

    def exists(self, path):
        return self.default_provider.exists(path)

    def remove(self, path):
        return self.default_provider.remove(path)

    def get_checksum(self, path):
        return self.default_provider.get_checksum(path)

    def clean_partial_uploads(self, deletion_date_threshold):
        return self.default_provider.clean_partial_uploads(deletion_date_threshold)

    def copy_to(self, destination, path):
        self.default_provider.copy_to(destination, path)
