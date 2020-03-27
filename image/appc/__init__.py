import json
import re
import calendar

from uuid import uuid4

from app import app
from util.registry.streamlayerformat import StreamLayerMerger
from util.dict_wrappers import JSONPathDict
from image.common import TarImageFormatter


ACNAME_REGEX = re.compile(r"[^a-z-]+")


class AppCImageFormatter(TarImageFormatter):
    """
    Image formatter which produces an tarball according to the AppC specification.
    """

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

        # ACI Format (.tar):
        #   manifest - The JSON manifest
        #   rootfs - The root file system

        # Yield the manifest.
        aci_manifest = json.dumps(
            DockerV1ToACIManifestTranslator.build_manifest(tag, parsed_manifest, synthetic_image_id)
        )
        yield self.tar_file("manifest", aci_manifest.encode("utf-8"), mtime=image_mtime)

        # Yield the merged layer dtaa.
        yield self.tar_folder("rootfs", mtime=image_mtime)

        layer_merger = StreamLayerMerger(
            tar_stream_getter_iterator, path_prefix="rootfs/", reporter=reporter
        )
        for entry in layer_merger.get_generator():
            yield entry


class DockerV1ToACIManifestTranslator(object):
    @staticmethod
    def _build_isolators(docker_config):
        """
        Builds ACI isolator config from the docker config.
        """

        def _isolate_memory(memory):
            return {"name": "memory/limit", "value": {"request": str(memory) + "B",}}

        def _isolate_swap(memory):
            return {"name": "memory/swap", "value": {"request": str(memory) + "B",}}

        def _isolate_cpu(cpu):
            return {"name": "cpu/shares", "value": {"request": str(cpu),}}

        def _isolate_capabilities(capabilities_set_value):
            capabilities_set = re.split(r"[\s,]", capabilities_set_value)
            return {"name": "os/linux/capabilities-retain-set", "value": {"set": capabilities_set,}}

        mappers = {
            "Memory": _isolate_memory,
            "MemorySwap": _isolate_swap,
            "CpuShares": _isolate_cpu,
            "Cpuset": _isolate_capabilities,
        }

        isolators = []

        for config_key in mappers:
            value = docker_config.get(config_key)
            if value:
                isolators.append(mappers[config_key](value))

        return isolators

    @staticmethod
    def _build_ports(docker_config):
        """
        Builds the ports definitions for the ACI.

        Formats:
          port/tcp
          port/udp
          port
        """
        ports = []

        exposed_ports = docker_config["ExposedPorts"]
        if exposed_ports is not None:
            port_list = list(exposed_ports.keys())
        else:
            port_list = docker_config["Ports"] or docker_config["ports"] or []

        for docker_port in port_list:
            protocol = "tcp"
            port_number = -1

            if "/" in docker_port:
                (port_number, protocol) = docker_port.split("/")
            else:
                port_number = docker_port

            try:
                port_number = int(port_number)
                ports.append(
                    {"name": "port-%s" % port_number, "port": port_number, "protocol": protocol,}
                )
            except ValueError:
                pass

        return ports

    @staticmethod
    def _ac_name(value):
        sanitized = ACNAME_REGEX.sub("-", value.lower()).strip("-")
        if sanitized == "":
            return str(uuid4())
        return sanitized

    @staticmethod
    def _build_volumes(docker_config):
        """
        Builds the volumes definitions for the ACI.
        """
        volumes = []

        def get_name(docker_volume_path):
            volume_name = DockerV1ToACIManifestTranslator._ac_name(docker_volume_path)
            return "volume-%s" % volume_name

        volume_list = docker_config["Volumes"] or docker_config["volumes"] or {}
        for docker_volume_path in volume_list.keys():
            if not docker_volume_path:
                continue

            volumes.append(
                {
                    "name": get_name(docker_volume_path),
                    "path": docker_volume_path,
                    "readOnly": False,
                }
            )
        return volumes

    @staticmethod
    def build_manifest(tag, manifest, synthetic_image_id):
        """
        Builds an ACI manifest of an existing repository image.
        """
        docker_layer_data = JSONPathDict(json.loads(manifest.leaf_layer.raw_v1_metadata))
        config = docker_layer_data["config"] or JSONPathDict({})

        namespace = tag.repository.namespace_name
        repo_name = tag.repository.name
        source_url = "%s://%s/%s/%s:%s" % (
            app.config["PREFERRED_URL_SCHEME"],
            app.config["SERVER_HOSTNAME"],
            namespace,
            repo_name,
            tag.name,
        )

        # ACI requires that the execution command be absolutely referenced. Therefore, if we find
        # a relative command, we give it as an argument to /bin/sh to resolve and execute for us.
        entrypoint = config["Entrypoint"] or []
        exec_path = entrypoint + (config["Cmd"] or [])
        if exec_path and not exec_path[0].startswith("/"):
            exec_path = ["/bin/sh", "-c", '""%s""' % " ".join(exec_path)]

        # TODO: ACI doesn't support : in the name, so remove any ports.
        hostname = app.config["SERVER_HOSTNAME"]
        hostname = hostname.split(":", 1)[0]

        # Calculate the environment variables.
        docker_env_vars = config.get("Env") or []
        env_vars = []
        for var in docker_env_vars:
            pieces = var.split("=")
            if len(pieces) != 2:
                continue

            env_vars.append(pieces)

        manifest = {
            "acKind": "ImageManifest",
            "acVersion": "0.6.1",
            "name": "%s/%s/%s" % (hostname.lower(), namespace.lower(), repo_name.lower()),
            "labels": [
                {"name": "version", "value": tag.name,},
                {"name": "arch", "value": docker_layer_data.get("architecture") or "amd64"},
                {"name": "os", "value": docker_layer_data.get("os") or "linux"},
            ],
            "app": {
                "exec": exec_path,
                # Below, `or 'root'` is required to replace empty string from Dockerfiles.
                "user": config.get("User") or "root",
                "group": config.get("Group") or "root",
                "eventHandlers": [],
                "workingDirectory": config.get("WorkingDir") or "/",
                "environment": [{"name": key, "value": value} for (key, value) in env_vars],
                "isolators": DockerV1ToACIManifestTranslator._build_isolators(config),
                "mountPoints": DockerV1ToACIManifestTranslator._build_volumes(config),
                "ports": DockerV1ToACIManifestTranslator._build_ports(config),
                "annotations": [
                    {"name": "created", "value": docker_layer_data.get("created") or ""},
                    {"name": "homepage", "value": source_url},
                    {"name": "quay.io/derived-image", "value": synthetic_image_id},
                ],
            },
        }

        return manifest
