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
        (actions["IndexState"](), {}, False, None),
        (actions["IndexState"](), {"state": "abc"}, True, None),
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
        (
            actions["GetNotification"]("5e4b387e-88d3-4364-86fd-063447a6fad2", None),
            None,
            False,
            None,
        ),
        (
            actions["GetNotification"]("5e4b387e-88d3-4364-86fd-063447a6fad2", None),
            {"page": {}, "notifications": []},
            True,
            None,
        ),
        (actions["DeleteNotification"]("5e4b387e-88d3-4364-86fd-063447a6fad2"), None, True, None,),
    ],
)
def test_is_valid_response(action, resp, expected, exception):
    class TestResponse(object):
        def json(self):
            return resp

    try:
        result = is_valid_response(action, TestResponse())
        assert result == expected
    except Exception as e:
        assert exception is not None and isinstance(e, exception)
