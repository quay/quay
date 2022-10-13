import logging

logger = logging.getLogger(__name__)


class RepoMirrorConfigValidator(object):
    """
    Helper class for validating the repository mirror configuration.
    """

    def __init__(self, feature_repo_mirror):
        self._feature_repo_mirror = feature_repo_mirror

    def valid(self):
        if not self._feature_repo_mirror:
            raise Exception("REPO_MIRROR feature not enabled")
        return True
