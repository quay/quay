import logging
import urllib.parse

# ignoring the below type check as mypy fails with "missing library stubs or py.typed marker" error
from akamai.edgeauth import EdgeAuth, EdgeAuthError  # type: ignore

logger = logging.getLogger(__name__)

from storage.cloud import S3Storage

DEFAULT_SIGNED_URL_EXPIRY_SECONDS = 900  # 15 mins
TOKEN_QUERY_STRING = "akamai_signature"


class AkamaiS3Storage(S3Storage):
    """
    Akamai CDN backed by S3 storage
    """

    def __init__(
        self,
        context,
        akamai_domain,
        akamai_shared_secret,
        storage_path,
        s3_bucket,
        s3_region,
        *args,
        **kwargs,
    ):
        super(AkamaiS3Storage, self).__init__(
            context, storage_path, s3_bucket, s3_region=s3_region, *args, **kwargs
        )

        self.akamai_domain = akamai_domain
        self.akamai_shared_secret = akamai_shared_secret
        self.region = s3_region
        self.et = EdgeAuth(
            token_name=TOKEN_QUERY_STRING,
            key=self.akamai_shared_secret,
            window_seconds=DEFAULT_SIGNED_URL_EXPIRY_SECONDS,
            escape_early=True,
        )

    def get_direct_download_url(
        self, path, request_ip=None, expires_in=60, requires_cors=False, head=False, **kwargs
    ):
        # If CloudFront could not be loaded, fall back to normal S3.
        s3_presigned_url = super(AkamaiS3Storage, self).get_direct_download_url(
            path, request_ip, expires_in, requires_cors, head
        )
        s3_url_parsed = urllib.parse.urlparse(s3_presigned_url)

        # replace s3 location with Akamai domain
        akamai_url_parsed = s3_url_parsed._replace(netloc=self.akamai_domain)

        # add akamai signed token
        try:

            # add region to the query string
            akamai_url_parsed = akamai_url_parsed._replace(
                query=f"{akamai_url_parsed.query}&region={self.region}"
            )

            # add additional params to the query string for metrics
            additional_params = ["namespace", "username", "repo_name"]
            for param in additional_params:
                if param in kwargs and kwargs[param] is not None:
                    akamai_url_parsed = akamai_url_parsed._replace(
                        query=f"{akamai_url_parsed.query}&{param}={kwargs[param]}"
                    )

            to_sign = f"{akamai_url_parsed.path}"
            akamai_url_parsed = akamai_url_parsed._replace(
                query=f"{akamai_url_parsed.query}&{TOKEN_QUERY_STRING}={self.et.generate_url_token(to_sign)}"
            )

        except EdgeAuthError as e:
            logger.error(f"Failed to generate Akamai token: {e}")
            return s3_presigned_url

        logger.debug(
            'Returning Akamai URL for path "%s" with IP "%s": %s',
            path,
            request_ip,
            akamai_url_parsed,
        )
        return akamai_url_parsed.geturl()
