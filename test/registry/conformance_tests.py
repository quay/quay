import subprocess
import os
import logging

from test.fixtures import *
from test.registry.liveserverfixture import *
from test.registry.fixtures import *
from test.registry.protocol_fixtures import *

CONFORMANCE_TEST_PATH = "dist-spec/conformance/conformance.test"

logger = logging.getLogger(__name__)


def test_run_conformance(liveserver_session, app_reloader, registry_server_executor, liveserver):
    server_url = liveserver_session.base_url
    env = os.environ.copy()
    env["OCI_ROOT_URL"] = server_url
    env["OCI_NAMESPACE"] = "devtable/oci"
    env["OCI_USERNAME"] = "devtable"
    env["OCI_PASSWORD"] = "password"
    env["OCI_DEBUG"] = "true"

    env["OCI_TEST_PUSH"] = "1"

    # TODO: support the content discovery once tags pagination is changed to support
    # the expected pagination parameter for next page.
    # env["OCI_TEST_CONTENT_DISCOVERY"] = "1"

    assert server_url.startswith("http://")

    server_hostname = server_url[len("http://") :]
    assert server_hostname

    logger.info("Running server at %s", server_hostname)

    with ConfigChange(
        "SERVER_HOSTNAME", server_hostname, registry_server_executor.on(liveserver), liveserver
    ):
        with FeatureFlagValue(
            "GENERAL_OCI_SUPPORT", True, registry_server_executor.on(liveserver),
        ):
            assert subprocess.call(CONFORMANCE_TEST_PATH, env=env) == 0
