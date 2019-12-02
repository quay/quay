import logging

from flask import abort, request

from config_app.config_endpoints.api.suconfig_models_pre_oci import pre_oci_model as model
from config_app.config_endpoints.api import resource, ApiResource, nickname, validate_json_request
from config_app.c_app import (
    app,
    config_provider,
    superusers,
    ip_resolver,
    instance_keys,
    INIT_SCRIPTS_LOCATION,
)

from data.database import configure
from data.runmigration import run_alembic_migration
from util.config.configutil import add_enterprise_config_defaults
from util.config.validator import (
    validate_service_for_config,
    ValidatorContext,
    is_valid_config_upload_filename,
)

logger = logging.getLogger(__name__)


def database_is_valid():
    """ Returns whether the database, as configured, is valid. """
    return model.is_valid()


def database_has_users():
    """ Returns whether the database has any users defined. """
    return model.has_users()


@resource("/v1/superuser/config")
class SuperUserConfig(ApiResource):
    """ Resource for fetching and updating the current configuration, if any. """

    schemas = {
        "UpdateConfig": {
            "type": "object",
            "description": "Updates the YAML config file",
            "required": ["config",],
            "properties": {"config": {"type": "object"}, "password": {"type": "string"},},
        },
    }

    @nickname("scGetConfig")
    def get(self):
        """ Returns the currently defined configuration, if any. """
        config_object = config_provider.get_config()
        return {"config": config_object}

    @nickname("scUpdateConfig")
    @validate_json_request("UpdateConfig")
    def put(self):
        """ Updates the config override file. """
        # Note: This method is called to set the database configuration before super users exists,
        # so we also allow it to be called if there is no valid registry configuration setup.
        config_object = request.get_json()["config"]

        # Add any enterprise defaults missing from the config.
        add_enterprise_config_defaults(config_object, app.config["SECRET_KEY"])

        # Write the configuration changes to the config override file.
        config_provider.save_config(config_object)

        # now try to connect to the db provided in their config to validate it works
        combined = dict(**app.config)
        combined.update(config_provider.get_config())
        configure(combined, testing=app.config["TESTING"])

        return {"exists": True, "config": config_object}


@resource("/v1/superuser/registrystatus")
class SuperUserRegistryStatus(ApiResource):
    """ Resource for determining the status of the registry, such as if config exists,
      if a database is configured, and if it has any defined users.
  """

    @nickname("scRegistryStatus")
    def get(self):
        """ Returns the status of the registry. """
        # If there is no config file, we need to setup the database.
        if not config_provider.config_exists():
            return {"status": "config-db"}

        # If the database isn't yet valid, then we need to set it up.
        if not database_is_valid():
            return {"status": "setup-db"}

        config = config_provider.get_config()
        if config and config.get("SETUP_COMPLETE"):
            return {"status": "config"}

        return {"status": "create-superuser" if not database_has_users() else "config"}


class _AlembicLogHandler(logging.Handler):
    def __init__(self):
        super(_AlembicLogHandler, self).__init__()
        self.records = []

    def emit(self, record):
        self.records.append({"level": record.levelname, "message": record.getMessage()})


def _reload_config():
    combined = dict(**app.config)
    combined.update(config_provider.get_config())
    configure(combined)
    return combined


@resource("/v1/superuser/setupdb")
class SuperUserSetupDatabase(ApiResource):
    """ Resource for invoking alembic to setup the database. """

    @nickname("scSetupDatabase")
    def get(self):
        """ Invokes the alembic upgrade process. """
        # Note: This method is called after the database configured is saved, but before the
        # database has any tables. Therefore, we only allow it to be run in that unique case.
        if config_provider.config_exists() and not database_is_valid():
            combined = _reload_config()

            app.config["DB_URI"] = combined["DB_URI"]
            db_uri = app.config["DB_URI"]
            escaped_db_uri = db_uri.replace("%", "%%")

            log_handler = _AlembicLogHandler()

            try:
                run_alembic_migration(escaped_db_uri, log_handler, setup_app=False)
            except Exception as ex:
                return {"error": str(ex)}

            return {"logs": log_handler.records}

        abort(403)


@resource("/v1/superuser/config/createsuperuser")
class SuperUserCreateInitialSuperUser(ApiResource):
    """ Resource for creating the initial super user. """

    schemas = {
        "CreateSuperUser": {
            "type": "object",
            "description": "Information for creating the initial super user",
            "required": ["username", "password", "email"],
            "properties": {
                "username": {"type": "string", "description": "The username for the superuser"},
                "password": {"type": "string", "description": "The password for the superuser"},
                "email": {"type": "string", "description": "The e-mail address for the superuser"},
            },
        },
    }

    @nickname("scCreateInitialSuperuser")
    @validate_json_request("CreateSuperUser")
    def post(self):
        """ Creates the initial super user, updates the underlying configuration and
        sets the current session to have that super user. """

        _reload_config()

        # Special security check: This method is only accessible when:
        #   - There is a valid config YAML file.
        #   - There are currently no users in the database (clean install)
        #
        # We do this special security check because at the point this method is called, the database
        # is clean but does not (yet) have any super users for our permissions code to check against.
        if config_provider.config_exists() and not database_has_users():
            data = request.get_json()
            username = data["username"]
            password = data["password"]
            email = data["email"]

            # Create the user in the database.
            superuser_uuid = model.create_superuser(username, password, email)

            # Add the user to the config.
            config_object = config_provider.get_config()
            config_object["SUPER_USERS"] = [username]
            config_provider.save_config(config_object)

            # Update the in-memory config for the new superuser.
            superusers.register_superuser(username)

            return {"status": True}

        abort(403)


@resource("/v1/superuser/config/validate/<service>")
class SuperUserConfigValidate(ApiResource):
    """ Resource for validating a block of configuration against an external service. """

    schemas = {
        "ValidateConfig": {
            "type": "object",
            "description": "Validates configuration",
            "required": ["config"],
            "properties": {
                "config": {"type": "object"},
                "password": {
                    "type": "string",
                    "description": "The users password, used for auth validation",
                },
            },
        },
    }

    @nickname("scValidateConfig")
    @validate_json_request("ValidateConfig")
    def post(self, service):
        """ Validates the given config for the given service. """
        # Note: This method is called to validate the database configuration before super users exists,
        # so we also allow it to be called if there is no valid registry configuration setup. Note that
        # this is also safe since this method does not access any information not given in the request.
        config = request.get_json()["config"]
        validator_context = ValidatorContext.from_app(
            app,
            config,
            request.get_json().get("password", ""),
            instance_keys=instance_keys,
            ip_resolver=ip_resolver,
            config_provider=config_provider,
            init_scripts_location=INIT_SCRIPTS_LOCATION,
        )

        return validate_service_for_config(service, validator_context)


@resource("/v1/superuser/config/file/<filename>")
class SuperUserConfigFile(ApiResource):
    """ Resource for fetching the status of config files and overriding them. """

    @nickname("scConfigFileExists")
    def get(self, filename):
        """ Returns whether the configuration file with the given name exists. """
        if not is_valid_config_upload_filename(filename):
            abort(404)

        return {"exists": config_provider.volume_file_exists(filename)}

    @nickname("scUpdateConfigFile")
    def post(self, filename):
        """ Updates the configuration file with the given name. """
        if not is_valid_config_upload_filename(filename):
            abort(404)

        # Note: This method can be called before the configuration exists
        # to upload the database SSL cert.
        uploaded_file = request.files["file"]
        if not uploaded_file:
            abort(400)

        config_provider.save_volume_file(filename, uploaded_file)
        return {"status": True}
