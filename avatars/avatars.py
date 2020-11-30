import hashlib
import math
import logging

from requests.exceptions import RequestException

from util.bytes import Bytes

logger = logging.getLogger(__name__)


class Avatar(object):
    def __init__(self, app=None):
        self.app = app
        self.state = self._init_app(app)

    def _init_app(self, app):
        return AVATAR_CLASSES[app.config.get("AVATAR_KIND", "Gravatar")](
            app.config["PREFERRED_URL_SCHEME"],
            app.config["AVATAR_COLORS"],
            app.config["HTTPCLIENT"],
        )

    def __getattr__(self, name):
        return getattr(self.state, name, None)


class BaseAvatar(object):
    """
    Base class for all avatar implementations.
    """

    def __init__(self, preferred_url_scheme, colors, http_client):
        self.preferred_url_scheme = preferred_url_scheme
        self.colors = colors
        self.http_client = http_client

    def get_mail_html(self, name, email_or_id, size=16, kind="user"):
        """
        Returns the full HTML and CSS for viewing the avatar of the given name and email address,
        with an optional size.
        """
        data = self.get_data(name, email_or_id, kind)
        url = self._get_url(data["hash"], size) if kind != "team" else None
        font_size = size - 6

        if url is not None:
            # Try to load the gravatar. If we get a non-404 response, then we use it in place of
            # the CSS avatar.
            try:
                response = self.http_client.get(url, timeout=5)
                if response.status_code == 200:
                    return """<img src="%s" width="%s" height="%s" alt="%s"
                         style="vertical-align: middle;">""" % (
                        url,
                        size,
                        size,
                        kind,
                    )
            except RequestException:
                logger.exception("Could not retrieve avatar for user %s", name)

        radius = "50%" if kind == "team" else "0%"
        letter = (
            "&Omega;" if kind == "team" and data["name"] == "owners" else data["name"].upper()[0]
        )

        return """
      <span style="width: %spx; height: %spx; background-color: %s; font-size: %spx;
                   line-height: %spx; margin-left: 2px; margin-right: 2px; display: inline-block;
                   vertical-align: middle; text-align: center; color: white; border-radius: %s">
        %s
      </span>
""" % (
            size,
            size,
            data["color"],
            font_size,
            size,
            radius,
            letter,
        )

    def get_data_for_user(self, user):
        return self.get_data(user.username, user.email, "robot" if user.robot else "user")

    def get_data_for_team(self, team):
        return self.get_data(team.name, team.name, "team")

    def get_data_for_org(self, org):
        return self.get_data(org.username, org.email, "org")

    def get_data_for_external_user(self, external_user):
        return self.get_data(external_user.username, external_user.email, "user")

    def get_data(self, name, email_or_id, kind="user"):
        """Computes and returns the full data block for the avatar:
        {
          'name': name,
          'hash': The gravatar hash, if any.
          'color': The color for the avatar
        }
        """
        colors = self.colors

        # Note: email_or_id may be None if gotten from external auth when email is disabled,
        # so use the username in that case.
        username_email_or_id = email_or_id or name
        username_email_or_id = Bytes.for_string_or_unicode(username_email_or_id).as_unicode()
        hash_value = hashlib.md5(username_email_or_id.strip().lower().encode("utf-8")).hexdigest()

        byte_count = int(math.ceil(math.log(len(colors), 16)))
        byte_data = hash_value[0:byte_count]
        hash_color = colors[int(byte_data, 16) % len(colors)]

        return {"name": name, "hash": hash_value, "color": hash_color, "kind": kind}

    def _get_url(self, hash_value, size):
        """
        Returns the URL for displaying the overlay avatar.
        """
        return None


class GravatarAvatar(BaseAvatar):
    """
    Avatar system that uses gravatar for generating avatars.
    """

    def _get_url(self, hash_value, size=16):
        return "%s://www.gravatar.com/avatar/%s?d=404&size=%s" % (
            self.preferred_url_scheme,
            hash_value,
            size,
        )


class LocalAvatar(BaseAvatar):
    """
    Avatar system that uses the local system for generating avatars.
    """

    pass


AVATAR_CLASSES = {"gravatar": GravatarAvatar, "local": LocalAvatar}
