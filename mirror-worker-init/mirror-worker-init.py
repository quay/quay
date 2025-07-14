import logging
import os
import sys
from time import sleep

import requests

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
handler = logging.StreamHandler()
logger.addHandler(handler)
handler.setFormatter(formatter)


def main():
    host = str(os.getenv("QUAY_APP_SERVICE_HOST"))
    http_proxy = os.getenv("HTTP_PROXY" or "http_proxy") or None
    https_proxy = os.getenv("HTTPS_PROXY" or "https_proxy") or None
    no_proxy = os.getenv("NO_PROXY" or "no_proxy") or None

    logger.info(
        "Init container initialized: Quay host %s, HTTP proxy: %s, HTTPS_PROXY: %s, NO_PROXY: %s",
        host,
        http_proxy,
        https_proxy,
        no_proxy,
    )
    logger.info("Waiting for Quay availability...")
    while True:
        try:
            if (
                requests.get("http://" + host, verify=False, allow_redirects=False).status_code
                == 200
            ):
                logger.info("Quay endpoint healthy, continuing bootstrap of mirror workers.")
                sys.exit(0)
            else:
                logger.error("Endpoint %s unavailable, sleeping for 5 seconds.", host)
                sleep(5)
        except requests.exceptions.ConnectionError as e:
            logger.error("Connection failed: %s", e)
            logger.info("Max connection retries reached, sleeping for 5 seconds.")
            sleep(5)


if __name__ == "__main__":
    main()
