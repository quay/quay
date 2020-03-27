import copy
import json
import math
import calendar

from app import app
from image.common import TarImageFormatter
from util.registry.gzipwrap import GZIP_BUFFER_SIZE
from util.registry.streamlayerformat import StreamLayerMerger


class FileEstimationException(Exception):
    """
    Exception raised by build_docker_load_stream if the estimated size of the layer tar was lower
    than the actual size.

    This means the sent tar header is wrong, and we have to fail.
    """

    pass


class SquashedDockerImageFormatter(TarImageFormatter):
    """
    Image formatter which produces a squashed image compatible with the `docker load` command.
    """

    # Multiplier against the image size reported by Docker to account for the tar metadata.
    # Note: This multiplier was not formally calculated in anyway and should be adjusted overtime
    # if/when we encounter issues with it. Unfortunately, we cannot make it too large or the Docker
    # daemon dies when trying to load the entire tar into memory.
    SIZE_MULTIPLIER = 1.2

    def stream_generator(
        self,
        tag,
        parsed_manifest,
        synthetic_image_id,
        layer_iterator,
        tar_stream_getter_iterator,
        reporter=None,
    ):
        image_mtime = 0
        created = parsed_manifest.created_datetime
        if created is not None:
            image_mtime = calendar.timegm(created.utctimetuple())

        # Docker import V1 Format (.tar):
        #  repositories - JSON file containing a repo -> tag -> image map
        #  {image ID folder}:
        #     json - The layer JSON
        #     layer.tar - The tarballed contents of the layer
        #     VERSION - The docker import version: '1.0'
        layer_merger = StreamLayerMerger(tar_stream_getter_iterator, reporter=reporter)

        # Yield the repositories file:
        synthetic_layer_info = {}
        synthetic_layer_info[tag.name + ".squash"] = synthetic_image_id

        hostname = app.config["SERVER_HOSTNAME"]
        repositories = {}
        namespace = tag.repository.namespace_name
        repository = tag.repository.name
        repositories[hostname + "/" + namespace + "/" + repository] = synthetic_layer_info

        yield self.tar_file(
            "repositories", json.dumps(repositories).encode("utf-8"), mtime=image_mtime
        )

        # Yield the image ID folder.
        yield self.tar_folder(synthetic_image_id, mtime=image_mtime)

        # Yield the JSON layer data.
        layer_json = SquashedDockerImageFormatter._build_layer_json(
            parsed_manifest, synthetic_image_id
        )
        yield self.tar_file(
            synthetic_image_id + "/json", json.dumps(layer_json).encode("utf-8"), mtime=image_mtime
        )

        # Yield the VERSION file.
        yield self.tar_file(synthetic_image_id + "/VERSION", b"1.0", mtime=image_mtime)

        # Yield the merged layer data's header.
        estimated_file_size = 0
        for layer in layer_iterator:
            estimated_file_size += layer.estimated_size(
                SquashedDockerImageFormatter.SIZE_MULTIPLIER
            )

        # Make sure the estimated file size is an integer number of bytes.
        estimated_file_size = int(math.ceil(estimated_file_size))

        yield self.tar_file_header(
            synthetic_image_id + "/layer.tar", estimated_file_size, mtime=image_mtime
        )

        # Yield the contents of the merged layer.
        yielded_size = 0
        for entry in layer_merger.get_generator():
            yield entry
            yielded_size += len(entry)

        # If the yielded size is more than the estimated size (which is unlikely but possible), then
        # raise an exception since the tar header will be wrong.
        if yielded_size > estimated_file_size:
            leaf_image_id = parsed_manifest.leaf_layer_v1_image_id
            message = "For %s/%s:%s (%s:%s): Expected %s bytes, found %s bytes" % (
                namespace,
                repository,
                tag,
                parsed_manifest.digest,
                leaf_image_id,
                estimated_file_size,
                yielded_size,
            )
            raise FileEstimationException(message)

        # If the yielded size is less than the estimated size (which is likely), fill the rest with
        # zeros.
        if yielded_size < estimated_file_size:
            to_yield = estimated_file_size - yielded_size
            while to_yield > 0:
                yielded = min(to_yield, GZIP_BUFFER_SIZE)
                yield b"\0" * yielded
                to_yield -= yielded

        # Yield any file padding to 512 bytes that is necessary.
        yield self.tar_file_padding(estimated_file_size)

        # Last two records are empty in tar spec.
        yield b"\0" * 512
        yield b"\0" * 512

    @staticmethod
    def _build_layer_json(manifest, synthetic_image_id):
        updated_json = json.loads(manifest.leaf_layer.raw_v1_metadata)
        updated_json["id"] = synthetic_image_id

        if "parent" in updated_json:
            del updated_json["parent"]

        if "config" in updated_json and "Image" in updated_json["config"]:
            updated_json["config"]["Image"] = synthetic_image_id

        if "container_config" in updated_json and "Image" in updated_json["container_config"]:
            updated_json["container_config"]["Image"] = synthetic_image_id

        return updated_json
