import bitmath


class V2RegistryException(Exception):
    def __init__(
        self,
        error_code_str,
        message,
        detail,
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
    def __init__(self, detail=None):
        super(BlobUnknown, self).__init__("BLOB_UNKNOWN", "blob unknown to registry", detail, 404)


class BlobUploadInvalid(V2RegistryException):
    def __init__(self, detail=None):
        super(BlobUploadInvalid, self).__init__(
            "BLOB_UPLOAD_INVALID", "blob upload invalid", detail
        )


class BlobUploadUnknown(V2RegistryException):
    def __init__(self, detail=None):
        super(BlobUploadUnknown, self).__init__(
            "BLOB_UPLOAD_UNKNOWN", "blob upload unknown to registry", detail, 404
        )


class DigestInvalid(V2RegistryException):
    def __init__(self, detail=None):
        super(DigestInvalid, self).__init__(
            "DIGEST_INVALID", "provided digest did not match uploaded content", detail
        )


class ManifestBlobUnknown(V2RegistryException):
    def __init__(self, detail=None):
        super(ManifestBlobUnknown, self).__init__(
            "MANIFEST_BLOB_UNKNOWN", "manifest blob unknown to registry", detail
        )


class ManifestInvalid(V2RegistryException):
    def __init__(self, detail=None, http_status_code=400):
        super(ManifestInvalid, self).__init__(
            "MANIFEST_INVALID", "manifest invalid", detail, http_status_code
        )


class ManifestUnknown(V2RegistryException):
    def __init__(self, detail=None):
        super(ManifestUnknown, self).__init__("MANIFEST_UNKNOWN", "manifest unknown", detail, 404)


class TagExpired(V2RegistryException):
    def __init__(self, message=None, detail=None):
        super(TagExpired, self).__init__("TAG_EXPIRED", message or "Tag has expired", detail, 404)


class ManifestUnverified(V2RegistryException):
    def __init__(self, detail=None):
        super(ManifestUnverified, self).__init__(
            "MANIFEST_UNVERIFIED", "manifest failed signature verification", detail
        )


class NameInvalid(V2RegistryException):
    def __init__(self, detail=None, message=None):
        super(NameInvalid, self).__init__(
            "NAME_INVALID", message or "invalid repository name", detail
        )


class NameUnknown(V2RegistryException):
    def __init__(self, detail=None):
        super(NameUnknown, self).__init__(
            "NAME_UNKNOWN", "repository name not known to registry", detail, 404
        )


class SizeInvalid(V2RegistryException):
    def __init__(self, detail=None):
        super(SizeInvalid, self).__init__(
            "SIZE_INVALID", "provided length did not match content length", detail
        )


class TagAlreadyExists(V2RegistryException):
    def __init__(self, detail=None):
        super(TagAlreadyExists, self).__init__(
            "TAG_ALREADY_EXISTS", "tag was already pushed", detail, 409
        )


class TagInvalid(V2RegistryException):
    def __init__(self, detail=None):
        super(TagInvalid, self).__init__("TAG_INVALID", "manifest tag did not match URI", detail)


class LayerTooLarge(V2RegistryException):
    def __init__(self, uploaded=None, max_allowed=None):
        detail = {}
        message = "Uploaded blob is larger than allowed by this registry"

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


class Unauthorized(V2RegistryException):
    def __init__(self, detail=None, repository=None, scopes=None):
        super(Unauthorized, self).__init__(
            "UNAUTHORIZED",
            "access to the requested resource is not authorized",
            detail,
            401,
            repository=repository,
            scopes=scopes,
        )


class Unsupported(V2RegistryException):
    def __init__(self, detail=None, message=None):
        super(Unsupported, self).__init__(
            "UNSUPPORTED", message or "The operation is unsupported.", detail, 405
        )


class InvalidLogin(V2RegistryException):
    def __init__(self, message=None):
        super(InvalidLogin, self).__init__(
            "UNAUTHORIZED", message or "Specified credentials are invalid", {}, 401
        )


class InvalidRequest(V2RegistryException):
    def __init__(self, message=None):
        super(InvalidRequest, self).__init__(
            "INVALID_REQUEST", message or "Invalid request", {}, 400
        )


class NamespaceDisabled(V2RegistryException):
    def __init__(self, message=None):
        message = message or "This namespace is disabled. Please contact your system administrator."
        super(NamespaceDisabled, self).__init__("DENIED", message, {}, 405)


class BlobDownloadGeoBlocked(V2RegistryException):
    def __init__(self, detail=None):
        message = (
            "The region from which you are pulling has been geo-ip blocked. "
            + "Please contact the namespace owner."
        )
        super(BlobDownloadGeoBlocked, self).__init__("DENIED", message, detail, 403)


class ReadOnlyMode(V2RegistryException):
    def __init__(self, detail=None):
        message = (
            "System is currently read-only. Pulls will succeed but all write operations "
            + "are currently suspended."
        )
        super(ReadOnlyMode, self).__init__("DENIED", message, detail, 405, is_read_only=True)
