import logging

from hashlib import sha1

from concurrent.futures import ThreadPoolExecutor
from marketorestpython.client import MarketoClient

from util.asyncwrapper import AsyncExecutorWrapper, NullExecutor, NullExecutorCancelled

logger = logging.getLogger(__name__)


class LeadNotFoundException(Exception):
    pass


def build_error_callback(message_when_exception):
    def maybe_log_error(response_future):
        try:
            response_future.result()
        except NullExecutorCancelled:
            pass
        except Exception:
            logger.exception("User analytics: %s", message_when_exception)

    return maybe_log_error


class _MarketoAnalyticsClient(object):
    """ User analytics implementation which will report user changes to the
      Marketo API.
  """

    def __init__(self, marketo_client, munchkin_private_key, lead_source):
        """ Instantiate with the given marketorestpython.client, the Marketo
        Munchkin Private Key, and the Lead Source that we want to set when we
        create new lead records in Marketo.
    """
        self._marketo = marketo_client
        self._munchkin_private_key = munchkin_private_key
        self._lead_source = lead_source

    def _get_lead_metadata(self, given_name, family_name, company, location):
        metadata = {}
        if given_name:
            metadata["firstName"] = given_name

        if family_name:
            metadata["lastName"] = family_name

        if company:
            metadata["company"] = company

        if location:
            metadata["location"] = location

        return metadata

    def create_lead(self, email, username, given_name, family_name, company, location):
        lead_data = dict(
            email=email,
            Quay_Username__c=username,
            leadSource="Web - Product Trial",
            Lead_Source_Detail__c=self._lead_source,
        )

        lead_data.update(self._get_lead_metadata(given_name, family_name, company, location))

        self._marketo.create_update_leads(
            action="createOrUpdate", leads=[lead_data], asyncProcessing=True, lookupField="email",
        )

    def _find_leads_by_email(self, email):
        # Fetch the existing user from the database by email
        found = self._marketo.get_multiple_leads_by_filter_type(
            filterType="email", filterValues=[email],
        )

        if not found:
            raise LeadNotFoundException("No lead found with email: {}".format(email))

        return found

    def change_email(self, old_email, new_email):
        found = self._find_leads_by_email(old_email)

        # Update using their user id.
        updated = [dict(id=lead["id"], email=new_email) for lead in found]
        self._marketo.create_update_leads(
            action="updateOnly", leads=updated, asyncProcessing=True, lookupField="id",
        )

    def change_metadata(
        self, email, given_name=None, family_name=None, company=None, location=None
    ):
        lead_data = self._get_lead_metadata(given_name, family_name, company, location)
        if not lead_data:
            return

        # Update using their email address.
        lead_data["email"] = email
        self._marketo.create_update_leads(
            action="updateOnly", leads=[lead_data], asyncProcessing=True, lookupField="email",
        )

    def change_username(self, email, new_username):
        # Update using their email.
        self._marketo.create_update_leads(
            action="updateOnly",
            leads=[{"email": email, "Quay_Username__c": new_username,}],
            asyncProcessing=True,
            lookupField="email",
        )

    @AsyncExecutorWrapper.sync
    def get_user_analytics_metadata(self, user_obj):
        """ Return a list of properties that should be added to the user object to allow
        analytics associations.
    """
        if not self._munchkin_private_key:
            return dict()

        marketo_user_hash = sha1(self._munchkin_private_key)
        marketo_user_hash.update(user_obj.email)

        return dict(marketo_user_hash=marketo_user_hash.hexdigest(),)


class UserAnalytics(object):
    def __init__(self, app=None):
        self.app = app
        if app is not None:
            self.state = self.init_app(app)
        else:
            self.state = None

    def init_app(self, app):
        analytics_type = app.config.get("USER_ANALYTICS_TYPE", "FakeAnalytics")

        marketo_munchkin_id = ""
        marketo_munchkin_private_key = ""
        marketo_client_id = ""
        marketo_client_secret = ""
        marketo_lead_source = ""
        executor = NullExecutor()

        if analytics_type == "Marketo":
            marketo_munchkin_id = app.config["MARKETO_MUNCHKIN_ID"]
            marketo_munchkin_private_key = app.config["MARKETO_MUNCHKIN_PRIVATE_KEY"]
            marketo_client_id = app.config["MARKETO_CLIENT_ID"]
            marketo_client_secret = app.config["MARKETO_CLIENT_SECRET"]
            marketo_lead_source = app.config["MARKETO_LEAD_SOURCE"]

            logger.debug(
                "Initializing marketo with keys: %s %s %s",
                marketo_munchkin_id,
                marketo_client_id,
                marketo_client_secret,
            )

            executor = ThreadPoolExecutor(max_workers=1)

        marketo_client = MarketoClient(
            marketo_munchkin_id, marketo_client_id, marketo_client_secret
        )
        client_wrapper = _MarketoAnalyticsClient(
            marketo_client, marketo_munchkin_private_key, marketo_lead_source
        )
        user_analytics = AsyncExecutorWrapper(client_wrapper, executor)

        # register extension with app
        app.extensions = getattr(app, "extensions", {})
        app.extensions["user_analytics"] = user_analytics
        return user_analytics

    def __getattr__(self, name):
        return getattr(self.state, name, None)
