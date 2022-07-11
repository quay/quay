from singletons.app import _app
from singletons.config import app_config
from util.tufmetadata.api import TUFMetadataAPI

tuf_metadata_api = TUFMetadataAPI(_app, app_config)
