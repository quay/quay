import bitmath


class V2RegistryException(Exception):
    def __init__(
        self,
        error_code_str="",
        message="",
        detail={},
        http_status_code=400,
        repository=None,
        scopes=None,
        is_read_only=False,
    ):
        super(V2RegistryException, self).__init__(message)
        self.http_status_code = http_status_code
        self.repository = repository
        self.scopes = scopes
        self.is_read_only = is_read_only

        self._error_code_str = error_code_str
        self._detail = detail

    def as_dict(self):
        error_dict = {
            "code": self._error_code_str,
            "message": str(self),
            "detail": self._detail if self._detail is not None else {},
        }

        if self.is_read_only:
            error_dict["is_readonly"] = True

        return error_dict


class BlobUnknown(V2RegistryException):
    http_status_code = 404

    def __init__(
        self,
        error_code_str="BLOB_UNKNOWN",
        message="blob unknown to registry",
        detail={},
        http_status_code=404,
        repository=None,
        scopes=None,
        is_read_only=False,
    ):
        super(BlobUnknown, self).__init__(
            error_code_str,
            message,
            detail,
            getattr(self, "http_status_code", http_status_code),
            repository,
            scopes,
            is_read_only,
        )


class BlobUploadInvalid(V2RegistryException):
    def __init__(
        self,
        error_code_str="BLOB_UPLOAD_INVALID",
        message="blob upload invalid",
        detail={},
        http_status_code=400,
        repository=None,
        scopes=None,
        is_read_only=False,
    ):
        super(BlobUploadInvalid, self).__init__(
            error_code_str,
            message,
            detail,
            getattr(self, "http_status_code", http_status_code),
            repository,
            scopes,
            is_read_only,
        )


class BlobUploadUnknown(V2RegistryException):
    http_status_code = 404

    def __init__(
        self,
        error_code_str="BLOB_UPLOAD_UNKNOWN",
        message="blob upload unknown to registry",
        detail={},
        http_status_code=404,
        repository=None,
        scopes=None,
        is_read_only=False,
    ):
        super(BlobUploadUnknown, self).__init__(
            error_code_str,
            message,
            detail,
            getattr(self, "http_status_code", http_status_code),
            repository,
            scopes,
            is_read_only,
        )


class DigestInvalid(V2RegistryException):
    def __init__(
        self,
        error_code_str="DIGEST_INVALID",
        message="provided digest did not match uploaded content",
        detail={},
        http_status_code=400,
        repository=None,
        scopes=None,
        is_read_only=False,
    ):
        super(DigestInvalid, self).__init__(
            error_code_str,
            message,
            detail,
            getattr(self, "http_status_code", http_status_code),
            repository,
            scopes,
            is_read_only,
        )


class ManifestBlobUnknown(V2RegistryException):
    def __init__(
        self,
        error_code_str="MANIFEST_BLOB_UNKNOWN",
        message="manifest blob unknown to registry",
        detail={},
        http_status_code=400,
        repository=None,
        scopes=None,
        is_read_only=False,
    ):
        super(ManifestBlobUnknown, self).__init__(
            error_code_str,
            message,
            detail,
            getattr(self, "http_status_code", http_status_code),
            repository,
            scopes,
            is_read_only,
        )


class ManifestInvalid(V2RegistryException):
    def __init__(
        self,
        error_code_str="MANIFEST_INVALID",
        message="manifest invalid",
        detail={},
        http_status_code=400,
        repository=None,
        scopes=None,
        is_read_only=False,
    ):
        super(ManifestInvalid, self).__init__(
            error_code_str,
            message,
            detail,
            getattr(self, "http_status_code", http_status_code),
            repository,
            scopes,
            is_read_only,
        )


class ManifestUnknown(V2RegistryException):
    http_status_code = 404

    def __init__(
        self,
        error_code_str="MANIFEST_UNKNOWN",
        message="manifest unknown",
        detail={},
        http_status_code=404,
        repository=None,
        scopes=None,
        is_read_only=False,
    ):
        super(ManifestUnknown, self).__init__(
            error_code_str,
            message,
            detail,
            getattr(self, "http_status_code", http_status_code),
            repository,
            scopes,
            is_read_only,
        )


class TagExpired(V2RegistryException):
    http_status_code = 404

    def __init__(
        self,
        error_code_str="TAG_EXPIRED",
        message="Tag has expired",
        detail={},
        http_status_code=404,
        repository=None,
        scopes=None,
        is_read_only=False,
    ):
        super(TagExpired, self).__init__(
            error_code_str,
            message,
            detail,
            getattr(self, "http_status_code", http_status_code),
            repository,
            scopes,
            is_read_only,
        )


class ManifestUnverified(V2RegistryException):
    def __init__(
        self,
        error_code_str="MANIFEST_UNVERIFIED",
        message="manifest failed signature verification",
        detail={},
        http_status_code=400,
        repository=None,
        scopes=None,
        is_read_only=False,
    ):
        super(ManifestUnverified, self).__init__(
            error_code_str,
            message,
            detail,
            getattr(self, "http_status_code", http_status_code),
            repository,
            scopes,
            is_read_only,
        )


class NameInvalid(V2RegistryException):
    def __init__(
        self,
        error_code_str="NAME_INVALID",
        message="invalid repository name",
        detail={},
        http_status_code=400,
        repository=None,
        scopes=None,
        is_read_only=False,
    ):
        super(NameInvalid, self).__init__(
            error_code_str,
            message,
            detail,
            getattr(self, "http_status_code", http_status_code),
            repository,
            scopes,
            is_read_only,
        )


class NameUnknown(V2RegistryException):
    http_status_code = 404

    def __init__(
        self,
        error_code_str="NAME_UNKNOWN",
        message="repository name not known to registry",
        detail={},
        http_status_code=404,
        repository=None,
        scopes=None,
        is_read_only=False,
    ):
        super(NameUnknown, self).__init__(
            error_code_str,
            message,
            detail,
            getattr(self, "http_status_code", http_status_code),
            repository,
            scopes,
            is_read_only,
        )


class SizeInvalid(V2RegistryException):
    def __init__(
        self,
        error_code_str="SIZE_INVALID",
        message="provided length did not match content length",
        detail={},
        http_status_code=400,
        repository=None,
        scopes=None,
        is_read_only=False,
    ):
        super(SizeInvalid, self).__init__(
            error_code_str,
            message,
            detail,
            getattr(self, "http_status_code", http_status_code),
            repository,
            scopes,
            is_read_only,
        )


class TagAlreadyExists(V2RegistryException):
    http_status_code = 409

    def __init__(
        self,
        error_code_str="TAG_ALREADY_EXISTS",
        message="tag was already pushed",
        detail={},
        http_status_code=409,
        repository=None,
        scopes=None,
        is_read_only=False,
    ):
        super(TagAlreadyExists, self).__init__(
            error_code_str,
            message,
            detail,
            getattr(self, "http_status_code", http_status_code),
            repository,
            scopes,
            is_read_only,
        )


class TagInvalid(V2RegistryException):
    def __init__(
        self,
        error_code_str="TAG_INVALID",
        message="manifest tag did not match URI",
        detail={},
        http_status_code=400,
        repository=None,
        scopes=None,
        is_read_only=False,
    ):
        super(TagInvalid, self).__init__(
            error_code_str,
            message,
            detail,
            getattr(self, "http_status_code", http_status_code),
            repository,
            scopes,
            is_read_only,
        )


class TooManyTagsRequested(V2RegistryException):
    http_status_code = 413

    def __init__(
        self,
        error_code_str="TOO_MANY_TAGS_REQUESTED",
        message="too many tags requested",
        detail={},
        http_status_code=413,
        repository=None,
        scopes=None,
        is_read_only=False,
    ):
        super(TooManyTagsRequested, self).__init__(
            error_code_str,
            message,
            detail,
            getattr(self, "http_status_code", http_status_code),
            repository,
            scopes,
            is_read_only,
        )


class LayerTooLarge(V2RegistryException):
    http_status_code = 413

    def __init__(
        self,
        error_code_str="LAYER_TOO_LARGE",
        message="Uploaded blob is larger than allowed by this registry",
        detail={},
        http_status_code=413,
        repository=None,
        scopes=None,
        is_read_only=False,
        uploaded=None,
        max_allowed=None,
    ):

        if uploaded is not None and max_allowed is not None:
            detail = {
                "reason": "%s is greater than maximum allowed size %s" % (uploaded, max_allowed),
                "max_allowed": max_allowed,
                "uploaded": uploaded,
            }

            up_str = bitmath.Byte(uploaded).best_prefix().format("{value:.2f} {unit}")
            max_str = bitmath.Byte(max_allowed).best_prefix().format("{value:.2f} {unit}")
            message = "Uploaded blob of %s is larger than %s allowed by this registry" % (
                up_str,
                max_str,
            )
        super(LayerTooLarge, self).__init__(
            error_code_str,
            message,
            detail,
            getattr(self, "http_status_code", http_status_code),
            repository,
            scopes,
            is_read_only,
        )


class QuotaExceeded(V2RegistryException):
    http_status_code = 403

    def __init__(
        self,
        error_code_str="DENIED",
        message="Quota has been exceeded on namespace",
        detail={},
        http_status_code=403,
        repository=None,
        scopes=None,
        is_read_only=False,
    ):
        super(QuotaExceeded, self).__init__(
            error_code_str,
            message,
            detail,
            getattr(self, "http_status_code", http_status_code),
            repository,
            scopes,
            is_read_only,
        )


class Unauthorized(V2RegistryException):
    http_status_code = 401

    def __init__(
        self,
        error_code_str="UNAUTHORIZED",
        message="access to the requested resource is not authorized",
        detail={},
        http_status_code=401,
        repository=None,
        scopes=None,
        is_read_only=False,
    ):
        super(Unauthorized, self).__init__(
            error_code_str,
            message,
            detail,
            getattr(self, "http_status_code", http_status_code),
            repository,
            scopes,
            is_read_only,
        )


class Unsupported(V2RegistryException):
    http_status_code = 405

    def __init__(
        self,
        error_code_str="UNSUPPORTED",
        message="The operation is unsupported.",
        detail={},
        http_status_code=405,
        repository=None,
        scopes=None,
        is_read_only=False,
    ):
        super(Unsupported, self).__init__(
            error_code_str,
            message,
            detail,
            getattr(self, "http_status_code", http_status_code),
            repository,
            scopes,
            is_read_only,
        )


class InvalidLogin(V2RegistryException):
    http_status_code = 401

    def __init__(
        self,
        error_code_str="UNAUTHORIZED",
        message="Specified credentials are invalid",
        detail={},
        http_status_code=401,
        repository=None,
        scopes=None,
        is_read_only=False,
    ):
        super(InvalidLogin, self).__init__(
            error_code_str,
            message,
            detail,
            getattr(self, "http_status_code", http_status_code),
            repository,
            scopes,
            is_read_only,
        )


class InvalidRequest(V2RegistryException):
    def __init__(
        self,
        error_code_str="INVALID_REQUEST",
        message="Invalid request",
        detail={},
        http_status_code=400,
        repository=None,
        scopes=None,
        is_read_only=False,
    ):
        super(InvalidRequest, self).__init__(
            error_code_str,
            message,
            detail,
            getattr(self, "http_status_code", http_status_code),
            repository,
            scopes,
            is_read_only,
        )


class NamespaceDisabled(V2RegistryException):
    http_status_code = 405

    def __init__(
        self,
        error_code_str="DENIED",
        message="This namespace is disabled. Please contact your system administrator.",
        detail={},
        http_status_code=405,
        repository=None,
        scopes=None,
        is_read_only=False,
    ):
        super(NamespaceDisabled, self).__init__(
            error_code_str,
            message,
            detail,
            getattr(self, "http_status_code", http_status_code),
            repository,
            scopes,
            is_read_only,
        )


class BlobDownloadGeoBlocked(V2RegistryException):
    http_status_code = 403

    def __init__(
        self,
        error_code_str="DENIED",
        message=(
            "The region from which you are pulling has been geo-ip blocked. "
            + "Please contact the namespace owner."
        ),
        detail={},
        http_status_code=403,
        repository=None,
        scopes=None,
        is_read_only=False,
    ):
        super(BlobDownloadGeoBlocked, self).__init__(
            error_code_str,
            message,
            detail,
            getattr(self, "http_status_code", http_status_code),
            repository,
            scopes,
            is_read_only,
        )


class ReadOnlyMode(V2RegistryException):
    http_status_code = 405

    def __init__(
        self,
        error_code_str="DENIED",
        message=(
            "System is currently read-only. Pulls will succeed but all write operations "
            + "are currently suspended."
        ),
        detail={},
        http_status_code=405,
        repository=None,
        scopes=None,
        is_read_only=False,
    ):
        super(ReadOnlyMode, self).__init__(
            error_code_str,
            message,
            detail,
            getattr(self, "http_status_code", http_status_code),
            repository,
            scopes,
            is_read_only,
        )


class PushesDisabled(V2RegistryException):
    http_status_code = 405

    def __init__(
        self,
        error_code_str="METHOD NOT ALLOWED",
        message=(
            "Pushes to the registry are currently disabled. Please contact"
            + " the administrator for more information."
        ),
        detail={},
        http_status_code=405,
        repository=None,
        scopes=None,
        is_read_only=False,
    ):
        super(PushesDisabled, self).__init__(
            error_code_str,
            message,
            detail,
            getattr(self, "http_status_code", http_status_code),
            repository,
            scopes,
            is_read_only,
        )
