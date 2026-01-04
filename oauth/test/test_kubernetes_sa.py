"""Tests for Kubernetes ServiceAccount OIDC authentication service."""

import pytest

from oauth.services.kubernetes_sa import (
    DEFAULT_SYSTEM_ORG_NAME,
    KUBERNETES_SA_SUBJECT_PATTERN,
    KubernetesServiceAccountLoginService,
)


class TestKubernetesServiceAccountLoginService:
    """Tests for KubernetesServiceAccountLoginService."""

    @pytest.fixture
    def kubernetes_config(self):
        """Basic Kubernetes SA auth configuration."""
        return {
            "FEATURE_KUBERNETES_SA_AUTH": True,
            "SERVER_HOSTNAME": "quay.example.com",
            "KUBERNETES_SA_AUTH_CONFIG": {
                "SERVICE_NAME": "Kubernetes",
                "VERIFY_TLS": False,
                "SYSTEM_ORG_NAME": "quay-system",
                "SUPERUSER_SUBJECT": "system:serviceaccount:quay-operator:quay-controller",
                "DEBUGGING": True,
            },
            "TESTING": True,
        }

    @pytest.fixture
    def kubernetes_service(self, kubernetes_config):
        """Create Kubernetes SA login service."""
        return KubernetesServiceAccountLoginService(kubernetes_config)

    def test_service_id(self, kubernetes_service):
        """Service ID should be 'kubernetes_sa'."""
        assert kubernetes_service.service_id() == "kubernetes_sa"

    def test_service_name(self, kubernetes_service):
        """Service name should be from config."""
        assert kubernetes_service.service_name() == "Kubernetes"

    def test_service_name_default(self):
        """Service name should default to 'Kubernetes'."""
        config = {
            "KUBERNETES_SA_AUTH_CONFIG": {},
            "TESTING": True,
        }
        service = KubernetesServiceAccountLoginService(config)
        assert service.service_name() == "Kubernetes"

    def test_system_org_name(self, kubernetes_service):
        """System org name should be from config."""
        assert kubernetes_service.system_org_name == "quay-system"

    def test_system_org_name_default(self):
        """System org name should default to 'quay-system'."""
        config = {
            "KUBERNETES_SA_AUTH_CONFIG": {},
            "TESTING": True,
        }
        service = KubernetesServiceAccountLoginService(config)
        assert service.system_org_name == DEFAULT_SYSTEM_ORG_NAME


class TestSASubjectParsing:
    """Tests for SA subject parsing."""

    @pytest.fixture
    def service(self):
        config = {
            "KUBERNETES_SA_AUTH_CONFIG": {},
            "TESTING": True,
        }
        return KubernetesServiceAccountLoginService(config)

    @pytest.mark.parametrize(
        "subject,expected",
        [
            ("system:serviceaccount:default:my-sa", ("default", "my-sa")),
            (
                "system:serviceaccount:quay-operator:controller",
                ("quay-operator", "controller"),
            ),
            (
                "system:serviceaccount:ns:name-with-dashes",
                ("ns", "name-with-dashes"),
            ),
            (
                "system:serviceaccount:kube-system:default",
                ("kube-system", "default"),
            ),
            (
                "system:serviceaccount:my-namespace:my-service-account",
                ("my-namespace", "my-service-account"),
            ),
        ],
    )
    def test_parse_valid_subjects(self, service, subject, expected):
        """Valid SA subjects should parse correctly."""
        result = service.parse_sa_subject(subject)
        assert result == expected

    @pytest.mark.parametrize(
        "subject",
        [
            "invalid",
            "system:serviceaccount",
            "system:serviceaccount:only-namespace",
            "user:someone",
            "",
            "system:node:my-node",
            "serviceaccount:default:my-sa",  # Missing system: prefix
        ],
    )
    def test_parse_invalid_subjects(self, service, subject):
        """Invalid SA subjects should return None."""
        result = service.parse_sa_subject(subject)
        assert result is None


class TestRobotNameGeneration:
    """Tests for robot name generation."""

    @pytest.fixture
    def service(self):
        config = {
            "KUBERNETES_SA_AUTH_CONFIG": {},
            "TESTING": True,
        }
        return KubernetesServiceAccountLoginService(config)

    @pytest.mark.parametrize(
        "namespace,sa_name,expected",
        [
            ("default", "my-sa", "kube_default_my_sa"),
            ("quay-operator", "controller-manager", "kube_quay_operator_controller_manager"),
            ("ns", "name.with.dots", "kube_ns_name_with_dots"),
            ("NS", "UPPERCASE", "kube_ns_uppercase"),
            ("kube-system", "default", "kube_kube_system_default"),
            ("my_namespace", "my_sa", "kube_my_namespace_my_sa"),
        ],
    )
    def test_generate_robot_shortname(self, service, namespace, sa_name, expected):
        """Robot shortnames should be generated correctly."""
        result = service.generate_robot_shortname(namespace, sa_name)
        assert result == expected

    def test_robot_shortname_deterministic(self, service):
        """Robot shortnames should be deterministic for same input."""
        result1 = service.generate_robot_shortname("quay", "operator")
        result2 = service.generate_robot_shortname("quay", "operator")
        assert result1 == result2


class TestSuperuserCheck:
    """Tests for superuser subject checking."""

    def test_is_superuser_subject_true(self):
        """Matching subject should return True."""
        config = {
            "KUBERNETES_SA_AUTH_CONFIG": {
                "SUPERUSER_SUBJECT": "system:serviceaccount:quay-operator:controller",
            },
            "TESTING": True,
        }
        service = KubernetesServiceAccountLoginService(config)
        assert service.is_superuser_subject("system:serviceaccount:quay-operator:controller")

    def test_is_superuser_subject_false(self):
        """Non-matching subject should return False."""
        config = {
            "KUBERNETES_SA_AUTH_CONFIG": {
                "SUPERUSER_SUBJECT": "system:serviceaccount:quay-operator:controller",
            },
            "TESTING": True,
        }
        service = KubernetesServiceAccountLoginService(config)
        assert not service.is_superuser_subject("system:serviceaccount:default:random-sa")

    def test_is_superuser_subject_no_config(self):
        """No superuser configured should always return False."""
        config = {
            "KUBERNETES_SA_AUTH_CONFIG": {},
            "TESTING": True,
        }
        service = KubernetesServiceAccountLoginService(config)
        assert not service.is_superuser_subject("system:serviceaccount:quay-operator:controller")


class TestSSLVerification:
    """Tests for SSL verification settings."""

    def test_verify_tls_false(self):
        """VERIFY_TLS=false should return False."""
        config = {
            "KUBERNETES_SA_AUTH_CONFIG": {
                "VERIFY_TLS": False,
            },
            "TESTING": True,
        }
        service = KubernetesServiceAccountLoginService(config)
        assert service.get_ssl_verification() is False

    def test_verify_tls_true_no_ca(self):
        """VERIFY_TLS=true without CA bundle should return True."""
        config = {
            "KUBERNETES_SA_AUTH_CONFIG": {
                "VERIFY_TLS": True,
                "CA_BUNDLE": "/nonexistent/path",
            },
            "TESTING": True,
        }
        service = KubernetesServiceAccountLoginService(config)
        assert service.get_ssl_verification() is True

    def test_verify_tls_default(self):
        """Default should be to verify TLS."""
        config = {
            "KUBERNETES_SA_AUTH_CONFIG": {},
            "TESTING": True,
        }
        service = KubernetesServiceAccountLoginService(config)
        # Will return True since default CA path doesn't exist in test environment
        result = service.get_ssl_verification()
        assert result is True or isinstance(result, str)


class TestSubjectPattern:
    """Tests for the SA subject regex pattern."""

    @pytest.mark.parametrize(
        "subject",
        [
            "system:serviceaccount:default:my-sa",
            "system:serviceaccount:kube-system:default",
            "system:serviceaccount:my-ns:my-sa-123",
        ],
    )
    def test_valid_pattern_matches(self, subject):
        """Valid SA subjects should match the pattern."""
        assert KUBERNETES_SA_SUBJECT_PATTERN.match(subject) is not None

    @pytest.mark.parametrize(
        "subject",
        [
            "system:node:my-node",
            "system:serviceaccount:only-namespace",
            "user:admin",
            "",
        ],
    )
    def test_invalid_pattern_no_match(self, subject):
        """Invalid SA subjects should not match the pattern."""
        assert KUBERNETES_SA_SUBJECT_PATTERN.match(subject) is None
