import logging
import pathvalidate
import os

from datetime import datetime
from subprocess import Popen, PIPE

from flask import request, jsonify, make_response

from endpoints.exception import NotFound
from data.database import ServiceKeyApprovalType
from data.model import ServiceKeyDoesNotExist
from util.config.validator import EXTRA_CA_DIRECTORY

from config_app.config_endpoints.exception import InvalidRequest
from config_app.config_endpoints.api import (
    resource,
    ApiResource,
    nickname,
    log_action,
    validate_json_request,
)
from config_app.config_endpoints.api.superuser_models_pre_oci import (
    pre_oci_model,
    ServiceKeyAlreadyApproved,
)
from config_app.config_util.ssl import load_certificate, CertInvalidException
from config_app.c_app import app, config_provider, INIT_SCRIPTS_LOCATION


logger = logging.getLogger(__name__)


@resource("/v1/superuser/customcerts/<certpath>")
class SuperUserCustomCertificate(ApiResource):
    """
    Resource for managing a custom certificate.
    """

    @nickname("uploadCustomCertificate")
    def post(self, certpath):
        uploaded_file = request.files["file"]
        if not uploaded_file:
            raise InvalidRequest("Missing certificate file")

        # Save the certificate.
        certpath = pathvalidate.sanitize_filename(certpath)
        if not certpath.endswith(".crt"):
            raise InvalidRequest("Invalid certificate file: must have suffix `.crt`")

        logger.debug("Saving custom certificate %s", certpath)
        cert_full_path = config_provider.get_volume_path(EXTRA_CA_DIRECTORY, certpath)
        filename = config_provider.save_volume_file(cert_full_path, uploaded_file)
        logger.debug("Saved custom certificate %s to %s", certpath, filename)

        # Validate the certificate.
        try:
            logger.debug("Loading custom certificate %s", certpath)
            with config_provider.get_volume_file(cert_full_path) as f:
                load_certificate(f.read())
        except CertInvalidException:
            logger.exception("Got certificate invalid error for cert %s", certpath)
            return "", 204
        except IOError:
            logger.exception("Got IO error for cert %s", certpath)
            return "", 204

        # Call the update script with config dir location to install the certificate immediately.
        # This is needed by the configuration application to verify connections to external services
        # which require a self-signed or otherwise user-managed certificate.
        if not app.config["TESTING"]:

            try:
                cert_dir = os.path.join(config_provider.get_config_dir_path(), EXTRA_CA_DIRECTORY)
                script_env = {"CERTDIR": cert_dir}
                logger.debug("Installing certificates from the directory: %s" % cert_dir)

                script_filename = os.path.join(INIT_SCRIPTS_LOCATION, "certs_install.sh")
                logger.debug("Running script to install all certificates: %s", script_filename)

                process = Popen([script_filename], stderr=PIPE, stdout=PIPE, env=script_env)
                output, err = process.communicate()
                return_code = process.returncode

                if return_code != 0:
                    raise Exception("Could not install certificates. Output: %s" % output)
                else:
                    logger.debug("Successfully installed certificates. Output: %s", output)

            except Exception as e:
                logger.exception("Unable to install certificates. Unexpected error: %s", e)

        else:
            msg = (
                "Quay is using the test configuration. Certificates will not be installed. "
                "This may break the configuration app's ability to verify certificates."
            )
            logger.warning(msg)

        return "", 204

    @nickname("deleteCustomCertificate")
    def delete(self, certpath):
        cert_full_path = config_provider.get_volume_path(EXTRA_CA_DIRECTORY, certpath)
        config_provider.remove_volume_file(cert_full_path)
        return "", 204


@resource("/v1/superuser/customcerts")
class SuperUserCustomCertificates(ApiResource):
    """
    Resource for managing custom certificates.
    """

    @nickname("getCustomCertificates")
    def get(self):
        has_extra_certs_path = config_provider.volume_file_exists(EXTRA_CA_DIRECTORY)
        extra_certs_found = config_provider.list_volume_directory(EXTRA_CA_DIRECTORY)
        if extra_certs_found is None:
            return {
                "status": "file" if has_extra_certs_path else "none",
            }

        cert_views = []
        for extra_cert_path in extra_certs_found:
            try:
                cert_full_path = config_provider.get_volume_path(
                    EXTRA_CA_DIRECTORY, extra_cert_path
                )
                with config_provider.get_volume_file(cert_full_path) as f:
                    certificate = load_certificate(f.read())
                    cert_views.append(
                        {
                            "path": extra_cert_path,
                            "names": list(certificate.names),
                            "expired": certificate.expired,
                        }
                    )
            except CertInvalidException as cie:
                cert_views.append(
                    {"path": extra_cert_path, "error": str(cie),}
                )
            except IOError as ioe:
                cert_views.append(
                    {"path": extra_cert_path, "error": str(ioe),}
                )

        return {
            "status": "directory",
            "certs": cert_views,
        }


@resource("/v1/superuser/keys")
class SuperUserServiceKeyManagement(ApiResource):
    """
    Resource for managing service keys.
    """

    schemas = {
        "CreateServiceKey": {
            "id": "CreateServiceKey",
            "type": "object",
            "description": "Description of creation of a service key",
            "required": ["service", "expiration"],
            "properties": {
                "service": {
                    "type": "string",
                    "description": "The service authenticating with this key",
                },
                "name": {"type": "string", "description": "The friendly name of a service key",},
                "metadata": {
                    "type": "object",
                    "description": "The key/value pairs of this key's metadata",
                },
                "notes": {
                    "type": "string",
                    "description": "If specified, the extra notes for the key",
                },
                "expiration": {
                    "description": "The expiration date as a unix timestamp",
                    "anyOf": [{"type": "number"}, {"type": "null"}],
                },
            },
        },
    }

    @nickname("listServiceKeys")
    def get(self):
        keys = pre_oci_model.list_all_service_keys()

        return jsonify({"keys": [key.to_dict() for key in keys],})

    @nickname("createServiceKey")
    @validate_json_request("CreateServiceKey")
    def post(self):
        body = request.get_json()

        # Ensure we have a valid expiration date if specified.
        expiration_date = body.get("expiration", None)
        if expiration_date is not None:
            try:
                expiration_date = datetime.utcfromtimestamp(float(expiration_date))
            except ValueError as ve:
                raise InvalidRequest("Invalid expiration date: %s" % ve)

            if expiration_date <= datetime.now():
                raise InvalidRequest("Expiration date cannot be in the past")

        # Create the metadata for the key.
        metadata = body.get("metadata", {})
        metadata.update(
            {"created_by": "Quay Superuser Panel", "ip": request.remote_addr,}
        )

        # Generate a key with a private key that we *never save*.
        (private_key, key_id) = pre_oci_model.generate_service_key(
            body["service"], expiration_date, metadata=metadata, name=body.get("name", "")
        )
        # Auto-approve the service key.
        pre_oci_model.approve_service_key(
            key_id, ServiceKeyApprovalType.SUPERUSER, notes=body.get("notes", "")
        )

        # Log the creation and auto-approval of the service key.
        key_log_metadata = {
            "kid": key_id,
            "preshared": True,
            "service": body["service"],
            "name": body.get("name", ""),
            "expiration_date": expiration_date,
            "auto_approved": True,
        }

        log_action("service_key_create", None, key_log_metadata)
        log_action("service_key_approve", None, key_log_metadata)

        return jsonify(
            {
                "kid": key_id,
                "name": body.get("name", ""),
                "service": body["service"],
                "public_key": private_key.publickey().exportKey("PEM").decode("ascii"),
                "private_key": private_key.exportKey("PEM").decode("ascii"),
            }
        )


@resource("/v1/superuser/approvedkeys/<kid>")
class SuperUserServiceKeyApproval(ApiResource):
    """
    Resource for approving service keys.
    """

    schemas = {
        "ApproveServiceKey": {
            "id": "ApproveServiceKey",
            "type": "object",
            "description": "Information for approving service keys",
            "properties": {"notes": {"type": "string", "description": "Optional approval notes",},},
        },
    }

    @nickname("approveServiceKey")
    @validate_json_request("ApproveServiceKey")
    def post(self, kid):
        notes = request.get_json().get("notes", "")
        try:
            key = pre_oci_model.approve_service_key(
                kid, ServiceKeyApprovalType.SUPERUSER, notes=notes
            )

            # Log the approval of the service key.
            key_log_metadata = {
                "kid": kid,
                "service": key.service,
                "name": key.name,
                "expiration_date": key.expiration_date,
            }

            # Note: this may not actually be the current person modifying the config, but if they're in the config tool,
            # they have full access to the DB and could pretend to be any user, so pulling any superuser is likely fine
            super_user = app.config.get("SUPER_USERS", [None])[0]
            log_action("service_key_approve", super_user, key_log_metadata)
        except ServiceKeyDoesNotExist:
            raise NotFound()
        except ServiceKeyAlreadyApproved:
            pass

        return make_response("", 201)
