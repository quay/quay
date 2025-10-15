from enum import Enum

from flask import url_for
from werkzeug.exceptions import HTTPException

from auth.auth_context import get_authenticated_user


class ApiErrorType(Enum):
    external_service_timeout = "external_service_timeout"
    invalid_request = "invalid_request"
    invalid_response = "invalid_response"
    invalid_token = "invalid_token"
    expired_token = "expired_token"
    insufficient_scope = "insufficient_scope"
    fresh_login_required = "fresh_login_required"
    exceeds_license = "exceeds_license"
    not_found = "not_found"
    downstream_issue = "downstream_issue"


ERROR_DESCRIPTION = {
    ApiErrorType.external_service_timeout.value: "An external service timed out. Retrying the request may resolve the issue.",
    ApiErrorType.invalid_request.value: "The request was invalid. It may have contained invalid values or was improperly formatted.",
    ApiErrorType.invalid_response.value: "The response was invalid.",
    ApiErrorType.invalid_token.value: "The access token provided was invalid.",
    ApiErrorType.expired_token.value: "The access token provided has expired.",
    ApiErrorType.insufficient_scope.value: "The access token did not have sufficient scope to access the requested resource.",
    ApiErrorType.fresh_login_required.value: "The action requires a fresh login to succeed.",
    ApiErrorType.exceeds_license.value: "The action was refused because the current license does not allow it.",
    ApiErrorType.not_found.value: "The resource was not found.",
    ApiErrorType.downstream_issue.value: "An error occurred in a downstream service.",
}


class ApiException(HTTPException):
    """
    Represents an error in the application/problem+json format.

    See: https://tools.ietf.org/html/rfc7807

     -  "type" (string) - A URI reference that identifies the
        problem type.

     -  "title" (string) - A short, human-readable summary of the problem
        type.  It SHOULD NOT change from occurrence to occurrence of the
        problem, except for purposes of localization

     -  "status" (number) - The HTTP status code

     -  "detail" (string) - A human-readable explanation specific to this
        occurrence of the problem.

     -  "instance" (string) - A URI reference that identifies the specific
        occurrence of the problem.  It may or may not yield further
        information if dereferenced.
    """

    def __init__(self, error_type, status_code, error_description, payload=None):
        Exception.__init__(self)
        self.error_description = error_description
        self.code = status_code
        self.payload = payload
        self.error_type = error_type
        self.data = self.to_dict()

        super(ApiException, self).__init__(error_description, None)

    def to_dict(self):
        rv = dict(self.payload or ())

        if self.error_description is not None:
            rv["detail"] = self.error_description
            rv["error_message"] = self.error_description  # TODO: deprecate

        rv["error_type"] = self.error_type.value  # TODO: deprecate
        rv["title"] = self.error_type.value
        rv["type"] = url_for("api.error", error_type=self.error_type.value, _external=True)
        rv["status"] = self.code

        return rv


class ExternalServiceError(ApiException):
    def __init__(self, error_description, payload=None):
        ApiException.__init__(
            self, ApiErrorType.external_service_timeout, 520, error_description, payload
        )


class InvalidRequest(ApiException):
    def __init__(self, error_description, payload=None):
        ApiException.__init__(self, ApiErrorType.invalid_request, 400, error_description, payload)


class InvalidResponse(ApiException):
    def __init__(self, error_description, payload=None):
        ApiException.__init__(self, ApiErrorType.invalid_response, 400, error_description, payload)


class InvalidToken(ApiException):
    def __init__(self, error_description, payload=None):
        ApiException.__init__(self, ApiErrorType.invalid_token, 401, error_description, payload)


class ExpiredToken(ApiException):
    def __init__(self, error_description, payload=None):
        ApiException.__init__(self, ApiErrorType.expired_token, 401, error_description, payload)


class Unauthorized(ApiException):
    def __init__(self, payload=None):
        user = get_authenticated_user()
        if user is None or user.organization:
            ApiException.__init__(
                self, ApiErrorType.invalid_token, 401, "Requires authentication", payload
            )
        else:
            ApiException.__init__(
                self, ApiErrorType.insufficient_scope, 403, "Unauthorized", payload
            )


class FreshLoginRequired(ApiException):
    def __init__(self, payload=None):
        ApiException.__init__(
            self, ApiErrorType.fresh_login_required, 401, "Requires fresh login", payload
        )


class ExceedsLicenseException(ApiException):
    def __init__(self, payload=None):
        ApiException.__init__(self, ApiErrorType.exceeds_license, 402, "Payment Required", payload)


class NotFound(ApiException):
    def __init__(self, payload=None):
        ApiException.__init__(self, ApiErrorType.not_found, 404, "Not Found", payload)


class DownstreamIssue(ApiException):
    def __init__(self, error_description, payload=None):
        ApiException.__init__(self, ApiErrorType.downstream_issue, 520, error_description, payload)
