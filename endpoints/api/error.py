"""
Error details API.
"""
from flask import url_for

from endpoints.api import resource, nickname, ApiResource, path_param, define_json_response
from endpoints.exception import NotFound, ApiErrorType, ERROR_DESCRIPTION


def error_view(error_type):
    return {
        "type": url_for("api.error", error_type=error_type, _external=True),
        "title": error_type,
        "description": ERROR_DESCRIPTION[error_type],
    }


@resource("/v1/error/<error_type>")
@path_param("error_type", "The error code identifying the type of error.")
class Error(ApiResource):
    """
    Resource for Error Descriptions.
    """

    schemas = {
        "ApiErrorDescription": {
            "type": "object",
            "description": "Description of an error",
            "required": ["type", "description", "title",],
            "properties": {
                "type": {"type": "string", "description": "A reference to the error type resource"},
                "title": {
                    "type": "string",
                    "description": (
                        "The title of the error. Can be used to uniquely identify the kind"
                        " of error."
                    ),
                    "enum": list(ApiErrorType.__members__),
                },
                "description": {
                    "type": "string",
                    "description": (
                        "A more detailed description of the error that may include help for"
                        " fixing the issue."
                    ),
                },
            },
        },
    }

    @define_json_response("ApiErrorDescription")
    @nickname("getErrorDescription")
    def get(self, error_type):
        """
        Get a detailed description of the error.
        """
        if error_type in ERROR_DESCRIPTION.keys():
            return error_view(error_type)

        raise NotFound()
