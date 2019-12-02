import logging
import sys

from app import app
from data import model
from data.database import (
    RepositoryTag,
    Repository,
    TagToRepositoryTag,
    TagManifest,
    ManifestLegacyImage,
)

logger = logging.getLogger(__name__)


def _vs(first, second):
    return "%s vs %s" % (first, second)


def verify_backfill(namespace_name):
    logger.info("Checking namespace %s", namespace_name)
    namespace_user = model.user.get_namespace_user(namespace_name)
    assert namespace_user

    repo_tags = (
        RepositoryTag.select()
        .join(Repository)
        .where(Repository.namespace_user == namespace_user)
        .where(RepositoryTag.hidden == False)
    )

    repo_tags = list(repo_tags)
    logger.info("Found %s tags", len(repo_tags))

    for index, repo_tag in enumerate(repo_tags):
        logger.info(
            "Checking tag %s under repository %s (%s/%s)",
            repo_tag.name,
            repo_tag.repository.name,
            index + 1,
            len(repo_tags),
        )

        tag = TagToRepositoryTag.get(repository_tag=repo_tag).tag
        assert not tag.hidden
        assert tag.repository == repo_tag.repository
        assert tag.name == repo_tag.name, _vs(tag.name, repo_tag.name)
        assert tag.repository == repo_tag.repository, _vs(tag.repository_id, repo_tag.repository_id)
        assert tag.reversion == repo_tag.reversion, _vs(tag.reversion, repo_tag.reversion)

        start_check = int(tag.lifetime_start_ms / 1000) == repo_tag.lifetime_start_ts
        assert start_check, _vs(tag.lifetime_start_ms, repo_tag.lifetime_start_ts)
        if repo_tag.lifetime_end_ts is not None:
            end_check = int(tag.lifetime_end_ms / 1000) == repo_tag.lifetime_end_ts
            assert end_check, _vs(tag.lifetime_end_ms, repo_tag.lifetime_end_ts)
        else:
            assert tag.lifetime_end_ms is None

        try:
            tag_manifest = tag.manifest
            repo_tag_manifest = TagManifest.get(tag=repo_tag)

            digest_check = tag_manifest.digest == repo_tag_manifest.digest
            assert digest_check, _vs(tag_manifest.digest, repo_tag_manifest.digest)

            bytes_check = tag_manifest.manifest_bytes == repo_tag_manifest.json_data
            assert bytes_check, _vs(tag_manifest.manifest_bytes, repo_tag_manifest.json_data)
        except TagManifest.DoesNotExist:
            logger.info("No tag manifest found for repository tag %s", repo_tag.id)

        mli = ManifestLegacyImage.get(manifest=tag_manifest)
        assert mli.repository == repo_tag.repository

        manifest_legacy_image = mli.image
        assert manifest_legacy_image == repo_tag.image, _vs(
            manifest_legacy_image.id, repo_tag.image_id
        )


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    verify_backfill(sys.argv[1])
