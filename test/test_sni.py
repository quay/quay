import ssl


def test_sni_support():
    assert ssl.HAS_SNI
