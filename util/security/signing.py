import gpg
import features
import logging

logger = logging.getLogger(__name__)

from io import BytesIO


class GPG2Signer(object):
    """
    Helper class for signing data using GPG2.
    """

    def __init__(self, config, config_provider):
        if not config.get("GPG2_PRIVATE_KEY_NAME"):
            raise Exception("Missing configuration key GPG2_PRIVATE_KEY_NAME")

        if not config.get("GPG2_PRIVATE_KEY_FILENAME"):
            raise Exception("Missing configuration key GPG2_PRIVATE_KEY_FILENAME")

        if not config.get("GPG2_PUBLIC_KEY_FILENAME"):
            raise Exception("Missing configuration key GPG2_PUBLIC_KEY_FILENAME")

        self._ctx = gpg.Context()
        self._ctx.armor = True
        self._private_key_name = config["GPG2_PRIVATE_KEY_NAME"]
        self._public_key_filename = config["GPG2_PUBLIC_KEY_FILENAME"]
        self._config_provider = config_provider

        if not config_provider.volume_file_exists(config["GPG2_PRIVATE_KEY_FILENAME"]):
            raise Exception("Missing key file %s" % config["GPG2_PRIVATE_KEY_FILENAME"])

        with config_provider.get_volume_file(config["GPG2_PRIVATE_KEY_FILENAME"], mode="rb") as fp:
            self._ctx.op_import(fp)

    @property
    def name(self):
        return "gpg2"

    def open_public_key_file(self):
        return self._config_provider.get_volume_file(self._public_key_filename, mode="rb")

    def detached_sign(self, stream):
        """
        Signs the given stream, returning the signature.
        """
        ctx = self._ctx
        try:
            ctx.signers = [ctx.get_key(self._private_key_name, 0)]
        except:
            raise Exception("Invalid private key name")

        signature = BytesIO()
        indata = gpg.core.Data(file=stream)
        outdata = gpg.core.Data(file=signature)
        ctx.op_sign(indata, outdata, gpg.constants.sig.DETACH)
        signature.seek(0)
        return signature.getvalue()


class Signer(object):
    def __init__(self, app=None, config_provider=None):
        self.app = app
        if app is not None:
            self.state = self.init_app(app, config_provider)
        else:
            self.state = None

    def init_app(self, app, config_provider):
        preference = app.config.get("SIGNING_ENGINE", None)
        if preference is None:
            return None

        if not features.ACI_CONVERSION:
            return None

        try:
            return SIGNING_ENGINES[preference](app.config, config_provider)
        except:
            logger.exception("Could not initialize signing engine")

    def __getattr__(self, name):
        return getattr(self.state, name, None)


SIGNING_ENGINES = {"gpg2": GPG2Signer}
