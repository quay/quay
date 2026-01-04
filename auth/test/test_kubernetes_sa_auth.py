"""Integration tests for Kubernetes SA authentication."""

from unittest.mock import MagicMock, patch

import pytest

from auth.oauth import validate_kubernetes_sa_token
from auth.validateresult import AuthKind


class TestValidateKubernetesSAToken:
    """Tests for validate_kubernetes_sa_token function."""

    def test_returns_none_when_feature_disabled(self, app):
        """Should return None when FEATURE_KUBERNETES_SA_AUTH is disabled."""
        with patch.dict(app.config, {"FEATURE_KUBERNETES_SA_AUTH": False}):
            result = validate_kubernetes_sa_token("some.jwt.token")
            assert result is None

    def test_returns_none_when_config_missing(self, app):
        """Should return None when KUBERNETES_SA_AUTH_CONFIG is missing."""
        with patch.dict(
            app.config,
            {"FEATURE_KUBERNETES_SA_AUTH": True, "KUBERNETES_SA_AUTH_CONFIG": None},
        ):
            result = validate_kubernetes_sa_token("some.jwt.token")
            assert result is None

    def test_returns_none_for_non_matching_issuer(self, app):
        """Should return None when token issuer doesn't match config."""
        # Create a minimal JWT-like token with a different issuer
        # The function checks issuer before full validation
        with patch.dict(
            app.config,
            {
                "FEATURE_KUBERNETES_SA_AUTH": True,
                "KUBERNETES_SA_AUTH_CONFIG": {},
            },
        ):
            with patch(
                "auth.oauth.get_jwt_issuer",
                return_value="https://some-other-issuer.com",
            ):
                result = validate_kubernetes_sa_token("some.jwt.token")
                assert result is None

    def test_returns_none_when_issuer_extraction_fails(self, app):
        """Should return None when issuer can't be extracted from token."""
        with patch.dict(
            app.config,
            {
                "FEATURE_KUBERNETES_SA_AUTH": True,
                "KUBERNETES_SA_AUTH_CONFIG": {},
            },
        ):
            with patch("auth.oauth.get_jwt_issuer", return_value=None):
                result = validate_kubernetes_sa_token("invalid.token")
                assert result is None

    def test_returns_error_for_invalid_token(self, app):
        """Should return error result for invalid token with matching issuer."""
        from util.security.jwtutil import InvalidTokenError

        with patch.dict(
            app.config,
            {
                "FEATURE_KUBERNETES_SA_AUTH": True,
                "KUBERNETES_SA_AUTH_CONFIG": {
                    "DEBUGGING": True,
                },
                "TESTING": True,
            },
        ):
            with patch(
                "auth.oauth.get_jwt_issuer",
                return_value="https://kubernetes.default.svc",
            ):
                # Mock service to raise InvalidTokenError
                mock_service = MagicMock()
                mock_service.validate_sa_token.side_effect = InvalidTokenError("Invalid signature")
                with patch(
                    "auth.oauth.KubernetesServiceAccountLoginService",
                    return_value=mock_service,
                ):
                    result = validate_kubernetes_sa_token("bad.jwt.token")
                    assert result is not None
                    assert result.kind == AuthKind.kubernetessa
                    assert result.error_message is not None
                    assert "Token validation failed" in result.error_message

    def test_returns_error_for_missing_subject(self, app):
        """Should return error when token lacks subject claim."""
        with patch.dict(
            app.config,
            {
                "FEATURE_KUBERNETES_SA_AUTH": True,
                "KUBERNETES_SA_AUTH_CONFIG": {
                    "DEBUGGING": True,
                },
                "TESTING": True,
            },
        ):
            with patch(
                "auth.oauth.get_jwt_issuer",
                return_value="https://kubernetes.default.svc",
            ):
                mock_service = MagicMock()
                mock_service.validate_sa_token.return_value = {"iss": "test"}  # No sub
                with patch(
                    "auth.oauth.KubernetesServiceAccountLoginService",
                    return_value=mock_service,
                ):
                    result = validate_kubernetes_sa_token("some.jwt.token")
                    assert result is not None
                    assert result.kind == AuthKind.kubernetessa
                    assert "subject" in result.error_message.lower()

    def test_returns_error_for_invalid_subject_format(self, app):
        """Should return error when subject format is invalid."""
        with patch.dict(
            app.config,
            {
                "FEATURE_KUBERNETES_SA_AUTH": True,
                "KUBERNETES_SA_AUTH_CONFIG": {
                    "DEBUGGING": True,
                },
                "TESTING": True,
            },
        ):
            with patch(
                "auth.oauth.get_jwt_issuer",
                return_value="https://kubernetes.default.svc",
            ):
                mock_service = MagicMock()
                mock_service.validate_sa_token.return_value = {"sub": "invalid:format"}
                mock_service.parse_sa_subject.return_value = None
                with patch(
                    "auth.oauth.KubernetesServiceAccountLoginService",
                    return_value=mock_service,
                ):
                    result = validate_kubernetes_sa_token("some.jwt.token")
                    assert result is not None
                    assert result.kind == AuthKind.kubernetessa
                    assert "Invalid ServiceAccount subject" in result.error_message


class TestValidateKubernetesSATokenWithFixtures:
    """Integration tests with database fixtures."""

    def test_returns_error_when_org_creation_fails(self, app):
        """Should return error when system organization creation fails."""
        from data import model

        with patch.dict(
            app.config,
            {
                "FEATURE_KUBERNETES_SA_AUTH": True,
                "KUBERNETES_SA_AUTH_CONFIG": {
                    "SYSTEM_ORG_NAME": "quay-system",
                    "DEBUGGING": True,
                },
                "TESTING": True,
            },
        ):
            with patch(
                "auth.oauth.get_jwt_issuer",
                return_value="https://kubernetes.default.svc",
            ):
                mock_service = MagicMock()
                mock_service.validate_sa_token.return_value = {
                    "sub": "system:serviceaccount:quay:operator"
                }
                mock_service.parse_sa_subject.return_value = ("quay", "operator")
                mock_service.generate_robot_shortname.return_value = "kube_quay_operator"
                mock_service.system_org_name = "quay-system"

                with patch(
                    "auth.oauth.KubernetesServiceAccountLoginService",
                    return_value=mock_service,
                ):
                    # Make sure robot lookup fails (triggering org lookup/creation)
                    with patch(
                        "data.model.user.lookup_robot",
                        side_effect=model.InvalidRobotException("Not found"),
                    ):
                        # Make sure org lookup fails
                        with patch(
                            "data.model.organization.get_organization",
                            side_effect=model.InvalidOrganizationException("Not found"),
                        ):
                            # Make sure org creation fails
                            with patch(
                                "auth.oauth._create_kubernetes_sa_system_org",
                                side_effect=Exception("Database error"),
                            ):
                                result = validate_kubernetes_sa_token("some.jwt.token")
                                assert result is not None
                                assert result.kind == AuthKind.kubernetessa
                                assert (
                                    "Failed to create system organization" in result.error_message
                                )
