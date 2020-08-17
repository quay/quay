"""
Provides helper methods and templates for generating cloud config for running containers.

Originally from https://github.com/DevTable/container-cloud-config
"""

from functools import partial

import base64
import json
import os
import requests
import logging

try:
    # Python 3
    from urllib.request import HTTPRedirectHandler, build_opener, install_opener, urlopen, Request
    from urllib.error import HTTPError
    from urllib.parse import quote as urlquote
except ImportError:
    # Python 2
    from urllib2 import (
        HTTPRedirectHandler,
        build_opener,
        install_opener,
        urlopen,
        Request,
        HTTPError,
    )
    from urllib import quote as urlquote

from jinja2 import FileSystemLoader, Environment, StrictUndefined

logger = logging.getLogger(__name__)


class CloudConfigContext(object):
    """ Context object for easy generating of cloud config. """

    def populate_jinja_environment(self, env):
        """ Populates the given jinja environment with the methods defined in this context. """
        env.filters["registry"] = self.registry
        env.filters["dataurl"] = self.data_url
        env.filters["jsonify"] = json.dumps
        env.globals["dockersystemd"] = self._dockersystemd_template

    def _dockersystemd_template(
        self,
        name,
        container,
        username="",
        password="",
        tag="latest",
        extra_args="",
        command="",
        after_units=[],
        exec_start_post=[],
        exec_stop_post=[],
        restart_policy="always",
        oneshot=False,
        env_file=None,
        onfailure_units=[],
        requires_units=[],
        wants_units=[],
        timeout_start_sec=600,
        timeout_stop_sec=2000,
        autostart=True,
    ):
        try:
            timeout_start_sec = int(timeout_start_sec)
            timeout_stop_sec = int(timeout_stop_sec)
        except (ValueError, TypeError):
            logger.error("Invalid timeouts (%s, %s): values should be integers",
                         timeout_start_sec,
                         timeout_stop_sec)
            raise

        path = os.path.join(os.path.dirname(__file__), "templates")
        env = Environment(loader=FileSystemLoader(path), undefined=StrictUndefined)
        self.populate_jinja_environment(env)
        template = env.get_template("dockersystemd.json")
        return template.render(
            name=name,
            container=container,
            username=username,
            password=password,
            tag=tag,
            extra_args=extra_args,
            command=command,
            after_units=after_units,
            requires_units=requires_units,
            wants_units=wants_units,
            onfailure_units=onfailure_units,
            exec_start_post=exec_start_post,
            exec_stop_post=exec_stop_post,
            restart_policy=restart_policy,
            oneshot=oneshot,
            autostart=autostart,
            timeout_start_sec=timeout_start_sec,
            timeout_stop_sec=timeout_stop_sec,
            env_file=env_file,
        )

    def data_url(self, content):
        """ Encodes the content of an ignition file using RFC 2397. """
        data = "," + urlquote(content)
        return "data:" + data


    def registry(self, container_name):
        """ Parse the registry from repositories of the following formats:
        quay.io/quay/quay:tagname -> quay.io
        localhost:5000/quay/quay:tagname -> localhost:5000
        localhost:5000/quay/quay -> localhost:5000
        quay/quay:latest -> ''
        quay/quay -> ''
        mysql:latest -> ''
        mysql -> ''
    """
        num_slashes = container_name.count("/")
        if num_slashes == 2:
            return container_name[: container_name.find("/")]
        else:
            return ""
