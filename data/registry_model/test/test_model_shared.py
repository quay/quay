import pytest

from data.registry_model.shared import SyntheticIDHandler


@pytest.mark.parametrize("manifest_id", [1, 1000, 10000, 60000])
@pytest.mark.parametrize(
    "hash_salt",
    [
        None,
        "",
        "testing1234",
        "foobarbaz",
    ],
)
def test_handler(manifest_id, hash_salt):
    handler = SyntheticIDHandler(hash_salt)
    for index in range(0, 10):
        assert handler.decode(handler.encode(manifest_id, layer_index=index)) == (
            manifest_id,
            index,
        )


def test_invalid_value():
    handler = SyntheticIDHandler("somehash")
    assert handler.decode("invalidvalue") == ()
