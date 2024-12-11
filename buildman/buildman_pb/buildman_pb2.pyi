from typing import ClassVar as _ClassVar
from typing import Iterable as _Iterable
from typing import Mapping as _Mapping
from typing import Optional as _Optional
from typing import Union as _Union

from google.protobuf import descriptor as _descriptor
from google.protobuf import message as _message
from google.protobuf.internal import containers as _containers
from google.protobuf.internal import enum_type_wrapper as _enum_type_wrapper

DESCRIPTOR: _descriptor.FileDescriptor

class Phase(int, metaclass=_enum_type_wrapper.EnumTypeWrapper):
    __slots__ = ()
    WAITING: _ClassVar[Phase]
    UNPACKING: _ClassVar[Phase]
    PULLING: _ClassVar[Phase]
    BUILDING: _ClassVar[Phase]
    PUSHING: _ClassVar[Phase]
    COMPLETE: _ClassVar[Phase]
    ERROR: _ClassVar[Phase]

WAITING: Phase
UNPACKING: Phase
PULLING: Phase
BUILDING: Phase
PUSHING: Phase
COMPLETE: Phase
ERROR: Phase

class PingRequest(_message.Message):
    __slots__ = ()
    def __init__(self) -> None: ...

class PingReply(_message.Message):
    __slots__ = ("reply",)
    REPLY_FIELD_NUMBER: _ClassVar[int]
    reply: str
    def __init__(self, reply: _Optional[str] = ...) -> None: ...

class BuildJobArgs(_message.Message):
    __slots__ = ("register_jwt",)
    REGISTER_JWT_FIELD_NUMBER: _ClassVar[int]
    register_jwt: str
    def __init__(self, register_jwt: _Optional[str] = ...) -> None: ...

class BuildPack(_message.Message):
    __slots__ = (
        "job_jwt",
        "package_url",
        "git_package",
        "context",
        "dockerfile_path",
        "repository",
        "registry",
        "pull_token",
        "push_token",
        "tag_names",
        "base_image",
    )

    class BaseImage(_message.Message):
        __slots__ = ("username", "password")
        USERNAME_FIELD_NUMBER: _ClassVar[int]
        PASSWORD_FIELD_NUMBER: _ClassVar[int]
        username: str
        password: str
        def __init__(
            self, username: _Optional[str] = ..., password: _Optional[str] = ...
        ) -> None: ...

    class GitPackage(_message.Message):
        __slots__ = ("url", "sha", "private_key")
        URL_FIELD_NUMBER: _ClassVar[int]
        SHA_FIELD_NUMBER: _ClassVar[int]
        PRIVATE_KEY_FIELD_NUMBER: _ClassVar[int]
        url: str
        sha: str
        private_key: str
        def __init__(
            self,
            url: _Optional[str] = ...,
            sha: _Optional[str] = ...,
            private_key: _Optional[str] = ...,
        ) -> None: ...

    JOB_JWT_FIELD_NUMBER: _ClassVar[int]
    PACKAGE_URL_FIELD_NUMBER: _ClassVar[int]
    GIT_PACKAGE_FIELD_NUMBER: _ClassVar[int]
    CONTEXT_FIELD_NUMBER: _ClassVar[int]
    DOCKERFILE_PATH_FIELD_NUMBER: _ClassVar[int]
    REPOSITORY_FIELD_NUMBER: _ClassVar[int]
    REGISTRY_FIELD_NUMBER: _ClassVar[int]
    PULL_TOKEN_FIELD_NUMBER: _ClassVar[int]
    PUSH_TOKEN_FIELD_NUMBER: _ClassVar[int]
    TAG_NAMES_FIELD_NUMBER: _ClassVar[int]
    BASE_IMAGE_FIELD_NUMBER: _ClassVar[int]
    job_jwt: str
    package_url: str
    git_package: BuildPack.GitPackage
    context: str
    dockerfile_path: str
    repository: str
    registry: str
    pull_token: str
    push_token: str
    tag_names: _containers.RepeatedScalarFieldContainer[str]
    base_image: BuildPack.BaseImage
    def __init__(
        self,
        job_jwt: _Optional[str] = ...,
        package_url: _Optional[str] = ...,
        git_package: _Optional[_Union[BuildPack.GitPackage, _Mapping]] = ...,
        context: _Optional[str] = ...,
        dockerfile_path: _Optional[str] = ...,
        repository: _Optional[str] = ...,
        registry: _Optional[str] = ...,
        pull_token: _Optional[str] = ...,
        push_token: _Optional[str] = ...,
        tag_names: _Optional[_Iterable[str]] = ...,
        base_image: _Optional[_Union[BuildPack.BaseImage, _Mapping]] = ...,
    ) -> None: ...

class HeartbeatRequest(_message.Message):
    __slots__ = ("job_jwt",)
    JOB_JWT_FIELD_NUMBER: _ClassVar[int]
    job_jwt: str
    def __init__(self, job_jwt: _Optional[str] = ...) -> None: ...

class HeartbeatResponse(_message.Message):
    __slots__ = ("reply",)
    REPLY_FIELD_NUMBER: _ClassVar[int]
    reply: bool
    def __init__(self, reply: bool = ...) -> None: ...

class SetPhaseRequest(_message.Message):
    __slots__ = ("job_jwt", "sequence_number", "phase", "pull_metadata")

    class PullMetadata(_message.Message):
        __slots__ = ("registry_url", "base_image", "base_image_tag", "pull_username")
        REGISTRY_URL_FIELD_NUMBER: _ClassVar[int]
        BASE_IMAGE_FIELD_NUMBER: _ClassVar[int]
        BASE_IMAGE_TAG_FIELD_NUMBER: _ClassVar[int]
        PULL_USERNAME_FIELD_NUMBER: _ClassVar[int]
        registry_url: str
        base_image: str
        base_image_tag: str
        pull_username: str
        def __init__(
            self,
            registry_url: _Optional[str] = ...,
            base_image: _Optional[str] = ...,
            base_image_tag: _Optional[str] = ...,
            pull_username: _Optional[str] = ...,
        ) -> None: ...

    JOB_JWT_FIELD_NUMBER: _ClassVar[int]
    SEQUENCE_NUMBER_FIELD_NUMBER: _ClassVar[int]
    PHASE_FIELD_NUMBER: _ClassVar[int]
    PULL_METADATA_FIELD_NUMBER: _ClassVar[int]
    job_jwt: str
    sequence_number: int
    phase: Phase
    pull_metadata: SetPhaseRequest.PullMetadata
    def __init__(
        self,
        job_jwt: _Optional[str] = ...,
        sequence_number: _Optional[int] = ...,
        phase: _Optional[_Union[Phase, str]] = ...,
        pull_metadata: _Optional[_Union[SetPhaseRequest.PullMetadata, _Mapping]] = ...,
    ) -> None: ...

class SetPhaseResponse(_message.Message):
    __slots__ = ("success", "sequence_number")
    SUCCESS_FIELD_NUMBER: _ClassVar[int]
    SEQUENCE_NUMBER_FIELD_NUMBER: _ClassVar[int]
    success: bool
    sequence_number: int
    def __init__(self, success: bool = ..., sequence_number: _Optional[int] = ...) -> None: ...

class LogMessageRequest(_message.Message):
    __slots__ = ("job_jwt", "sequence_number", "log_message", "phase")
    JOB_JWT_FIELD_NUMBER: _ClassVar[int]
    SEQUENCE_NUMBER_FIELD_NUMBER: _ClassVar[int]
    LOG_MESSAGE_FIELD_NUMBER: _ClassVar[int]
    PHASE_FIELD_NUMBER: _ClassVar[int]
    job_jwt: str
    sequence_number: int
    log_message: str
    phase: str
    def __init__(
        self,
        job_jwt: _Optional[str] = ...,
        sequence_number: _Optional[int] = ...,
        log_message: _Optional[str] = ...,
        phase: _Optional[str] = ...,
    ) -> None: ...

class LogMessageResponse(_message.Message):
    __slots__ = ("success", "sequence_number")
    SUCCESS_FIELD_NUMBER: _ClassVar[int]
    SEQUENCE_NUMBER_FIELD_NUMBER: _ClassVar[int]
    success: bool
    sequence_number: int
    def __init__(self, success: bool = ..., sequence_number: _Optional[int] = ...) -> None: ...

class CachedTagRequest(_message.Message):
    __slots__ = ("job_jwt", "base_image_name", "base_image_tag", "base_image_id")
    JOB_JWT_FIELD_NUMBER: _ClassVar[int]
    BASE_IMAGE_NAME_FIELD_NUMBER: _ClassVar[int]
    BASE_IMAGE_TAG_FIELD_NUMBER: _ClassVar[int]
    BASE_IMAGE_ID_FIELD_NUMBER: _ClassVar[int]
    job_jwt: str
    base_image_name: str
    base_image_tag: str
    base_image_id: str
    def __init__(
        self,
        job_jwt: _Optional[str] = ...,
        base_image_name: _Optional[str] = ...,
        base_image_tag: _Optional[str] = ...,
        base_image_id: _Optional[str] = ...,
    ) -> None: ...

class CachedTag(_message.Message):
    __slots__ = ("CachedTag",)
    CACHEDTAG_FIELD_NUMBER: _ClassVar[int]
    CachedTag: str
    def __init__(self, CachedTag: _Optional[str] = ...) -> None: ...
