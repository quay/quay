from data import model


class DatabaseUsers(object):
    @property
    def federated_service(self):
        return None

    @property
    def supports_fresh_login(self):
        return True

    def ping(self):
        """
        Always assumed to be working.

        If the DB is broken, other checks will handle it.
        """
        return (True, None)

    @property
    def supports_encrypted_credentials(self):
        return True

    def has_password_set(self, username):
        user = model.user.get_user(username)
        return user and user.password_hash is not None

    @property
    def requires_distinct_cli_password(self):
        # Since the database stores its own password.
        return True

    def verify_credentials(self, username_or_email, password):
        """
        Simply delegate to the model implementation.
        """
        result = model.user.verify_user(username_or_email, password)
        if not result:
            return (None, "Invalid Username or Password")

        return (result, None)

    def verify_and_link_user(self, username_or_email, password):
        """
        Simply delegate to the model implementation.
        """
        return self.verify_credentials(username_or_email, password)

    def confirm_existing_user(self, username, password):
        return self.verify_credentials(username, password)

    def link_user(self, username_or_email):
        """
        Never used since all users being added are already, by definition, in the database.
        """
        return (None, "Unsupported for this authentication system")

    def get_and_link_federated_user_info(self, user_info, internal_create=False):
        """
        Never used since all users being added are already, by definition, in the database.
        """
        return (None, "Unsupported for this authentication system")

    def query_users(self, query, limit):
        """
        No need to implement, as we already query for users directly in the database.
        """
        return (None, "", "")

    def check_group_lookup_args(self, group_lookup_args):
        """
        Never used since all groups, by definition, are in the database.
        """
        return (False, "Not supported")

    def iterate_group_members(self, group_lookup_args, page_size=None, disable_pagination=False):
        """
        Never used since all groups, by definition, are in the database.
        """
        return (None, "Not supported")

    def service_metadata(self):
        """
        Never used since database has no metadata.
        """
        return {}
