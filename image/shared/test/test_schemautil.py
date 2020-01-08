import pytest

from image.shared.schemautil import to_canonical_json


@pytest.mark.parametrize(
    "input, expected_output",
    [
        pytest.param({}, "{}", id="empty object"),
        pytest.param({"b": 2, "a": 1}, '{"a":1,"b":2}', id="object with sorted keys"),
        pytest.param("hello world", '"hello world"', id="basic string"),
        pytest.param("hey & hi", '"hey \\u0026 hi"', id="string with &"),
        pytest.param("<hey>", '"\\u003chey\\u003e"', id="string with brackets"),
        pytest.param(
            {"zxcv": [{}, True, 1000000000, "tyui"], "asdf": 1, "qwer": [],},
            '{"asdf":1,"qwer":[],"zxcv":[{},true,1000000000,"tyui"]}',
            id="example canonical",
        ),
    ],
)
def test_to_canonical_json(input, expected_output):
    result = to_canonical_json(input)
    assert result == expected_output

    # Ensure the result is utf-8.
    assert isinstance(result, str)
