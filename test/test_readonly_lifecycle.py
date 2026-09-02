"""
Tests for PROJQUAY-6259: operator-managed read-only lifecycle hooks.

Covers:
- Config flag (INSTANCE_SERVICE_KEY_IMPORT_FROM_FILES)
- Keyserver GET service filtering fix
- Keyserver /status endpoint
- boot.py readonly DB-write guards
- boot.py file-based service key import
- boot.py readonly verification hardening
- manage_servicekey.py cleanup CLI
- Cross-language thumbprint fixture
"""

import json
import os
import tempfile
from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pytest
from authlib.jose import JsonWebKey
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa
from test.fixtures import *

from data.database import ServiceKey, ServiceKeyApprovalType
from data.model import ServiceKeyDoesNotExist
from data.model.service_keys import (
    approve_service_key,
    create_service_key,
    get_service_key,
    get_service_key_for_status,
)
from tools.manage_servicekey import expire_key
from util.config.schema import INTERNAL_ONLY_PROPERTIES


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _generate_test_rsa_key():
    """Generate an RSA 2048 key pair and return (private_key, kid, public_jwk)."""
    private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    pem_bytes = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption(),
    )
    jwk_obj = JsonWebKey.import_key(pem_bytes)
    public_jwk = jwk_obj.as_dict()
    kid = public_jwk["kid"]
    return private_key, kid, public_jwk


def _write_key_files(tmpdir, private_key, kid):
    """Write .kid and .pem files to tmpdir, return (kid_path, pem_path)."""
    kid_path = os.path.join(tmpdir, "quay-readonly.kid")
    pem_path = os.path.join(tmpdir, "quay-readonly.pem")

    with open(kid_path, "w") as f:
        f.write(kid)

    pem_bytes = private_key.private_bytes(
        encoding=serialization.Encoding.PEM,
        format=serialization.PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=serialization.NoEncryption(),
    )
    with open(pem_path, "wb") as f:
        f.write(pem_bytes)

    return kid_path, pem_path


def _create_operator_key(kid, public_jwk, service="quay", approved=True, expired=False):
    """Create a service key in the DB with operator metadata."""
    exp = datetime.utcnow() + timedelta(hours=1)
    if expired:
        exp = datetime.utcnow() - timedelta(hours=1)

    key = create_service_key(
        "operator-managed-readonly",
        kid,
        service,
        public_jwk,
        {"created_by": "quay-operator-readonly"},
        exp,
    )

    if approved:
        approve_service_key(kid, ServiceKeyApprovalType.AUTOMATIC)

    return key


# ---------------------------------------------------------------------------
# Task 1: Config flag
# ---------------------------------------------------------------------------


class TestConfigFlag:
    def test_import_flag_in_internal_only_properties(self):
        assert "INSTANCE_SERVICE_KEY_IMPORT_FROM_FILES" in INTERNAL_ONLY_PROPERTIES

    def test_import_flag_default_is_false(self, app):
        assert app.config.get("INSTANCE_SERVICE_KEY_IMPORT_FROM_FILES") is False


# ---------------------------------------------------------------------------
# Task 2: Keyserver GET service filtering
# ---------------------------------------------------------------------------


class TestKeyserverGetServiceFilter:
    def test_get_key_wrong_service_returns_404(self, app, initialized_db):
        private_key, kid, public_jwk = _generate_test_rsa_key()
        _create_operator_key(kid, public_jwk, service="quay")

        client = app.test_client()
        rv = client.get("/keys/services/wrong-service/keys/%s" % kid)
        assert rv.status_code == 404

    def test_get_key_correct_service_returns_200(self, app, initialized_db):
        private_key, kid, public_jwk = _generate_test_rsa_key()
        _create_operator_key(kid, public_jwk, service="quay")

        client = app.test_client()
        rv = client.get("/keys/services/quay/keys/%s" % kid)
        assert rv.status_code == 200
        data = rv.get_json()
        assert data["kty"] == "RSA"


# ---------------------------------------------------------------------------
# Task 3: Keyserver /status endpoint
# ---------------------------------------------------------------------------


class TestKeyserverStatus:
    def test_status_unknown_kid_returns_404(self, app, initialized_db):
        client = app.test_client()
        rv = client.get("/keys/services/quay/keys/nonexistent-kid/status")
        assert rv.status_code == 404

    def test_status_wrong_service_returns_404(self, app, initialized_db):
        private_key, kid, public_jwk = _generate_test_rsa_key()
        _create_operator_key(kid, public_jwk, service="quay")

        client = app.test_client()
        rv = client.get("/keys/services/other/keys/%s/status" % kid)
        assert rv.status_code == 404

    def test_status_returns_correct_fields(self, app, initialized_db):
        private_key, kid, public_jwk = _generate_test_rsa_key()
        _create_operator_key(kid, public_jwk, service="quay")

        client = app.test_client()
        rv = client.get("/keys/services/quay/keys/%s/status" % kid)
        assert rv.status_code == 200
        data = rv.get_json()
        assert data["kid"] == kid
        assert data["service"] == "quay"
        assert data["operator_managed"] is True
        assert data["expiration_date"] is not None
        assert data["expiration_date"].endswith("Z")
        assert set(data.keys()) == {"kid", "service", "operator_managed", "expiration_date"}

    def test_status_non_operator_key(self, app, initialized_db):
        private_key, kid, public_jwk = _generate_test_rsa_key()
        create_service_key("test-key", kid, "quay", public_jwk, {}, None)

        client = app.test_client()
        rv = client.get("/keys/services/quay/keys/%s/status" % kid)
        assert rv.status_code == 200
        data = rv.get_json()
        assert data["operator_managed"] is False
        assert data["expiration_date"] is None

    def test_status_returns_200_for_expired_key(self, app, initialized_db):
        private_key, kid, public_jwk = _generate_test_rsa_key()
        _create_operator_key(kid, public_jwk, service="quay", expired=True)

        client = app.test_client()
        # Raw GET returns 403 for expired
        rv_get = client.get("/keys/services/quay/keys/%s" % kid)
        assert rv_get.status_code == 403

        # /status returns 200
        rv_status = client.get("/keys/services/quay/keys/%s/status" % kid)
        assert rv_status.status_code == 200
        data = rv_status.get_json()
        assert data["operator_managed"] is True

    def test_status_returns_200_for_unapproved_key(self, app, initialized_db):
        private_key, kid, public_jwk = _generate_test_rsa_key()
        _create_operator_key(kid, public_jwk, service="quay", approved=False)

        client = app.test_client()
        # Raw GET returns 409 for unapproved
        rv_get = client.get("/keys/services/quay/keys/%s" % kid)
        assert rv_get.status_code == 409

        # /status returns 200
        rv_status = client.get("/keys/services/quay/keys/%s/status" % kid)
        assert rv_status.status_code == 200


# ---------------------------------------------------------------------------
# Task 3 (model layer): get_service_key_for_status
# ---------------------------------------------------------------------------


class TestGetServiceKeyForStatus:
    def test_bypasses_stale_expired_filtering(self, initialized_db):
        private_key, kid, public_jwk = _generate_test_rsa_key()
        _create_operator_key(kid, public_jwk, expired=True)

        # Direct lookup should still find the key
        key = get_service_key_for_status(kid, "quay")
        assert key.kid == kid

    def test_filters_by_service(self, initialized_db):
        private_key, kid, public_jwk = _generate_test_rsa_key()
        _create_operator_key(kid, public_jwk, service="quay")

        with pytest.raises(ServiceKeyDoesNotExist):
            get_service_key_for_status(kid, "other-service")

    def test_raises_for_missing_key(self, initialized_db):
        with pytest.raises(ServiceKeyDoesNotExist):
            get_service_key_for_status("nonexistent", "quay")


# ---------------------------------------------------------------------------
# Task 4: boot.py readonly DB-write guards
# ---------------------------------------------------------------------------


class TestReadonlyDbWriteGuards:
    def test_readonly_skips_sync_and_release(self, app, initialized_db):
        with patch("boot.sync_database_with_config") as mock_sync, patch(
            "boot.set_region_release"
        ) as mock_release, patch("boot.setup_instance_service_key"), patch(
            "boot.setup_bootstrap_token"
        ), patch(
            "boot.release"
        ) as mock_rel_module:
            mock_rel_module.REGION = "us-east"
            mock_rel_module.GIT_HEAD = "abc123"
            mock_rel_module.SERVICE = "quay"
            app.config["REGISTRY_STATE"] = "readonly"
            app.config["SETUP_COMPLETE"] = True

            try:
                from boot import main

                main()
            except Exception:
                pass
            finally:
                app.config["REGISTRY_STATE"] = "normal"

            mock_sync.assert_not_called()
            mock_release.assert_not_called()

    def test_normal_calls_sync_and_release(self, app, initialized_db):
        with patch("boot.sync_database_with_config") as mock_sync, patch(
            "boot.set_region_release"
        ) as mock_release, patch("boot.setup_instance_service_key"), patch(
            "boot.setup_bootstrap_token"
        ), patch(
            "boot.release"
        ) as mock_rel_module:
            mock_rel_module.REGION = "us-east"
            mock_rel_module.GIT_HEAD = "abc123"
            mock_rel_module.SERVICE = "quay"
            app.config["REGISTRY_STATE"] = "normal"
            app.config["SETUP_COMPLETE"] = True

            from boot import main

            main()

            mock_sync.assert_called_once()
            mock_release.assert_called_once()


# ---------------------------------------------------------------------------
# Task 5: File-based service key import
# ---------------------------------------------------------------------------


class TestFileBasedImport:
    def test_import_creates_new_key(self, app, initialized_db):
        private_key, kid, public_jwk = _generate_test_rsa_key()

        with tempfile.TemporaryDirectory() as tmpdir:
            kid_path, pem_path = _write_key_files(tmpdir, private_key, kid)
            app.config["INSTANCE_SERVICE_KEY_KID_LOCATION"] = kid_path
            app.config["INSTANCE_SERVICE_KEY_LOCATION"] = pem_path
            app.config["INSTANCE_SERVICE_KEY_IMPORT_FROM_FILES"] = True

            from boot import _import_service_key_from_files

            result_kid = _import_service_key_from_files()

            assert result_kid == kid
            db_key = ServiceKey.select().where(ServiceKey.kid == kid).get()
            assert db_key.metadata.get("created_by") == "quay-operator-readonly"
            assert db_key.approval is not None

    def test_import_refreshes_existing_key(self, app, initialized_db):
        private_key, kid, public_jwk = _generate_test_rsa_key()
        _create_operator_key(kid, public_jwk)

        old_exp = ServiceKey.select().where(ServiceKey.kid == kid).get().expiration_date

        with tempfile.TemporaryDirectory() as tmpdir:
            kid_path, pem_path = _write_key_files(tmpdir, private_key, kid)
            app.config["INSTANCE_SERVICE_KEY_KID_LOCATION"] = kid_path
            app.config["INSTANCE_SERVICE_KEY_LOCATION"] = pem_path

            from boot import _import_service_key_from_files

            _import_service_key_from_files()

            new_exp = ServiceKey.select().where(ServiceKey.kid == kid).get().expiration_date
            assert new_exp > old_exp

    def test_import_rejects_wrong_service(self, app, initialized_db):
        private_key, kid, public_jwk = _generate_test_rsa_key()
        _create_operator_key(kid, public_jwk, service="other")

        with tempfile.TemporaryDirectory() as tmpdir:
            kid_path, pem_path = _write_key_files(tmpdir, private_key, kid)
            app.config["INSTANCE_SERVICE_KEY_KID_LOCATION"] = kid_path
            app.config["INSTANCE_SERVICE_KEY_LOCATION"] = pem_path

            from boot import _import_service_key_from_files

            with pytest.raises(Exception, match="belongs to service 'other'"):
                _import_service_key_from_files()

    def test_import_rejects_mismatched_jwk(self, app, initialized_db):
        private_key, kid, public_jwk = _generate_test_rsa_key()
        # Create a key in DB with a different JWK but same kid (impossible in normal flow,
        # but we test the validation)
        other_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        other_jwk = JsonWebKey.import_key(other_key).as_dict()
        other_jwk["kid"] = kid  # force same kid

        create_service_key(
            "test", kid, "quay", other_jwk, {"created_by": "quay-operator-readonly"}, None
        )
        approve_service_key(kid, ServiceKeyApprovalType.AUTOMATIC)

        with tempfile.TemporaryDirectory() as tmpdir:
            kid_path, pem_path = _write_key_files(tmpdir, private_key, kid)
            app.config["INSTANCE_SERVICE_KEY_KID_LOCATION"] = kid_path
            app.config["INSTANCE_SERVICE_KEY_LOCATION"] = pem_path

            from boot import _import_service_key_from_files

            with pytest.raises(Exception, match="does not match"):
                _import_service_key_from_files()

    def test_import_rejects_conflicting_created_by(self, app, initialized_db):
        private_key, kid, public_jwk = _generate_test_rsa_key()
        create_service_key(
            "manual-key", kid, "quay", public_jwk, {"created_by": "admin"}, None
        )
        approve_service_key(kid, ServiceKeyApprovalType.AUTOMATIC)

        with tempfile.TemporaryDirectory() as tmpdir:
            kid_path, pem_path = _write_key_files(tmpdir, private_key, kid)
            app.config["INSTANCE_SERVICE_KEY_KID_LOCATION"] = kid_path
            app.config["INSTANCE_SERVICE_KEY_LOCATION"] = pem_path

            from boot import _import_service_key_from_files

            with pytest.raises(Exception, match="refusing to claim"):
                _import_service_key_from_files()

    def test_import_backfills_created_by(self, app, initialized_db):
        private_key, kid, public_jwk = _generate_test_rsa_key()
        create_service_key("old-key", kid, "quay", public_jwk, {}, None)
        approve_service_key(kid, ServiceKeyApprovalType.AUTOMATIC)

        with tempfile.TemporaryDirectory() as tmpdir:
            kid_path, pem_path = _write_key_files(tmpdir, private_key, kid)
            app.config["INSTANCE_SERVICE_KEY_KID_LOCATION"] = kid_path
            app.config["INSTANCE_SERVICE_KEY_LOCATION"] = pem_path

            from boot import _import_service_key_from_files

            _import_service_key_from_files()

            db_key = ServiceKey.select().where(ServiceKey.kid == kid).get()
            assert db_key.metadata.get("created_by") == "quay-operator-readonly"

    def test_import_flag_false_does_not_trigger(self, app, initialized_db):
        """Existing key files at default paths must not trigger import when flag is false."""
        app.config["INSTANCE_SERVICE_KEY_IMPORT_FROM_FILES"] = False

        from boot import setup_instance_service_key

        with patch("boot.generate_key") as mock_gen, patch("builtins.open", MagicMock()):
            mock_gen.return_value = (MagicMock(), "test-kid")
            # Should go to the generate path, not import
            setup_instance_service_key()
            mock_gen.assert_called_once()

    def test_import_flag_true_missing_files_fails(self, app, initialized_db):
        app.config["INSTANCE_SERVICE_KEY_IMPORT_FROM_FILES"] = True
        app.config["INSTANCE_SERVICE_KEY_KID_LOCATION"] = "/nonexistent/quay.kid"
        app.config["INSTANCE_SERVICE_KEY_LOCATION"] = "/nonexistent/quay.pem"
        app.config["REGISTRY_STATE"] = "normal"

        from boot import setup_instance_service_key

        with pytest.raises(Exception, match="key files are missing"):
            setup_instance_service_key()


# ---------------------------------------------------------------------------
# Task 6: Readonly verification hardening
# ---------------------------------------------------------------------------


class TestReadonlyVerification:
    def test_verify_rejects_unapproved_key(self, app, initialized_db):
        private_key, kid, public_jwk = _generate_test_rsa_key()
        _create_operator_key(kid, public_jwk, approved=False)

        with tempfile.TemporaryDirectory() as tmpdir:
            kid_path, pem_path = _write_key_files(tmpdir, private_key, kid)
            app.config["INSTANCE_SERVICE_KEY_KID_LOCATION"] = kid_path
            app.config["INSTANCE_SERVICE_KEY_LOCATION"] = pem_path

            from boot import _verify_service_key

            assert _verify_service_key() is None

    def test_verify_rejects_expired_key(self, app, initialized_db):
        private_key, kid, public_jwk = _generate_test_rsa_key()
        _create_operator_key(kid, public_jwk, expired=True)

        with tempfile.TemporaryDirectory() as tmpdir:
            kid_path, pem_path = _write_key_files(tmpdir, private_key, kid)
            app.config["INSTANCE_SERVICE_KEY_KID_LOCATION"] = kid_path
            app.config["INSTANCE_SERVICE_KEY_LOCATION"] = pem_path

            from boot import _verify_service_key

            assert _verify_service_key() is None

    def test_verify_rejects_wrong_service(self, app, initialized_db):
        private_key, kid, public_jwk = _generate_test_rsa_key()
        _create_operator_key(kid, public_jwk, service="other")

        with tempfile.TemporaryDirectory() as tmpdir:
            kid_path, pem_path = _write_key_files(tmpdir, private_key, kid)
            app.config["INSTANCE_SERVICE_KEY_KID_LOCATION"] = kid_path
            app.config["INSTANCE_SERVICE_KEY_LOCATION"] = pem_path
            app.config["INSTANCE_SERVICE_KEY_SERVICE"] = "quay"

            from boot import _verify_service_key

            assert _verify_service_key() is None

    def test_verify_rejects_missing_pem(self, app, initialized_db):
        private_key, kid, public_jwk = _generate_test_rsa_key()
        _create_operator_key(kid, public_jwk)

        with tempfile.TemporaryDirectory() as tmpdir:
            kid_path = os.path.join(tmpdir, "quay-readonly.kid")
            with open(kid_path, "w") as f:
                f.write(kid)

            app.config["INSTANCE_SERVICE_KEY_KID_LOCATION"] = kid_path
            app.config["INSTANCE_SERVICE_KEY_LOCATION"] = os.path.join(tmpdir, "missing.pem")

            from boot import _verify_service_key

            assert _verify_service_key() is None

    def test_verify_succeeds_with_valid_key(self, app, initialized_db):
        private_key, kid, public_jwk = _generate_test_rsa_key()
        _create_operator_key(kid, public_jwk)

        with tempfile.TemporaryDirectory() as tmpdir:
            kid_path, pem_path = _write_key_files(tmpdir, private_key, kid)
            app.config["INSTANCE_SERVICE_KEY_KID_LOCATION"] = kid_path
            app.config["INSTANCE_SERVICE_KEY_LOCATION"] = pem_path
            app.config["INSTANCE_SERVICE_KEY_SERVICE"] = "quay"

            from boot import _verify_service_key

            assert _verify_service_key() == kid


# ---------------------------------------------------------------------------
# Task 7: Cleanup CLI
# ---------------------------------------------------------------------------


class TestManageServiceKey:
    def test_expire_missing_key_is_noop(self, initialized_db):
        assert expire_key("nonexistent-kid", 86400) == 0

    def test_expire_wrong_service_fails(self, initialized_db):
        private_key, kid, public_jwk = _generate_test_rsa_key()
        _create_operator_key(kid, public_jwk, service="other")

        assert expire_key(kid, 86400) == 1

    def test_expire_non_operator_key_fails(self, initialized_db):
        private_key, kid, public_jwk = _generate_test_rsa_key()
        create_service_key("manual", kid, "quay", public_jwk, {"created_by": "admin"}, None)

        assert expire_key(kid, 86400) == 1

    def test_expire_operator_key_succeeds(self, initialized_db):
        private_key, kid, public_jwk = _generate_test_rsa_key()
        _create_operator_key(kid, public_jwk)

        assert expire_key(kid, 86400) == 0
        key = ServiceKey.select().where(ServiceKey.kid == kid).get()
        assert key.expiration_date is not None
        assert key.expiration_date <= datetime.utcnow() + timedelta(seconds=86401)

    def test_expire_already_expiring_is_idempotent(self, initialized_db):
        private_key, kid, public_jwk = _generate_test_rsa_key()
        _create_operator_key(kid, public_jwk, expired=True)

        assert expire_key(kid, 86400) == 0

    def test_expire_no_metadata_fails(self, initialized_db):
        private_key, kid, public_jwk = _generate_test_rsa_key()
        create_service_key("bare", kid, "quay", public_jwk, {}, None)

        assert expire_key(kid, 86400) == 1


# ---------------------------------------------------------------------------
# Task 9: Cross-language thumbprint fixture
# ---------------------------------------------------------------------------


class TestCrossLanguageThumbprint:
    """
    Verify that authlib produces deterministic RFC 7638 thumbprints.
    The Go operator must produce identical thumbprints from the same PEM.
    """

    def test_pkcs1_and_pkcs8_produce_same_thumbprint(self):
        private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)

        pkcs1_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption(),
        )
        pkcs8_pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.PKCS8,
            encryption_algorithm=serialization.NoEncryption(),
        )

        jwk_from_pkcs1 = JsonWebKey.import_key(pkcs1_pem)
        jwk_from_pkcs8 = JsonWebKey.import_key(pkcs8_pem)

        kid_pkcs1 = jwk_from_pkcs1.as_dict()["kid"]
        kid_pkcs8 = jwk_from_pkcs8.as_dict()["kid"]

        assert kid_pkcs1 == kid_pkcs8

    def test_2048_bit_key_thumbprint_is_deterministic(self):
        private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption(),
        )

        kid1 = JsonWebKey.import_key(pem).as_dict()["kid"]
        kid2 = JsonWebKey.import_key(pem).as_dict()["kid"]
        assert kid1 == kid2

    def test_4096_bit_key_thumbprint_is_deterministic(self):
        private_key = rsa.generate_private_key(public_exponent=65537, key_size=4096)
        pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption(),
        )

        kid1 = JsonWebKey.import_key(pem).as_dict()["kid"]
        kid2 = JsonWebKey.import_key(pem).as_dict()["kid"]
        assert kid1 == kid2

    def test_as_dict_returns_only_public_fields(self):
        private_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
        pem = private_key.private_bytes(
            encoding=serialization.Encoding.PEM,
            format=serialization.PrivateFormat.TraditionalOpenSSL,
            encryption_algorithm=serialization.NoEncryption(),
        )
        jwk_obj = JsonWebKey.import_key(pem)
        public_dict = jwk_obj.as_dict()

        private_fields = {"d", "p", "q", "dp", "dq", "qi"}
        assert not private_fields.intersection(public_dict.keys())
        assert set(public_dict.keys()) == {"kty", "n", "e", "kid"}
