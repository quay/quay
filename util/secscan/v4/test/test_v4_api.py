import pytest

from util.secscan.v4.api import is_valid_response, Action, actions


good_index_report = {
    "manifest_hash": "sha256:b05ac1eeec8635442fa5d3e55d6ef4ad287b9c66055a552c2fd309c334563b0a",
    "state": "IndexError",
    "packages": {},
    "distributions": {},
    "repository": {},
    "environments": {},
    "success": False,
    "err": "failed to scan all layer contents: scanner: dpkg error: opening layer failed: claircore: Layer not fetched",
}
bad_index_report = {
    key: good_index_report[key] for key in good_index_report if key not in ["state"]
}
good_vuln_report = {
    "manifest_hash": "sha256:b05ac1eeec8635442fa5d3e55d6ef4ad287b9c66055a552c2fd309c334563b0a",
    "packages": {},
    "distributions": {},
    "environments": {},
    "vulnerabilities": {},
    "package_vulnerabilities": {},
}
bad_vuln_report = {
    key: good_vuln_report[key] for key in good_vuln_report if key not in ["vulnerabilities"]
}


@pytest.mark.parametrize(
    "action, resp, expected, exception",
    [
        (None, None, False, AttributeError),
        (actions["State"](), {}, False, None),
        (actions["State"](), {"state": "abc"}, True, None),
        (actions["Index"](None), {}, False, None),
        (actions["Index"](None), good_index_report, True, None),
        (actions["GetIndexReport"](good_index_report["manifest_hash"]), {}, False, None),
        (
            actions["GetIndexReport"](good_index_report["manifest_hash"]),
            bad_index_report,
            False,
            None,
        ),
        (
            actions["GetIndexReport"](good_index_report["manifest_hash"]),
            good_index_report,
            True,
            None,
        ),
        (actions["GetVulnerabilityReport"](good_vuln_report["manifest_hash"]), {}, False, None),
        (
            actions["GetVulnerabilityReport"](good_vuln_report["manifest_hash"]),
            bad_vuln_report,
            False,
            None,
        ),
        (
            actions["GetVulnerabilityReport"](good_vuln_report["manifest_hash"]),
            good_vuln_report,
            True,
            None,
        ),
    ],
)
def test_is_valid_response(action, resp, expected, exception):
    try:
        assert is_valid_response(action, resp) == expected
    except Exception as e:
        assert exception is not None and isinstance(e, exception)
