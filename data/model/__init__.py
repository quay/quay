from data.database import db, db_transaction


class DataModelException(Exception):
    pass


class InvalidLabelKeyException(DataModelException):
    pass


class InvalidMediaTypeException(DataModelException):
    pass


class BlobDoesNotExist(DataModelException):
    pass


class InvalidBlobUpload(DataModelException):
    pass


class InvalidEmailAddressException(DataModelException):
    pass


class InvalidOrganizationException(DataModelException):
    pass


class InvalidPasswordException(DataModelException):
    pass


class InvalidRobotException(DataModelException):
    pass


class InvalidUsernameException(DataModelException):
    pass


class InvalidRepositoryBuildException(DataModelException):
    pass


class InvalidBuildTriggerException(DataModelException):
    pass


class InvalidTokenException(DataModelException):
    pass


class InvalidNotificationException(DataModelException):
    pass


class InvalidImageException(DataModelException):
    pass


class UserAlreadyInTeam(DataModelException):
    pass


class InvalidTeamException(DataModelException):
    pass


class InvalidTeamMemberException(DataModelException):
    pass


class InvalidManifestException(DataModelException):
    pass


class ServiceKeyDoesNotExist(DataModelException):
    pass


class ServiceKeyAlreadyApproved(DataModelException):
    pass


class ServiceNameInvalid(DataModelException):
    pass


class TagAlreadyCreatedException(DataModelException):
    pass


class StaleTagException(DataModelException):
    pass


class TooManyLoginAttemptsException(Exception):
    def __init__(self, message, retry_after):
        super(TooManyLoginAttemptsException, self).__init__(message)
        self.retry_after = retry_after


class Config(object):
    def __init__(self):
        self.app_config = None
        self.store = None
        self.image_cleanup_callbacks = []
        self.repo_cleanup_callbacks = []

    def register_image_cleanup_callback(self, callback):
        self.image_cleanup_callbacks.append(callback)
        return lambda: self.image_cleanup_callbacks.remove(callback)

    def register_repo_cleanup_callback(self, callback):
        self.repo_cleanup_callbacks.append(callback)
        return lambda: self.repo_cleanup_callbacks.remove(callback)


config = Config()


# There MUST NOT be any circular dependencies between these subsections. If there are fix it by
# moving the minimal number of things to _basequery
from data.model import (
    appspecifictoken,
    blob,
    build,
    gc,
    image,
    label,
    log,
    message,
    modelutil,
    notification,
    oauth,
    organization,
    permission,
    repositoryactioncount,
    repo_mirror,
    release,
    repo_mirror,
    repository,
    service_keys,
    storage,
    team,
    token,
    user,
)
