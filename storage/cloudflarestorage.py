import base64
import logging
import urllib.parse
from datetime import datetime, timedelta
from functools import lru_cache

from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes, serialization
from cryptography.hazmat.primitives.asymmetric import padding

logger = logging.getLogger(__name__)

from storage.cloud import S3Storage, is_in_network_request


class CloudFlareS3Storage(S3Storage):
    """
    CloudFlare CDN backed by S3 storage
    """

    def __init__(
        self,
        context,
        cloudflare_domain,
        cloudflare_privatekey_filename,
        storage_path,
        s3_bucket,
        s3_region,
        *args,
        **kwargs,
    ):
        super(CloudFlareS3Storage, self).__init__(
            context, storage_path, s3_bucket, s3_region=s3_region, *args, **kwargs
        )

        self.context = context
        self.cloudflare_domain = cloudflare_domain
        self.cloudflare_privatekey = self._load_private_key(cloudflare_privatekey_filename)
        self.region = s3_region

    def get_direct_download_url(
        self, path, request_ip=None, expires_in=60, requires_cors=False, head=False, **kwargs
    ):
        # If CloudFlare could not be loaded, fall back to normal S3.
        s3_presigned_url = super(CloudFlareS3Storage, self).get_direct_download_url(
            path, request_ip, expires_in, requires_cors, head
        )
        logger.debug(f"s3 presigned_url: {s3_presigned_url}")
        if self.cloudflare_privatekey is None or request_ip is None:
            return s3_presigned_url

        if is_in_network_request(self._context, request_ip, self.region):
            if kwargs.get("cdn_specific", False):
                logger.debug(
                    "Request came from within network but namespace is protected: %s", path
                )
            else:
                logger.debug("Request is from within the network, returning S3 URL")
                return s3_presigned_url

        s3_url_parsed = urllib.parse.urlparse(s3_presigned_url)

        cf_url_parsed = s3_url_parsed._replace(netloc=self.cloudflare_domain)

        expire_date = datetime.now() + timedelta(seconds=expires_in)
        signed_url = self._cf_sign_url(cf_url_parsed, date_less_than=expire_date, **kwargs)
        logger.debug(
            'Returning CloudFlare URL for path "%s" with IP "%s": %s',
            path,
            request_ip,
            signed_url,
        )
        return signed_url

    def _cf_sign_url(self, cf_url_parsed, date_less_than, **kwargs):
        expiry_ts = date_less_than.timestamp()
        sign_data = "%s@%d" % (cf_url_parsed.path, expiry_ts)
        signature = self.cloudflare_privatekey.sign(
            sign_data.encode("utf8"), padding.PKCS1v15(), hashes.SHA256()
        )
        signature_b64 = base64.b64encode(signature)

        return self._build_signed_url(cf_url_parsed, signature_b64, date_less_than, **kwargs)

    def _build_signed_url(self, cf_url_parsed, signature, expiry_date, **kwargs):
        query = cf_url_parsed.query
        url_dict = dict(urllib.parse.parse_qsl(query))
        params = {
            "cf_sign": signature,
            "cf_expiry": "%d" % expiry_date.timestamp(),
            "region": self.region,
        }
        # Additional params for usage calculation. They are removed
        # from the URL before sending to S3 by the CloudFlare worker
        if kwargs.get("namespace"):
            params["namespace"] = kwargs.get("namespace")
        if kwargs.get("username"):
            params["username"] = kwargs.get("username")
        if kwargs.get("repo_name"):
            params["repo_name"] = kwargs.get("repo_name")

        url_dict.update(params)
        url_new_query = urllib.parse.urlencode(url_dict)
        url_parse = cf_url_parsed._replace(query=url_new_query)
        return urllib.parse.urlunparse(url_parse)

    @lru_cache(maxsize=1)
    def _load_private_key(self, cloudfront_privatekey_filename):
        """
        Returns the private key, loaded from the config provider, used to sign direct download URLs
        to CloudFront.
        """
        if self._context.config_provider is None:
            return None

        with self._context.config_provider.get_volume_file(
            cloudfront_privatekey_filename,
            mode="rb",
        ) as key_file:
            return serialization.load_pem_private_key(
                key_file.read(), password=None, backend=default_backend()
            )
