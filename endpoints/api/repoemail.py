"""
Authorize repository to send e-mail notifications.
"""

import logging

from flask import request, abort

from endpoints.api import (
    resource,
    nickname,
    require_repo_admin,
    RepositoryParamResource,
    log_action,
    validate_json_request,
    internal_only,
    path_param,
    show_if,
)
from endpoints.api.repoemail_models_pre_oci import pre_oci_model as model
from endpoints.exception import NotFound
from app import tf
from data.database import db
from util.useremails import send_repo_authorization_email

import features

logger = logging.getLogger(__name__)


@internal_only
@resource("/v1/repository/<apirepopath:repository>/authorizedemail/<email>")
@show_if(features.MAILING)
@path_param("repository", "The full path of the repository. e.g. namespace/name")
@path_param("email", "The e-mail address")
class RepositoryAuthorizedEmail(RepositoryParamResource):
    """
    Resource for checking and authorizing e-mail addresses to receive repo notifications.
    """

    @require_repo_admin
    @nickname("checkRepoEmailAuthorized")
    def get(self, namespace, repository, email):
        """
        Checks to see if the given e-mail address is authorized on this repository.
        """
        record = model.get_email_authorized_for_repo(namespace, repository, email)
        if not record:
            abort(404)

        response = record.to_dict()
        del response["code"]
        return response

    @require_repo_admin
    @nickname("sendAuthorizeRepoEmail")
    def post(self, namespace, repository, email):
        """
        Starts the authorization process for an e-mail address on a repository.
        """

        with tf(db):
            record = model.get_email_authorized_for_repo(namespace, repository, email)
            if record and record.confirmed:
                response = record.to_dict()
                del response["code"]
                return response

            if not record:
                record = model.create_email_authorization_for_repo(namespace, repository, email)

            send_repo_authorization_email(namespace, repository, email, record.code)

            response = record.to_dict()
            del response["code"]
            return response
