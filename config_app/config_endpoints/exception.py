from enum import Enum

from flask import url_for
from werkzeug.exceptions import HTTPException


class ApiErrorType(Enum):
    invalid_request = "invalid_request"


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


class InvalidRequest(ApiException):
    def __init__(self, error_description, payload=None):
        ApiException.__init__(self, ApiErrorType.invalid_request, 400, error_description, payload)


class InvalidResponse(ApiException):
    def __init__(self, error_description, payload=None):
        ApiException.__init__(self, ApiErrorType.invalid_response, 400, error_description, payload)
