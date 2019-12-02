import inspect
import logging
import hashlib

from data.database import DerivedStorageForImage, TagManifest, Manifest, Image
from data.registry_model.registry_oci_model import back_compat_oci_model, oci_model
from data.registry_model.registry_pre_oci_model import pre_oci_model
from data.registry_model.datatypes import LegacyImage, Manifest as ManifestDataType


logger = logging.getLogger(__name__)


class SplitModel(object):
    def __init__(
        self, oci_model_proportion, oci_namespace_whitelist, v22_namespace_whitelist, oci_only_mode
    ):
        self.v22_namespace_whitelist = set(v22_namespace_whitelist)

        self.oci_namespace_whitelist = set(oci_namespace_whitelist)
        self.oci_namespace_whitelist.update(v22_namespace_whitelist)

        self.oci_model_proportion = oci_model_proportion
        self.oci_only_mode = oci_only_mode

    def supports_schema2(self, namespace_name):
        """ Returns whether the implementation of the data interface supports schema 2 format
        manifests. """
        return namespace_name in self.v22_namespace_whitelist

    def _namespace_from_kwargs(self, args_dict):
        if "namespace_name" in args_dict:
            return args_dict["namespace_name"]

        if "repository_ref" in args_dict:
            return args_dict["repository_ref"].namespace_name

        if "tag" in args_dict:
            return args_dict["tag"].repository.namespace_name

        if "manifest" in args_dict:
            manifest = args_dict["manifest"]
            if manifest._is_tag_manifest:
                return TagManifest.get(id=manifest._db_id).tag.repository.namespace_user.username
            else:
                return Manifest.get(id=manifest._db_id).repository.namespace_user.username

        if "manifest_or_legacy_image" in args_dict:
            manifest_or_legacy_image = args_dict["manifest_or_legacy_image"]
            if isinstance(manifest_or_legacy_image, LegacyImage):
                return Image.get(
                    id=manifest_or_legacy_image._db_id
                ).repository.namespace_user.username
            else:
                manifest = manifest_or_legacy_image
                if manifest._is_tag_manifest:
                    return TagManifest.get(
                        id=manifest._db_id
                    ).tag.repository.namespace_user.username
                else:
                    return Manifest.get(id=manifest._db_id).repository.namespace_user.username

        if "derived_image" in args_dict:
            return DerivedStorageForImage.get(
                id=args_dict["derived_image"]._db_id
            ).source_image.repository.namespace_user.username

        if "blob" in args_dict:
            return ""  # Blob functions are shared, so no need to do anything.

        if "blob_upload" in args_dict:
            return ""  # Blob functions are shared, so no need to do anything.

        raise Exception("Unknown namespace for dict `%s`" % args_dict)

    def __getattr__(self, attr):
        def method(*args, **kwargs):
            if self.oci_model_proportion >= 1.0:
                if self.oci_only_mode:
                    logger.debug(
                        "Calling method `%s` under full OCI data model for all namespaces", attr
                    )
                    return getattr(oci_model, attr)(*args, **kwargs)
                else:
                    logger.debug(
                        "Calling method `%s` under compat OCI data model for all namespaces", attr
                    )
                    return getattr(back_compat_oci_model, attr)(*args, **kwargs)

            argnames = inspect.getargspec(getattr(back_compat_oci_model, attr))[0]
            if not argnames and isinstance(args[0], ManifestDataType):
                args_dict = dict(manifest=args[0])
            else:
                args_dict = {argnames[index + 1]: value for index, value in enumerate(args)}

            if attr in [
                "yield_tags_for_vulnerability_notification",
                "get_most_recent_tag_lifetime_start",
            ]:
                use_oci = self.oci_model_proportion >= 1.0
                namespace_name = "(implicit for " + attr + ")"
            else:
                namespace_name = self._namespace_from_kwargs(args_dict)
                use_oci = namespace_name in self.oci_namespace_whitelist

                if not use_oci and self.oci_model_proportion:
                    # Hash the namespace name and see if it falls into the proportion bucket.
                    bucket = int(hashlib.md5(namespace_name).hexdigest(), 16) % 100
                    if bucket <= int(self.oci_model_proportion * 100):
                        logger.debug(
                            "Enabling OCI for namespace `%s` in proportional bucket", namespace_name
                        )
                        use_oci = True

            if use_oci:
                logger.debug(
                    "Calling method `%s` under OCI data model for namespace `%s`",
                    attr,
                    namespace_name,
                )
                return getattr(back_compat_oci_model, attr)(*args, **kwargs)
            else:
                return getattr(pre_oci_model, attr)(*args, **kwargs)

        return method
