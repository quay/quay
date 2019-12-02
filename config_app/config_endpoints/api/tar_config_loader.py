import os
import tempfile
import tarfile

from contextlib import closing

from flask import request, make_response, send_file

from data.database import configure

from config_app.c_app import app, config_provider
from config_app.config_endpoints.api import resource, ApiResource, nickname
from config_app.config_util.tar import (
    tarinfo_filter_partial,
    strip_absolute_path_and_add_trailing_dir,
)


@resource("/v1/configapp/initialization")
class ConfigInitialization(ApiResource):
    """
  Resource for dealing with any initialization logic for the config app
  """

    @nickname("scStartNewConfig")
    def post(self):
        config_provider.new_config_dir()
        return make_response("OK")


@resource("/v1/configapp/tarconfig")
class TarConfigLoader(ApiResource):
    """
  Resource for dealing with configuration as a tarball,
  including loading and generating functions
  """

    @nickname("scGetConfigTarball")
    def get(self):
        config_path = config_provider.get_config_dir_path()
        tar_dir_prefix = strip_absolute_path_and_add_trailing_dir(config_path)
        temp = tempfile.NamedTemporaryFile()

        with closing(tarfile.open(temp.name, mode="w|gz")) as tar:
            for name in os.listdir(config_path):
                tar.add(
                    os.path.join(config_path, name), filter=tarinfo_filter_partial(tar_dir_prefix)
                )
        return send_file(temp.name, mimetype="application/gzip")

    @nickname("scUploadTarballConfig")
    def put(self):
        """ Loads tarball config into the config provider """
        # Generate a new empty dir to load the config into
        config_provider.new_config_dir()
        input_stream = request.stream
        with tarfile.open(mode="r|gz", fileobj=input_stream) as tar_stream:
            tar_stream.extractall(config_provider.get_config_dir_path())

        config_provider.create_copy_of_config_dir()

        # now try to connect to the db provided in their config to validate it works
        combined = dict(**app.config)
        combined.update(config_provider.get_config())
        configure(combined)

        return make_response("OK")
