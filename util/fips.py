from smtplib import SMTPException
from smtplib import SMTPAuthenticationError
from smtplib import SMTPNotSupportedError

# This method is the same as smtplib.SMTP.login except that CRAM_MD5 has been removed from preferred auths since MD5 is not FIPS compliant.
def login_fips_safe(self, user, password, *, initial_response_ok=True):
    """Log in on an SMTP server that requires authentication.
    The arguments are:
        - user:         The user name to authenticate with.
        - password:     The password for the authentication.
    Keyword arguments:
        - initial_response_ok: Allow sending the RFC 4954 initial-response
            to the AUTH command, if the authentication methods supports it.
    If there has been no previous EHLO or HELO command this session, this
    method tries ESMTP EHLO first.
    This method will return normally if the authentication was successful.
    This method may raise the following exceptions:
        SMTPHeloError            The server didn't reply properly to
                                the helo greeting.
        SMTPAuthenticationError  The server didn't accept the username/
                                password combination.
        SMTPNotSupportedError    The AUTH command is not supported by the
                                server.
        SMTPException            No suitable authentication method was
                                found.
    """

    self.ehlo_or_helo_if_needed()
    if not self.has_extn("auth"):
        raise SMTPNotSupportedError("SMTP AUTH extension not supported by server.")

    # Authentication methods the server claims to support
    advertised_authlist = self.esmtp_features["auth"].split()

    # Authentication methods we can handle in our preferred order:
    preferred_auths = ["PLAIN", "LOGIN"]

    # We try the supported authentications in our preferred order, if
    # the server supports them.
    authlist = [auth for auth in preferred_auths if auth in advertised_authlist]
    if not authlist:
        raise SMTPException("No suitable authentication method found.")

    # Some servers advertise authentication methods they don't really
    # support, so if authentication fails, we continue until we've tried
    # all methods.
    self.user, self.password = user, password
    for authmethod in authlist:
        method_name = "auth_" + authmethod.lower().replace("-", "_")
        try:
            (code, resp) = self.auth(
                authmethod, getattr(self, method_name), initial_response_ok=initial_response_ok
            )
            # 235 == 'Authentication successful'
            # 503 == 'Error: already authenticated'
            if code in (235, 503):
                return (code, resp)
        except SMTPAuthenticationError as e:
            last_exception = e

    # We could not login successfully.  Return result of last attempt.
    raise last_exception
