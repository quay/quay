# -*- coding: utf-8 -*-

from itertools import islice

import pytest

from util.validation import is_json, validate_label_key, generate_valid_usernames, validate_username


@pytest.mark.parametrize(
    "username, is_valid",
    [
        ("ja", True),
        ("jak", True),
        ("jake", True),
        ("ja_ke", True),
        ("te-st", True),
        ("te.st", True),
        ("z" * 30, True),
        ("z" * 255, True),
        ("j", False),
        ("z" * 256, False),
        ("_test", False),
        ("Test", False),
        ("hello world", False),
        ("hello→world", False),
        ("te---st", False),
    ],
)
def test_validate_username(username, is_valid):
    valid, _ = validate_username(username)
    assert valid == is_valid


@pytest.mark.parametrize(
    "string_value,expected",
    [
        ("{}", True),
        ("[]", True),
        ("[hello world]", False),
        ("{hello world}", False),
        ("[test] this is a test", False),
        ("hello world", False),
        ('{"hi": "there"}', True),
        ("[1, 2, 3, 4]", True),
        ('[1, 2, {"num": 3}, 4]', True),
    ],
)
def test_is_json(string_value, expected):
    assert is_json(string_value) == expected


@pytest.mark.parametrize(
    "key, is_valid",
    [
        ("foo", True),
        ("bar", True),
        ("foo1", True),
        ("bar2", True),
        ("1", True),
        ("12", True),
        ("123", True),
        ("1234", True),
        ("git-sha", True),
        ("com.coreos.something", True),
        ("io.quay.git-sha", True),
        ("", False),
        ("git_sha", False),
        ("-125", False),
        ("-foo", False),
        ("foo-", False),
        ("123-", False),
        ("foo--bar", False),
        ("foo..bar", False),
    ],
)
def test_validate_label_key(key, is_valid):
    assert validate_label_key(key) == is_valid


@pytest.mark.parametrize(
    "input_username, expected_output",
    [
        ("jake", "jake"),
        ("frank", "frank"),
        ("fra-nk", "fra_nk"),
        ("Jake", "jake"),
        ("FranK", "frank"),
        ("ja__ke", "ja_ke"),
        ("ja___ke", "ja_ke"),
        ("ja__", "ja"),
        ("jake__", "jake"),
        ("_jake", "jake"),
        ("a", "a0"),
        ("ab", "ab"),
        ("abc", "abc"),
        ("abcdefghijklmnopqrstuvwxyz1234567890", "abcdefghijklmnopqrstuvwxyz1234567890"),
        ("c" * 256, "c" * 255),
        ("\xc6neid", "aeneid"),
        ("\xe9tude", "etude"),
        ("\u5317\u4eb0", "bei_jing"),
        ("\u1515\u14c7\u14c7", "shanana"),
        ("\u13d4\u13b5\u13c6", "taliqua"),
        ("\u0726\u071b\u073d\u0710\u073a", "ptu_i"),
        ("\u0905\u092d\u093f\u091c\u0940\u0924", "abhijiit"),
        ("\u0985\u09ad\u09bf\u099c\u09c0\u09a4", "abhijiit"),
        ("\u0d05\u0d2d\u0d3f\u0d1c\u0d40\u0d24", "abhijiit"),
        ("\u0d2e\u0d32\u0d2f\u0d3e\u0d32\u0d2e\u0d4d", "mlyaalm"),
        ("\ue000", "00"),
        ("\u03ff", "00"),
        ("\u0d2e\u0d32\u03ff\u03ff\u0d2e\u0d32", "ml_ml"),
        ("\u0d2e\u0d32\u0d2e\u0d32", "mlml"),
        (b"kenny", "kenny"),
        (b"c" * 256, "c" * 255),
        # \uXXXX are only interpreted in unicode strings
        (b"\u0d2e\u0d32\u0d2e\u0d32", "u0d2e_u0d32_u0d2e_u0d32"),
    ],
)
def test_generate_valid_usernames(input_username, expected_output):
    name_gen = generate_valid_usernames(input_username)
    generated_output = list(islice(name_gen, 1))[0]
    assert generated_output == expected_output


def test_multiple_suggestions():
    name_gen = generate_valid_usernames("a")
    generated_output = list(islice(name_gen, 4))
    assert generated_output[0] == "a0"
    assert generated_output[1] == "a1"
    assert generated_output[2] == "a2"
    assert generated_output[3] == "a3"
