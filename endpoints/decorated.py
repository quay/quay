import logging

from flask import make_response, jsonify
from flask_restful.utils.cors import crossdomain

from app import app
from data import model
from data.readreplica import ReadOnlyModeException
from util.config.provider.baseprovider import CannotWriteConfigException
from util.useremails import CannotSendEmailException


logger = logging.getLogger(__name__)


@app.errorhandler(model.DataModelException)
def handle_dme(ex):
    logger.exception(ex)
    response = jsonify({"message": str(ex)})
    response.status_code = 400
    return response


@app.errorhandler(CannotSendEmailException)
def handle_emailexception(ex):
    message = "Could not send email. Please contact an administrator and report this problem."
    response = jsonify({"message": message})
    response.status_code = 400
    return response


@app.errorhandler(CannotWriteConfigException)
def handle_configexception(ex):
    message = (
        "Configuration could not be written to the mounted volume. \n"
        + "Please make sure the mounted volume is not read-only and restart "
        + "the setup process. \n\nIssue: %s" % ex
    )
    response = jsonify({"message": message})
    response.status_code = 400
    return response


@app.errorhandler(model.TooManyLoginAttemptsException)
@crossdomain(origin="*", headers=["Authorization", "Content-Type"])
def handle_too_many_login_attempts(error):
    msg = "Too many login attempts. \nPlease reset your Quay password and try again."
    response = make_response(msg, 429)
    response.headers["Retry-After"] = int(error.retry_after)
    return response


@app.errorhandler(ReadOnlyModeException)
def handle_readonly(ex):
    logger.exception(ex)
    response = jsonify(
        {
            "message": "System is currently read-only. Pulls will succeed but all "
            + "write operations are currently suspended.",
            "is_readonly": True,
        }
    )
    response.status_code = 503
    return response
