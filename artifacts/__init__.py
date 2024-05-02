import importlib
import pkgutil

from data.database import RepositoryKind
from flask import Blueprint
from artifacts import plugins
import sys
import logging

from artifacts.utils.registry_utils import QuayRegistryClient

logger = logging.getLogger(__name__)

current_module = sys.modules[__name__]
current_package = current_module.__package__

plugins_bp = Blueprint("artifacts", __name__)


def discover_plugins():
    # All plugins go in the `plugins` directory and
    # each plugin exposes the `plugin` variable in its
    # __init__.py file

    return {
        pkg.name: importlib.import_module(f'.plugins.{pkg.name}', package=current_package).plugin
        for pkg in pkgutil.iter_modules(plugins.__path__)
    }


def init_plugins(application):
    # TODO: check if plugin is enabled
    # TODO: pass plugin specific config

    discovered_plugins = discover_plugins()
    for plugin_obj in discovered_plugins.values():
        plugin_obj.register_routes(plugins_bp)
        RepositoryKind.get_or_create(name=plugin_obj.name)

    application.register_blueprint(plugins_bp, url_prefix='/artifacts')
