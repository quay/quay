class WorkerError(object):
    """
    Helper class which represents errors raised by a build worker.
    """

    def __init__(self, error_code, base_message=None):
        self._error_code = error_code
        self._base_message = base_message

        self._error_handlers = {
            "io.quay.builder.buildpackissue": {
                "message": "Could not load build package",
                "is_internal": True,
            },
            "io.quay.builder.gitfailure": {
                "message": "Could not clone git repository",
                "show_base_error": True,
            },
            "io.quay.builder.gitcheckout": {
                "message": "Could not checkout git ref. If you force pushed recently, "
                + "the commit may be missing.",
                "show_base_error": True,
            },
            "io.quay.builder.cannotextractbuildpack": {
                "message": "Could not extract the contents of the build package"
            },
            "io.quay.builder.cannotpullforcache": {
                "message": "Could not pull cached image",
                "is_internal": True,
            },
            "io.quay.builder.dockerfileissue": {
                "message": "Could not find or parse Dockerfile",
                "show_base_error": True,
            },
            "io.quay.builder.cannotpullbaseimage": {
                "message": "Could not pull base image",
                "show_base_error": True,
            },
            "io.quay.builder.internalerror": {
                "message": "An internal error occurred while building. Please submit a ticket.",
                "is_internal": True,
            },
            "io.quay.builder.buildrunerror": {
                "message": "Could not start the build process",
                "is_internal": True,
            },
            "io.quay.builder.builderror": {
                "message": "A build step failed",
                "show_base_error": True,
            },
            "io.quay.builder.tagissue": {
                "message": "Could not tag built image",
                "is_internal": True,
            },
            "io.quay.builder.pushissue": {
                "message": "Could not push built image",
                "show_base_error": True,
                "is_internal": True,
            },
            "io.quay.builder.dockerconnecterror": {
                "message": "Could not connect to Docker daemon",
                "is_internal": True,
            },
            "io.quay.builder.missingorinvalidargument": {
                "message": "Missing required arguments for builder",
                "is_internal": True,
            },
            "io.quay.builder.cachelookupissue": {
                "message": "Error checking for a cached tag",
                "is_internal": True,
            },
            "io.quay.builder.errorduringphasetransition": {
                "message": "Error during phase transition. If this problem persists "
                + "please contact customer support.",
                "is_internal": True,
            },
            "io.quay.builder.clientrejectedtransition": {
                "message": "Build can not be finished due to user cancellation.",
            },
        }

    def is_internal_error(self):
        handler = self._error_handlers.get(self._error_code)
        return handler.get("is_internal", False) if handler else True

    def public_message(self):
        handler = self._error_handlers.get(self._error_code)
        if not handler:
            return "An unknown error occurred"

        message = handler["message"]
        if handler.get("show_base_error", False) and self._base_message:
            message = message + ": " + self._base_message

        return message

    def extra_data(self):
        if self._base_message:
            return {"base_error": self._base_message, "error_code": self._error_code}

        return {"error_code": self._error_code}
