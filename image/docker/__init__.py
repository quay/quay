"""
docker implements pure data transformations according to the many Docker specifications.
"""


class DockerFormatException(Exception):
    pass


class ManifestException(DockerFormatException):
    pass
