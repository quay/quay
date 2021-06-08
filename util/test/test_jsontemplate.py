import pytest

from util.jsontemplate import JSONTemplate, JSONTemplateParseException


@pytest.mark.parametrize(
    "template_string, data, expected",
    [
        ("{}", {}, {}),
        ('{"hello": "world"}', {}, {"hello": "world"}),
        pytest.param(
            '{"hello": "${thing}"}', {"thing": 1234}, {"hello": 1234}, id="direct expression"
        ),
        pytest.param(
            '{"hello": "cool-${thing}"}',
            {"thing": "beans"},
            {"hello": "cool-beans"},
            id="inline expression",
        ),
        pytest.param(
            '{"hello": "${first.second.third}"}',
            {"first": {"second": {"third": 42}}},
            {"hello": 42},
            id="nested object",
        ),
        pytest.param(
            '{"hello": "${first.second.third} is the answer"}',
            {"first": {"second": {"third": 42}}},
            {"hello": "42 is the answer"},
            id="nested object with inline expression",
        ),
        pytest.param(
            '{"hello": "${first.doesnotexist.third}"}',
            {"first": {"second": {"third": 42}}},
            {"hello": None},
            id="inline expression with unknown child",
        ),
        pytest.param(
            '{"hello": "${first[2]}"}', {"first": [1, 2, 42]}, {"hello": 42}, id="array access"
        ),
        pytest.param(
            '{"hello": "${first[2]}"}',
            {"first": [1, 2]},
            {"hello": None},
            id="outside of array index",
        ),
        pytest.param(
            '{"hello": ["${first[1]}", "${first[0]}"]}',
            {"first": [1, 2]},
            {"hello": [2, 1]},
            id="array to list",
        ),
        pytest.param(
            '{"hello": "hey-${first[2]}"}',
            {"first": [1, 2]},
            {"hello": "hey-(none)"},
            id="outside of array index inline expression",
        ),
        pytest.param(
            '{"hello": "${tags[*]}"}',
            {"tags": ["latest", "prod", "foo"]},
            {"hello": ["latest", "prod", "foo"]},
            id="match multiples inline",
        ),
        pytest.param(
            '{"hello": "tags: ${tags[*]}"}',
            {"tags": ["latest", "prod", "foo"]},
            {"hello": "tags: latest,prod,foo"},
            id="match multiples with inline expression",
        ),
        pytest.param('{"hello": "}', {}, JSONTemplateParseException, id="invalid template"),
        pytest.param('{"hello": "${}"}', {}, JSONTemplateParseException, id="empty expression"),
        pytest.param('{"hello": "${;;}"}', {}, JSONTemplateParseException, id="invalid expression"),
        pytest.param(
            '{"hello": "${first[}"}',
            {},
            JSONTemplateParseException,
            id="another invalid expression",
        ),
    ],
)
def test_json_template(template_string, data, expected):
    if expected == JSONTemplateParseException:
        with pytest.raises(JSONTemplateParseException):
            JSONTemplate(template_string)
    else:
        jt = JSONTemplate(template_string)
        assert jt.apply(data) == expected
