from enum import IntEnum, unique
from collections import namedtuple


@unique
class ScanLookupStatus(IntEnum):
    # Indicates that the given manifest or image could not be found in the registry data model.
    UNKNOWN_MANIFEST_OR_IMAGE = 0

    # Indicates that the security status of the manifest/image could not be loaded from the
    # downstream indexer.
    COULD_NOT_LOAD = 1

    # Indicates that the manifest/image is not yet indexed.
    NOT_YET_INDEXED = 2

    # Indicates that the manifest/image was unable to be indexed.
    FAILED_TO_INDEX = 3

    # Indicates that the manifest/image was unable to be indexed because the indexer does not
    # support it. Indexers may provide additional details in this case.
    UNSUPPORTED_FOR_INDEXING = 4

    # Indicates that the manifest/image has been indexed and its information has been returned.
    SUCCESS = 5


Vulnerability = namedtuple(
    "Vulnerability",
    ["Severity", "NamespaceName", "Link", "FixedBy", "Description", "Name", "Metadata"],
)
Metadata = namedtuple(
    "Metadata", ["UpdatedBy", "RepoName", "RepoLink", "DistroName", "DistroVersion"]
)
Feature = namedtuple(
    "Feature", ["Name", "VersionFormat", "NamespaceName", "AddedBy", "Version", "Vulnerabilities"]
)
Layer = namedtuple("Layer", ["Name", "NamespaceName", "ParentName", "IndexedByVersion", "Features"])


class SecurityInformation(namedtuple("SecurityInformation", ["Layer"])):
    """
    Canonical representation of security scan data for an image/manifest which is returned by the Quay API.
    """

    @classmethod
    def from_dict(cls, data_dict):
        return SecurityInformation(
            Layer(
                Name=data_dict["Layer"].get("Name", ""),
                ParentName=data_dict["Layer"].get("ParentName", ""),
                NamespaceName=data_dict["Layer"].get("NamespaceName", ""),
                IndexedByVersion=data_dict["Layer"].get("IndexedByVersion", None),
                Features=[
                    Feature(
                        Name=f["Name"],
                        VersionFormat=f["VersionFormat"],
                        NamespaceName=f["NamespaceName"],
                        AddedBy=f["AddedBy"],
                        Version=f["Version"],
                        Vulnerabilities=[
                            Vulnerability(
                                Severity=vuln.get("Severity", None),
                                NamespaceName=vuln.get("NamespaceName", None),
                                Link=vuln.get("Link", None),
                                FixedBy=vuln.get("FixedBy", None),
                                Description=vuln.get("Description", None),
                                Name=vuln.get("Name", None),
                                Metadata=Metadata(
                                    UpdatedBy=vuln["Metadata"].get("UpdatedBy", None),
                                    RepoName=vuln["Metadata"].get("RepoName", None),
                                    RepoLink=vuln["Metadata"].get("RepoLink", None),
                                    DistroName=vuln["Metadata"].get("DistroName", None),
                                    DistroVersion=vuln["Metadata"].get("DistroVersion", None),
                                ),
                            )
                            for vuln in f.get("Vulnerabilities", [])
                        ],
                    )
                    for f in data_dict["Layer"].get("Features", [])
                ],
            )
        )

    def to_dict(self):
        return {
            "Layer": {
                "Name": self.Layer.Name,
                "ParentName": self.Layer.ParentName,
                "NamespaceName": self.Layer.NamespaceName,
                "IndexedByVersion": self.Layer.IndexedByVersion,
                "Features": [
                    {
                        "Name": f.Name,
                        "VersionFormat": f.VersionFormat,
                        "NamespaceName": f.NamespaceName,
                        "AddedBy": f.AddedBy,
                        "Version": f.Version,
                        "Vulnerabilities": [
                            {
                                "Severity": v.Severity,
                                "NamespaceName": v.NamespaceName,
                                "Link": v.Link,
                                "FixedBy": v.FixedBy,
                                "Description": v.Description,
                                "Name": v.Name,
                                "Metadata": {
                                    "UpdatedBy": v.Metadata.UpdatedBy,
                                    "RepoName": v.Metadata.RepoName,
                                    "RepoLink": v.Metadata.RepoLink,
                                    "DistroName": v.Metadata.DistroName,
                                    "DistroVersion": v.Metadata.DistroVersion,
                                },
                            }
                            for v in f.Vulnerabilities
                        ],
                    }
                    for f in self.Layer.Features
                ],
            }
        }


class SecurityInformationLookupResult(object):
    """
    Represents the result of calling to lookup security information for a manifest/image.
    """

    def __init__(self, status, security_information=None, indexing_error=None, request_error=None):
        self._status = status
        self._request_error = request_error
        self._indexing_error = indexing_error
        self._security_information = security_information

    @classmethod
    def with_status(cls, status):
        return SecurityInformationLookupResult(status)

    @classmethod
    def for_request_error(cls, request_error):
        return SecurityInformationLookupResult(
            ScanLookupStatus.COULD_NOT_LOAD, request_error=request_error
        )

    @classmethod
    def for_data(cls, data):
        """
        Returns a result with successful status and the given data, provided that it
        passes validation.
        """

        assert isinstance(data, SecurityInformation)
        for f in data.Layer.Features:
            assert isinstance(f, Feature)
            for v in f.Vulnerabilities:
                assert isinstance(v, Vulnerability)

        return SecurityInformationLookupResult(ScanLookupStatus.SUCCESS, data)

    @property
    def security_information(self):
        """
        The loaded security information for the manifest/image.

        :rtype: SecurityInformation
        """
        return self._security_information

    @property
    def status(self):
        """
        The ScanLookupStatus of this requested lookup.
        """
        return self._status

    @property
    def indexing_error(self):
        """
        Returns the string of the error message describing why the manifest/image failed to index.

        May be empty or None if there was no error.
        """
        return self._indexing_error

    @property
    def scanner_request_error(self):
        """
        Returns the string of the error message when trying to load the security information from
        the downstream scanner.

        None otherwise.
        """
        return self._request_error


@unique
class PaginatedNotificationStatus(IntEnum):
    # Indicates that an error has occurred and that the lookup should be retried again in the
    # future.
    RETRYABLE_ERROR = 0

    # Indicates that an error has occurred and that the lookup should not be retried again in
    # the future
    FATAL_ERROR = 1

    # Indicates that the lookup was successful and more data is available for processing.
    SUCCESS = 2


class PaginatedNotificationResult(
    namedtuple("PaginatedNotificationResult", ["status", "data", "next_page_index"])
):
    """
    Named tuple that contains the result of a paginated notification lookup in the security scanner.
    """


class UpdatedVulnerability(
    namedtuple("UpdatedVulnerability", ["manifest_digest", "vulnerability"])
):
    """
    Named tuple that represents an updated vulnerability for a manifest.
    """
