import logging
import os

import requests

import features
from _init import CONF_DIR
from oauth.base import OAuthEndpoint
from oauth.login import ExportComplianceException, OAuthLoginException
from oauth.oidc import OIDCLoginService

logger = logging.getLogger(__name__)


class RHSSOOAuthService(OIDCLoginService):
    def exchange_code_for_login(self, app_config, http_client, code, redirect_suffix):

        sub, lusername, email_address, additional_info = super().exchange_code_for_login(
            app_config, http_client, code, redirect_suffix
        )

        # Conduct RedHat Export Compliance if enabled
        if features.EXPORT_COMPLIANCE:
            logger.debug("Attempting to hit export compliance service")
            try:

                # subject is of the form `f:<uuid>:<sso-username>`
                sso_username = sub.split(":")[-1]

                result = requests.post(
                    app_config.get("EXPORT_COMPLIANCE_ENDPOINT"),
                    cert=(
                        "/conf/stack/export-compliance-client.crt",
                        "/conf/stack/export-compliance-client.key",
                    ),
                    json={"user": {"login": sso_username}, "account": {"primary": True}},
                    timeout=5,
                )
                logger.debug(
                    f"Got result from export compliance service: {result.json()} "
                    f"for sub: {sub}, lusername: {lusername}"
                )

                # 200 => Endpoint was hit successfully and user was found
                # 400 => Endpoint was hit successfully but no user was found
                if result.status_code == 200 and result.json().get("result", "") in [
                    "ERROR_EXPORT_CONTROL",
                    "DOMAIN_BLOCKING",
                    "ERROR_OFAC",
                    "EMBARGOED_COUNTRY_BLOCK",
                    "ERROR_T5",
                ]:
                    raise ExportComplianceException(sso_username, email_address, lusername)

            except ExportComplianceException as e:
                # Raise the export compliance exception as-is
                # to render the compliance error page
                raise e
            except Exception as e:
                # This generates a generic OAUTH error page
                # also any issues with reaching the export
                # compliance API should trigger this
                # Adding error log to capture the error on sentry without causing quay.io logins to fail
                msg = ""
                if result:
                    msg = f"Got unknown response from export compliance service: {result.text}, with status_code: {result.status_code}"

                logger.error(
                    f"{msg}"
                    f"for sub: {sub}, lusername: {lusername}"
                    f"Failing with exception as: {str(e)}",
                    extra={"stack": True},
                    exc_info=True,
                )

        return sub, lusername, email_address, additional_info
