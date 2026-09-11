"""Dataclasses for Quay CI matrix cells.

A `matrix.yaml` expands as: each `quay[]` release (identified by `branch`,
e.g. `redhat-3.18`) × each `jobs[]` entry × `clouds` × `ocp` → one `Cell`.
The Quay version is derived from the branch suffix.

`image_source` is carried for forward compatibility; templates do not use it
yet.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

YamlMap = dict[str, Any]

STORAGE_BY_CLOUD = {
    "aws": "s3",
    "gcp": "gcs",
    "azure": "blob",
}
DEPLOY_REF_BY_CLOUD = {
    "aws": "quay-deploy-aws-s3",
    "gcp": "quay-deploy-gcp-gcs",
    "azure": "quay-deploy-azure-blob",
}


@dataclass(frozen=True)
class Cell:
    org: str
    repo: str
    branch: str
    quay_version: str
    ocp_version: str
    cloud: str
    test: str
    tier: str
    arch: str = "amd64"
    image_source: str = "build"
    env: dict[str, Any] = field(default_factory=dict)
    as_name: str | None = None

    @property
    def quay_version_dashed(self) -> str:
        return self.quay_version.replace(".", "-")

    @property
    def ocp_version_dashed(self) -> str:
        return self.ocp_version.replace(".", "-")

    @property
    def ocp_version_nodot(self) -> str:
        return self.ocp_version.replace(".", "")

    @property
    def storage(self) -> str:
        try:
            return STORAGE_BY_CLOUD[self.cloud]
        except KeyError as exc:
            raise ValueError(f"unsupported cloud {self.cloud!r}") from exc

    @property
    def deploy_ref(self) -> str:
        try:
            return DEPLOY_REF_BY_CLOUD[self.cloud]
        except KeyError as exc:
            raise ValueError(f"unsupported cloud {self.cloud!r}") from exc

    @property
    def operator_channel(self) -> str:
        return f"stable-{self.quay_version}"

    @property
    def index_image_repo(self) -> str:
        dashed = self.quay_version_dashed
        ocp = self.ocp_version_dashed
        return "quay.io/redhat-user-workloads/quay-eng-tenant/" f"stable-{dashed}-v{ocp}"

    @property
    def variant(self) -> str:
        return f"{self.cloud}-ocp{self.ocp_version_nodot}-{self.test}"

    @property
    def test_as(self) -> str:
        return (
            f"{self.cloud}-{self.storage}-{self.quay_version_dashed}-"
            f"{self.tier}-{self.ocp_version_dashed}"
        )

    @property
    def filename(self) -> str:
        return f"{self.org}-{self.repo}-{self.branch}__{self.variant}.yaml"

    @property
    def owned_prefix(self) -> str:
        return f"{self.org}-{self.repo}-{self.branch}__"

    def context(self) -> dict[str, str]:
        return {
            "org": self.org,
            "repo": self.repo,
            "branch": self.branch,
            "quay_version": self.quay_version,
            "quay_version_dashed": self.quay_version_dashed,
            "ocp_version": self.ocp_version,
            "ocp_version_dashed": self.ocp_version_dashed,
            "ocp_version_nodot": self.ocp_version_nodot,
            "cloud": self.cloud,
            "storage": self.storage,
            "test": self.test,
            "tier": self.tier,
            "arch": self.arch,
            "image_source": self.image_source,
            "operator_channel": self.operator_channel,
            "index_image_repo": self.index_image_repo,
            "variant": self.variant,
            "test_as": self.test_as,
            "deploy_ref": self.deploy_ref,
        }
