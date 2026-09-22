from unittest.mock import Mock, patch

from util.repomirror.skopeomirror import SkopeoMirror


def _address(ip):
    return [(2, 1, 6, "", (ip, 0))]


def test_proxy_is_revalidated_before_every_skopeo_process():
    skopeo = SkopeoMirror()
    process = Mock(returncode=0)
    proxy = {"https_proxy": "https://proxy.example.com:8443"}

    with patch("util.security.ssrf._getaddrinfo") as mock_dns:
        mock_dns.side_effect = [_address("93.184.216.34"), _address("10.0.0.1")]
        with patch("util.repomirror.skopeomirror.subprocess.Popen", return_value=process) as popen:
            result = skopeo.run_skopeo(["/usr/bin/skopeo", "list-tags"], proxy, 300)
            blocked = skopeo.run_skopeo(["/usr/bin/skopeo", "copy"], proxy, 300)

    assert result.success is True
    assert blocked.success is False
    assert blocked.stderr == "Mirror proxy location is not allowed"
    popen.assert_called_once()
    assert popen.call_args.kwargs["env"]["HTTPS_PROXY"].startswith("http://127.0.0.1:")
    assert proxy == {"https_proxy": "https://proxy.example.com:8443"}
    assert mock_dns.call_count == 2


def test_allowlisted_proxy_is_revalidated_before_skopeo_process():
    skopeo = SkopeoMirror(allowed_hosts=["10.0.0.0/8"])
    process = Mock(returncode=0)
    proxy = {"http_proxy": "http://10.0.0.1:8080"}

    with patch("util.repomirror.skopeomirror.subprocess.Popen", return_value=process) as popen:
        result = skopeo.run_skopeo(["/usr/bin/skopeo", "list-tags"], proxy, 300)

    assert result.success is True
    popen.assert_called_once()
    assert popen.call_args.kwargs["env"]["HTTP_PROXY"].startswith("http://127.0.0.1:")
