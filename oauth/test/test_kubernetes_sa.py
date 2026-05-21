"""Tests for Kubernetes ServiceAccount OIDC authentication service."""

# isort: off
# Must import fixtures first to initialize app context before oauth imports
from test.fixtures import *  # noqa: F401,F403

# isort: on

import pytest

from oauth.services.kubernetes_sa import (
    DEFAULT_EXPECTED_AUDIENCE,
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
                "ALLOWED_SUBJECTS": ["system:serviceaccount:quay-operator:quay-controller"],
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


class TestAllowedSubjectCheck:
    """Tests for allowed subject checking."""

    def test_is_allowed_subject_true(self):
        """Matching subject should return True."""
        config = {
            "KUBERNETES_SA_AUTH_CONFIG": {
                "ALLOWED_SUBJECTS": ["system:serviceaccount:quay-operator:controller"],
            },
            "TESTING": True,
        }
        service = KubernetesServiceAccountLoginService(config)
        assert service.is_allowed_subject("system:serviceaccount:quay-operator:controller")

    def test_is_allowed_subject_multiple(self):
        """Any matching subject in list should return True."""
        config = {
            "KUBERNETES_SA_AUTH_CONFIG": {
                "ALLOWED_SUBJECTS": [
                    "system:serviceaccount:quay-operator:controller",
                    "system:serviceaccount:admin:superadmin",
                ],
            },
            "TESTING": True,
        }
        service = KubernetesServiceAccountLoginService(config)
        assert service.is_allowed_subject("system:serviceaccount:quay-operator:controller")
        assert service.is_allowed_subject("system:serviceaccount:admin:superadmin")
        assert not service.is_allowed_subject("system:serviceaccount:default:random")

    def test_is_allowed_subject_false(self):
        """Non-matching subject should return False."""
        config = {
            "KUBERNETES_SA_AUTH_CONFIG": {
                "ALLOWED_SUBJECTS": ["system:serviceaccount:quay-operator:controller"],
            },
            "TESTING": True,
        }
        service = KubernetesServiceAccountLoginService(config)
        assert not service.is_allowed_subject("system:serviceaccount:default:random-sa")

    def test_is_allowed_subject_no_config(self):
        """No allowed subjects configured should always return False."""
        config = {
            "KUBERNETES_SA_AUTH_CONFIG": {},
            "TESTING": True,
        }
        service = KubernetesServiceAccountLoginService(config)
        assert not service.is_allowed_subject("system:serviceaccount:quay-operator:controller")

    def test_allowed_subjects_property(self):
        """allowed_subjects property should return the configured list."""
        config = {
            "KUBERNETES_SA_AUTH_CONFIG": {
                "ALLOWED_SUBJECTS": [
                    "system:serviceaccount:ns1:sa1",
                    "system:serviceaccount:ns2:sa2",
                ],
            },
            "TESTING": True,
        }
        service = KubernetesServiceAccountLoginService(config)
        assert service.allowed_subjects == [
            "system:serviceaccount:ns1:sa1",
            "system:serviceaccount:ns2:sa2",
        ]


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


class TestExpectedAudience:
    """Tests for expected audience configuration."""

    def test_expected_audience_default(self):
        """Default expected audience should be 'quay'."""
        config = {
            "KUBERNETES_SA_AUTH_CONFIG": {},
            "TESTING": True,
        }
        service = KubernetesServiceAccountLoginService(config)
        assert service.expected_audience == DEFAULT_EXPECTED_AUDIENCE
        assert service.expected_audience == "quay"

    def test_expected_audience_custom(self):
        """Custom expected audience should be used when configured."""
        config = {
            "KUBERNETES_SA_AUTH_CONFIG": {
                "EXPECTED_AUDIENCE": "custom-quay-audience",
            },
            "TESTING": True,
        }
        service = KubernetesServiceAccountLoginService(config)
        assert service.expected_audience == "custom-quay-audience"

    def test_expected_audience_property(self):
        """expected_audience property should return configured value."""
        config = {
            "KUBERNETES_SA_AUTH_CONFIG": {
                "EXPECTED_AUDIENCE": "my-quay-instance",
            },
            "TESTING": True,
        }
        service = KubernetesServiceAccountLoginService(config)
        assert service.expected_audience == "my-quay-instance"


class TestOIDCServerConfig:
    """Tests for OIDC server configuration."""

    def test_oidc_server_default(self):
        """Default OIDC server should be kubernetes.default.svc."""
        config = {
            "KUBERNETES_SA_AUTH_CONFIG": {},
            "TESTING": True,
        }
        service = KubernetesServiceAccountLoginService(config)
        assert service.oidc_server == "https://kubernetes.default.svc"

    def test_oidc_server_custom(self):
        """Custom OIDC server should be used when configured."""
        config = {
            "KUBERNETES_SA_AUTH_CONFIG": {
                "OIDC_SERVER": "https://my-cluster.example.com",
            },
            "TESTING": True,
        }
        service = KubernetesServiceAccountLoginService(config)
        assert service.oidc_server == "https://my-cluster.example.com"
