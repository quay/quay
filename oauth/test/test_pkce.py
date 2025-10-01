# pylint: disable=missing-docstring

import base64
import hashlib
import re
import string

import pytest

from oauth.pkce import code_challenge, generate_code_verifier


class TestGenerateCodeVerifier:
    def test_generate_code_verifier_default_length(self):
        verifier = generate_code_verifier()
        assert len(verifier) == 64, f"Expected default verifier length 64, got {len(verifier)}"

    def test_generate_code_verifier_custom_length(self):
        for length in [43, 50, 64, 100, 128]:
            verifier = generate_code_verifier(length)
            assert (
                len(verifier) == length
            ), f"Expected verifier length {length}, got {len(verifier)}"

    def test_generate_code_verifier_invalid_length(self):
        with pytest.raises(
            ValueError, match="PKCE code_verifier length must be between 43 and 128"
        ):
            generate_code_verifier(42)

        with pytest.raises(
            ValueError, match="PKCE code_verifier length must be between 43 and 128"
        ):
            generate_code_verifier(129)

    def test_generate_code_verifier_character_set(self):
        unreserved_chars = string.ascii_letters + string.digits + "-._~"
        verifier = generate_code_verifier()

        # All characters should be from the unreserved set
        for char in verifier:
            assert (
                char in unreserved_chars
            ), f"Invalid character '{char}' in verifier (not in unreserved set)"

    def test_generate_code_verifier_randomness(self):
        # Generate multiple verifiers and ensure they're different
        verifiers = [generate_code_verifier() for _ in range(10)]
        # All verifiers should be unique
        assert (
            len(set(verifiers)) == 10
        ), f"Expected 10 unique verifiers, got {len(set(verifiers))} (insufficient randomness)"

    def test_generate_code_verifier_pattern(self):
        verifier = generate_code_verifier()
        # Should match the RFC 7636 unreserved character pattern
        pattern = r"^[A-Za-z0-9\-\._~]+$"
        assert re.match(
            pattern, verifier
        ), f"Verifier '{verifier}' does not match RFC 7636 unreserved pattern"


class TestCodeChallenge:
    def test_code_challenge_s256(self):
        # Test with known input/output for S256
        verifier = "dBjftJeZ4CVP-mB92K27uhbUJU1p1r_wW1gFWFOEjXk"
        expected = "E9Melhoa2OwvFrEMTJguCHaoeK1t8URWbuGJSstw-cM"

        challenge = code_challenge(verifier, "S256")
        assert (
            challenge == expected
        ), f"S256 challenge mismatch: expected '{expected}', got '{challenge}'"

    def test_code_challenge_s256_case_insensitive(self):
        verifier = "test_verifier"
        challenge_upper = code_challenge(verifier, "S256")
        challenge_lower = code_challenge(verifier, "s256")
        assert challenge_upper == challenge_lower, "S256 method should be case-insensitive"

    def test_code_challenge_plain(self):
        verifier = "plain_text_verifier"
        challenge = code_challenge(verifier, "plain")
        assert challenge == verifier, "Plain method should return verifier unchanged"

    def test_code_challenge_plain_case_insensitive(self):
        verifier = "plain_text_verifier"
        challenge_upper = code_challenge(verifier, "PLAIN")
        challenge_lower = code_challenge(verifier, "plain")
        assert challenge_upper == verifier, "PLAIN method should return verifier unchanged"
        assert challenge_lower == verifier, "plain method should return verifier unchanged"

    def test_code_challenge_invalid_method(self):
        verifier = "test_verifier"
        with pytest.raises(ValueError, match="Unsupported PKCE method: invalid"):
            code_challenge(verifier, "invalid")

    def test_code_challenge_s256_format(self):
        verifier = "test_verifier_123"
        challenge = code_challenge(verifier, "S256")

        # Should be base64url encoded (no padding)
        assert "=" not in challenge, f"S256 challenge should not contain padding: '{challenge}'"
        # Should contain only base64url characters
        pattern = r"^[A-Za-z0-9\-_]+$"
        assert re.match(
            pattern, challenge
        ), f"S256 challenge contains invalid base64url characters: '{challenge}'"

    def test_code_challenge_s256_deterministic(self):
        verifier = "same_verifier"
        challenge1 = code_challenge(verifier, "S256")
        challenge2 = code_challenge(verifier, "S256")
        assert (
            challenge1 == challenge2
        ), "S256 should produce deterministic output for same verifier"

    def test_code_challenge_different_verifiers_different_challenges(self):
        verifier1 = "verifier_one"
        verifier2 = "verifier_two"
        challenge1 = code_challenge(verifier1, "S256")
        challenge2 = code_challenge(verifier2, "S256")
        assert challenge1 != challenge2, "Different verifiers should produce different challenges"

    def test_code_challenge_edge_cases(self):
        # Test with minimum length verifier
        min_verifier = "a" * 43
        challenge = code_challenge(min_verifier, "S256")
        assert len(challenge) > 0, "S256 should produce non-empty challenge for min-length verifier"

        # Test with maximum length verifier
        max_verifier = "b" * 128
        challenge = code_challenge(max_verifier, "S256")
        assert len(challenge) > 0, "S256 should produce non-empty challenge for max-length verifier"

    def test_code_challenge_unicode_handling(self):
        # Should handle ASCII properly
        verifier = "test_with_special_chars-._~"
        challenge = code_challenge(verifier, "S256")
        assert len(challenge) > 0, "S256 should handle special unreserved characters"

    def test_code_challenge_s256_manual_verification(self):
        # Manually verify the S256 implementation
        verifier = "test_manual_verification"
        expected_digest = hashlib.sha256(verifier.encode("ascii")).digest()
        expected_challenge = base64.urlsafe_b64encode(expected_digest).rstrip(b"=").decode("ascii")

        actual_challenge = code_challenge(verifier, "S256")
        assert (
            actual_challenge == expected_challenge
        ), f"S256 implementation incorrect: expected '{expected_challenge}', got '{actual_challenge}'"
