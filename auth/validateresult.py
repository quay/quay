from enum import Enum
from auth.auth_context_type import ValidatedAuthContext, ContextEntityKind


class AuthKind(Enum):
    cookie = "cookie"
    basic = "basic"
    oauth = "oauth"
    signed_grant = "signed_grant"
    credentials = "credentials"

    def __str__(self):
        return "%s" % self.value


class ValidateResult(object):
    """
    A result of validating auth in one form or another.
    """

    def __init__(
        self,
        kind,
        missing=False,
        user=None,
        token=None,
        oauthtoken=None,
        robot=None,
        appspecifictoken=None,
        signed_data=None,
        error_message=None,
    ):
        self.kind = kind
        self.missing = missing
        self.error_message = error_message
        self.context = ValidatedAuthContext(
            user=user,
            token=token,
            oauthtoken=oauthtoken,
            robot=robot,
            appspecifictoken=appspecifictoken,
            signed_data=signed_data,
        )

    def tuple(self):
        return (self.kind, self.missing, self.error_message, self.context.tuple())

    def __eq__(self, other):
        return self.tuple() == other.tuple()

    def apply_to_context(self):
        """
        Applies this auth result to the auth context and Flask-Principal.
        """
        self.context.apply_to_request_context()

    def with_kind(self, kind):
        """
        Returns a copy of this result, but with the kind replaced.
        """
        result = ValidateResult(kind, missing=self.missing, error_message=self.error_message)
        result.context = self.context
        return result

    def __repr__(self):
        return "ValidateResult: %s (missing: %s, error: %s)" % (
            self.kind,
            self.missing,
            self.error_message,
        )

    @property
    def authed_user(self):
        """
        Returns the authenticated user, whether directly, or via an OAuth token.
        """
        return self.context.authed_user

    @property
    def has_nonrobot_user(self):
        """
        Returns whether a user (not a robot) was authenticated successfully.
        """
        return self.context.has_nonrobot_user

    @property
    def auth_valid(self):
        """
        Returns whether authentication successfully occurred.
        """
        return self.context.entity_kind != ContextEntityKind.anonymous
