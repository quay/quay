from oauth.base import OAuthEndpoint
from oauth.login import OAuthLoginException
from oauth.oidc import OIDCLoginService
import features
import logging
import os
from _init import CONF_DIR

logger = logging.getLogger(__name__)


class RHSSOOAuthService(OIDCLoginService):
    def exchange_code_for_login(self, app_config, http_client, code, redirect_suffix):

        sub, lusername, email_address = super().exchange_code_for_login(
            app_config, http_client, code, redirect_suffix
        )

        # Conduct RedHat Export Compliance if enabled
        if features.EXPORT_COMPLIANCE:
            logger.debug("Attempting to hit export compliance service")
            try:
                result = http_client.post(
                    app_config.get("EXPORT_COMPLIANCE_ENDPOINT"),
                    cert=(
                        os.path.join(CONF_DIR, "export-compliance-client.crt"),
                        os.path.join(CONF_DIR, "export-compliance-client.key"),
                    ),
                    verify=os.path.join(CONF_DIR, "export-compliance-ca.crt"),
                    json={"user": {"login": lusername}, "account": {"primary": True}},
                    timeout=5,
                )
                logger.debug("Got result from export compliance service: " + result.json())
                if result.status_code != 200:
                    raise OAuthLoginException(str(result.json()["errors"]))
            except Exception as e:
                raise OAuthLoginException(str(e))

        return sub, lusername, email_address
