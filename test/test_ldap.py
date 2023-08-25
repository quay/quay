import unittest
from contextlib import contextmanager

import ldap
from ldap.filter import filter_format
from mock import patch
from mockldap import MockLdap

from app import app
from data import model
from data.users import LDAPUsers
from initdb import finished_database_for_testing, setup_database_for_testing


def _create_ldap(
    requires_email=True, user_filter=None, superuser_filter=None, restricted_user_filter=None
):
    base_dn = ["dc=quay", "dc=io"]
    admin_dn = "uid=testy,ou=employees,dc=quay,dc=io"
    admin_passwd = "password"
    user_rdn = ["ou=employees"]
    uid_attr = "uid"
    email_attr = "mail"
    secondary_user_rdns = ["ou=otheremployees"]

    ldap = LDAPUsers(
        "ldap://localhost",
        base_dn,
        admin_dn,
        admin_passwd,
        user_rdn,
        uid_attr,
        email_attr,
        secondary_user_rdns=secondary_user_rdns,
        requires_email=requires_email,
        ldap_user_filter=user_filter,
        ldap_superuser_filter=superuser_filter,
        ldap_restricted_user_filter=restricted_user_filter,
    )
    return ldap


@contextmanager
def mock_ldap(
    requires_email=True, user_filter=None, superuser_filter=None, restricted_user_filter=None
):
    mock_data = {
        "dc=quay,dc=io": {"dc": ["quay", "io"]},
        "ou=employees,dc=quay,dc=io": {"dc": ["quay", "io"], "ou": "employees"},
        "ou=otheremployees,dc=quay,dc=io": {"dc": ["quay", "io"], "ou": "otheremployees"},
        "cn=AwesomeFolk,dc=quay,dc=io": {"dc": ["quay", "io"], "cn": "AwesomeFolk"},
        "uid=testy,ou=employees,dc=quay,dc=io": {
            "dc": ["quay", "io"],
            "ou": "employees",
            "uid": ["testy"],
            "userPassword": ["password"],
            "mail": ["bar@baz.com"],
            "memberOf": ["cn=AwesomeFolk,dc=quay,dc=io", "cn=*Guys,dc=quay,dc=io"],
            "filterField": ["somevalue"],
            "objectClass": "user",
        },
        "uid=someuser,ou=employees,dc=quay,dc=io": {
            "dc": ["quay", "io"],
            "ou": "employees",
            "uid": ["someuser"],
            "userPassword": ["somepass"],
            "mail": ["foo@bar.com"],
            "memberOf": ["cn=AwesomeFolk,dc=quay,dc=io", "cn=*Guys,dc=quay,dc=io"],
            "filterField": ["somevalue"],
            "objectClass": "user",
        },
        "uid=nomail,ou=employees,dc=quay,dc=io": {
            "dc": ["quay", "io"],
            "ou": "employees",
            "uid": ["nomail"],
            "userPassword": ["somepass"],
            "filterField": ["somevalue"],
        },
        "uid=bytesuser,ou=employees,dc=quay,dc=io": {
            "dc": ["quay", "io"],
            "ou": "employees",
            "uid": ["bytesuser"],
            "userPassword": ["somepass"],
            "mail": [b"bytes@bar.com"],
            "filterField": ["somevalue"],
        },
        "uid=cool.user,ou=employees,dc=quay,dc=io": {
            "dc": ["quay", "io"],
            "ou": "employees",
            "uid": ["cool.user", "referred"],
            "userPassword": ["somepass"],
            "mail": ["foo@bar.com"],
            "filterField": ["somevalue"],
            "objectClass": "user",
        },
        "uid=referred,ou=employees,dc=quay,dc=io": {
            "uid": ["referred"],
            "_referral": "ldap:///uid=cool.user,ou=employees,dc=quay,dc=io",
        },
        "uid=invalidreferred,ou=employees,dc=quay,dc=io": {
            "uid": ["invalidreferred"],
            "_referral": "ldap:///uid=someinvaliduser,ou=employees,dc=quay,dc=io",
        },
        "uid=multientry,ou=subgroup1,ou=employees,dc=quay,dc=io": {
            "uid": ["multientry"],
            "mail": ["foo@bar.com"],
            "userPassword": ["somepass"],
            "filterField": ["somevalue"],
            "objectClass": "user",
        },
        "uid=multientry,ou=subgroup2,ou=employees,dc=quay,dc=io": {
            "uid": ["multientry"],
            "another": ["key"],
            "filterField": ["somevalue"],
            "objectClass": "user",
        },
        "uid=secondaryuser,ou=otheremployees,dc=quay,dc=io": {
            "dc": ["quay", "io"],
            "ou": "otheremployees",
            "uid": ["secondaryuser"],
            "userPassword": ["somepass"],
            "mail": ["foosecondary@bar.com"],
            "filterField": ["somevalue"],
            "objectClass": "user",
        },
        # Feature: Email Blacklisting
        "uid=blacklistedcom,ou=otheremployees,dc=quay,dc=io": {
            "dc": ["quay", "io"],
            "ou": "otheremployees",
            "uid": ["blacklistedcom"],
            "userPassword": ["somepass"],
            "mail": ["foo@blacklisted.com"],
            "filterField": ["somevalue"],
            "objectClass": "user",
        },
        "uid=blacklistednet,ou=otheremployees,dc=quay,dc=io": {
            "dc": ["quay", "io"],
            "ou": "otheremployees",
            "uid": ["blacklistednet"],
            "userPassword": ["somepass"],
            "mail": ["foo@blacklisted.net"],
            "filterField": ["somevalue"],
            "objectClass": "user",
        },
        "uid=blacklistedorg,ou=otheremployees,dc=quay,dc=io": {
            "dc": ["quay", "io"],
            "ou": "otheremployees",
            "uid": ["blacklistedorg"],
            "userPassword": ["somepass"],
            "mail": ["foo@blacklisted.org"],
            "filterField": ["somevalue"],
            "objectClass": "user",
        },
        "uid=notblacklistedcom,ou=otheremployees,dc=quay,dc=io": {
            "dc": ["quay", "io"],
            "ou": "otheremployees",
            "uid": ["notblacklistedcom"],
            "userPassword": ["somepass"],
            "mail": ["foo@notblacklisted.com"],
            "filterField": ["somevalue"],
            "objectClass": "user",
        },
        "uid=somesuperuser,ou=employees,dc=quay,dc=io": {
            "dc": ["quay", "io"],
            "ou": "employees",
            "uid": ["somesuperuser"],
            "userPassword": ["somesuperpass"],
            "mail": ["superfoo@bar.com"],
            "memberOf": ["cn=AwesomeFolk,dc=quay,dc=io", "cn=*Guys,dc=quay,dc=io"],
            "filterField": ["somevalue", "superuser"],
            "objectClass": "user",
        },
        "uid=somerestricteduser,ou=employees,dc=quay,dc=io": {
            "dc": ["quay", "io"],
            "ou": "employees",
            "uid": ["somerestricteduser"],
            "userPassword": ["somerestrictedpass"],
            "mail": ["restrictedfoo@bar.com"],
            "memberOf": ["cn=AwesomeFolk,dc=quay,dc=io", "cn=*Guys,dc=quay,dc=io"],
            "filterField": ["somevalue", "restricted"],
            "objectClass": "user",
        },
    }

    if not requires_email:
        for path in mock_data:
            mock_data[path].pop("mail", None)

    mockldap = MockLdap(mock_data)

    def initializer(uri, trace_level=0, bytes_mode=False):
        obj = mockldap[uri]

        # Seed to "support" wildcard queries, which MockLDAP does not support natively.
        cool_block = {
            "dc": ["quay", "io"],
            "ou": "employees",
            "uid": ["cool.user", "referred"],
            "userPassword": ["somepass"],
            "mail": ["foo@bar.com"],
        }

        if not requires_email:
            cool_block.pop("mail", None)

        obj.search_s.seed("ou=employees,dc=quay,dc=io", 2, "(|(uid=cool*)(mail=cool*))")(
            [("uid=cool.user,ou=employees,dc=quay,dc=io", cool_block)]
        )

        obj.search_s.seed("ou=otheremployees,dc=quay,dc=io", 2, "(|(uid=cool*)(mail=cool*))")([])

        obj.search_s.seed("ou=employees,dc=quay,dc=io", 2, "(|(uid=unknown*)(mail=unknown*))")([])
        obj.search_s.seed("ou=otheremployees,dc=quay,dc=io", 2, "(|(uid=unknown*)(mail=unknown*))")(
            []
        )

        no_users_found_exception = Exception()
        no_users_found_exception.message = {"matched": "dc=quay,dc=io", "desc": "No such object"}

        obj.search_s.seed("ou=nonexistent,dc=quay,dc=io", 2)(no_users_found_exception)
        obj.search_s.seed("ou=employees,dc=quay,dc=io", 2)(
            [("uid=cool.user,ou=employees,dc=quay,dc=io", cool_block)]
        )
        obj.search.seed("ou=employees,dc=quay,dc=io", 2, "(objectClass=*)")(
            [("uid=cool.user,ou=employees,dc=quay,dc=io", cool_block)]
        )
        obj.search.seed("ou=employees,dc=quay,dc=io", 2)(
            [("uid=cool.user,ou=employees,dc=quay,dc=io", cool_block)]
        )

        obj._results = {}
        original_result_fn = obj.result

        def result(messageid):
            if messageid is None:
                return None, [], None, None

            # NOTE: Added because of weirdness with using mock-ldap.
            if isinstance(messageid, list):
                return None, messageid

            if messageid in obj._results:
                return obj._results[messageid]

            return original_result_fn(messageid)

        def result3(messageid):
            if messageid is None:
                return None, [], None, None

            return obj._results[messageid]

        def search_ext(
            user_search_dn, scope, search_flt=None, serverctrls=None, sizelimit=None, attrlist=None
        ):
            if scope != ldap.SCOPE_SUBTREE:
                return None

            if not serverctrls:
                if search_flt:
                    rdata = obj.search_s(user_search_dn, scope, search_flt, attrlist=attrlist)
                else:
                    if attrlist:
                        rdata = obj.search_s(user_search_dn, scope, attrlist=attrlist)
                    else:
                        rdata = obj.search_s(user_search_dn, scope)

                obj._results["messageid"] = (None, rdata)
                return "messageid"

            page_control = serverctrls[0]
            if page_control.controlType != ldap.controls.SimplePagedResultsControl.controlType:
                return None

            if search_flt:
                msgid = obj.search(user_search_dn, scope, search_flt, attrlist=attrlist)
            else:
                if attrlist:
                    msgid = obj.search(user_search_dn, scope, attrlist=attrlist)
                else:
                    msgid = obj.search(user_search_dn, scope)

            _, rdata = obj.result(msgid)
            msgid = "messageid"
            cookie = int(page_control.cookie) if page_control.cookie else 0

            results = rdata[cookie : cookie + page_control.size]
            cookie = cookie + page_control.size
            if cookie > len(results):
                page_control.cookie = None
            else:
                page_control.cookie = cookie

            obj._results["messageid"] = (None, results, None, [page_control])
            return msgid

        def search_ext_s(user_search_dn, scope, sizelimit=None):
            return [obj.search_s(user_search_dn, scope)]

        obj.search_ext = search_ext
        obj.result = result
        obj.result3 = result3
        obj.search_ext_s = search_ext_s

        return obj

    mockldap.start()
    try:
        with patch("ldap.initialize", new=initializer):
            yield _create_ldap(
                requires_email=requires_email,
                user_filter=user_filter,
                superuser_filter=superuser_filter,
                restricted_user_filter=restricted_user_filter,
            )
    finally:
        mockldap.stop()


class TestLDAP(unittest.TestCase):
    def setUp(self):
        setup_database_for_testing(self)
        self.app = app.test_client()
        self.ctx = app.test_request_context()
        self.ctx.__enter__()

    def tearDown(self):
        finished_database_for_testing(self)
        self.ctx.__exit__(True, None, None)

    def test_invalid_admin_password(self):
        base_dn = ["dc=quay", "dc=io"]
        admin_dn = "uid=testy,ou=employees,dc=quay,dc=io"
        admin_passwd = "INVALIDPASSWORD"
        user_rdn = ["ou=employees"]
        uid_attr = "uid"
        email_attr = "mail"

        with mock_ldap():
            ldap = LDAPUsers(
                "ldap://localhost", base_dn, admin_dn, admin_passwd, user_rdn, uid_attr, email_attr
            )

            # Try to login.
            (response, err_msg) = ldap.verify_and_link_user("someuser", "somepass")
            self.assertIsNone(response)
            self.assertEqual("LDAP Admin dn or password is invalid", err_msg)

    def test_login(self):
        with mock_ldap() as ldap:
            # Verify we can login.
            (response, _) = ldap.verify_and_link_user("someuser", "somepass")
            self.assertEqual(response.username, "someuser")
            self.assertTrue(model.user.has_user_prompt(response, "confirm_username"))

            # Verify we can confirm the user.
            (response, _) = ldap.confirm_existing_user("someuser", "somepass")
            self.assertEqual(response.username, "someuser")

    def test_login_empty_password(self):
        with mock_ldap() as ldap:
            # Verify we cannot login.
            (response, err_msg) = ldap.verify_and_link_user("someuser", "")
            self.assertIsNone(response)
            self.assertEqual(err_msg, "Anonymous binding not allowed.")

            # Verify we cannot confirm the user.
            (response, err_msg) = ldap.confirm_existing_user("someuser", "")
            self.assertIsNone(response)
            self.assertEqual(err_msg, "Invalid username or password.")

    def test_login_whitespace_password(self):
        with mock_ldap() as ldap:
            # Verify we cannot login.
            (response, err_msg) = ldap.verify_and_link_user("someuser", "    ")
            self.assertIsNone(response)
            self.assertEqual(err_msg, "Invalid username or password.")

            # Verify we cannot confirm the user.
            (response, err_msg) = ldap.confirm_existing_user("someuser", "    ")
            self.assertIsNone(response)
            self.assertEqual(err_msg, "Invalid username or password.")

    def test_login_secondary(self):
        with mock_ldap() as ldap:
            # Verify we can login.
            (response, _) = ldap.verify_and_link_user("secondaryuser", "somepass")
            self.assertEqual(response.username, "secondaryuser")

            # Verify we can confirm the user.
            (response, _) = ldap.confirm_existing_user("secondaryuser", "somepass")
            self.assertEqual(response.username, "secondaryuser")

    def test_invalid_wildcard(self):
        with mock_ldap() as ldap:
            # Verify we cannot login with a wildcard.
            (response, err_msg) = ldap.verify_and_link_user("some*", "somepass")
            self.assertIsNone(response)
            self.assertEqual(err_msg, "Invalid username or password.")

            # Verify we cannot confirm the user.
            (response, err_msg) = ldap.confirm_existing_user("some*", "somepass")
            self.assertIsNone(response)
            self.assertEqual(err_msg, "Invalid username or password.")

    def test_invalid_password(self):
        with mock_ldap() as ldap:
            # Verify we cannot login with an invalid password.
            (response, err_msg) = ldap.verify_and_link_user("someuser", "invalidpass")
            self.assertIsNone(response)
            self.assertEqual(err_msg, "Invalid username or password.")

            # Verify we cannot confirm the user.
            (response, err_msg) = ldap.confirm_existing_user("someuser", "invalidpass")
            self.assertIsNone(response)
            self.assertEqual(err_msg, "Invalid username or password.")

    def test_missing_mail(self):
        with mock_ldap() as ldap:
            (response, err_msg) = ldap.get_user("nomail")
            self.assertIsNone(response)
            self.assertEqual('Missing mail field "mail" in user record', err_msg)

    def test_missing_mail_allowed(self):
        with mock_ldap(requires_email=False) as ldap:
            (response, _) = ldap.get_user("nomail")
            self.assertEqual(response.username, "nomail")

    def test_bytes_in_results(self):
        with mock_ldap() as ldap:
            (response, _) = ldap.get_user("bytesuser")
            self.assertEqual(response.username, "bytesuser")

    def test_confirm_different_username(self):
        with mock_ldap() as ldap:
            # Verify that the user is logged in and their username was adjusted.
            (response, _) = ldap.verify_and_link_user("cool.user", "somepass")
            self.assertEqual(response.username, "cool_user")

            # Verify we can confirm the user's quay username.
            (response, _) = ldap.confirm_existing_user("cool_user", "somepass")
            self.assertEqual(response.username, "cool_user")

            # Verify that we *cannot* confirm the LDAP username.
            (response, _) = ldap.confirm_existing_user("cool.user", "somepass")
            self.assertIsNone(response)

    def test_referral(self):
        with mock_ldap() as ldap:
            (response, _) = ldap.verify_and_link_user("referred", "somepass")
            self.assertEqual(response.username, "cool_user")

            # Verify we can confirm the user's quay username.
            (response, _) = ldap.confirm_existing_user("cool_user", "somepass")
            self.assertEqual(response.username, "cool_user")

    def test_invalid_referral(self):
        with mock_ldap() as ldap:
            (response, _) = ldap.verify_and_link_user("invalidreferred", "somepass")
            self.assertIsNone(response)

    def test_multientry(self):
        with mock_ldap() as ldap:
            (response, _) = ldap.verify_and_link_user("multientry", "somepass")
            self.assertEqual(response.username, "multientry")

    def test_login_empty_userdn(self):
        with mock_ldap():
            base_dn = ["ou=employees", "dc=quay", "dc=io"]
            admin_dn = "uid=testy,ou=employees,dc=quay,dc=io"
            admin_passwd = "password"
            user_rdn = []
            uid_attr = "uid"
            email_attr = "mail"
            secondary_user_rdns = ["ou=otheremployees"]

            ldap = LDAPUsers(
                "ldap://localhost",
                base_dn,
                admin_dn,
                admin_passwd,
                user_rdn,
                uid_attr,
                email_attr,
                secondary_user_rdns=secondary_user_rdns,
            )

            # Verify we can login.
            (response, _) = ldap.verify_and_link_user("someuser", "somepass")
            self.assertEqual(response.username, "someuser")

            # Verify we can confirm the user.
            (response, _) = ldap.confirm_existing_user("someuser", "somepass")
            self.assertEqual(response.username, "someuser")

    def test_link_user(self):
        with mock_ldap() as ldap:
            # Link someuser.
            user, error_message = ldap.link_user("someuser")
            self.assertIsNone(error_message)
            self.assertIsNotNone(user)
            self.assertEqual("someuser", user.username)

            # Link again. Should return the same user record.
            user_again, _ = ldap.link_user("someuser")
            self.assertEqual(user_again.id, user.id)

            # Confirm someuser.
            result, _ = ldap.confirm_existing_user("someuser", "somepass")
            self.assertIsNotNone(result)
            self.assertEqual("someuser", result.username)
            self.assertTrue(model.user.has_user_prompt(user, "confirm_username"))

    def test_query(self):
        with mock_ldap() as ldap:
            # Lookup cool.
            (response, federated_id, error_message) = ldap.query_users("cool")
            self.assertIsNone(error_message)
            self.assertEqual(1, len(response))
            self.assertEqual("ldap", federated_id)

            user_info = response[0]
            self.assertEqual("cool.user", user_info.username)
            self.assertEqual("foo@bar.com", user_info.email)

            # Lookup unknown.
            (response, federated_id, error_message) = ldap.query_users("unknown")
            self.assertIsNone(error_message)
            self.assertEqual(0, len(response))
            self.assertEqual("ldap", federated_id)

    def test_timeout(self):
        base_dn = ["dc=quay", "dc=io"]
        admin_dn = "uid=testy,ou=employees,dc=quay,dc=io"
        admin_passwd = "password"
        user_rdn = ["ou=employees"]
        uid_attr = "uid"
        email_attr = "mail"
        secondary_user_rdns = ["ou=otheremployees"]

        with self.assertRaisesRegex(Exception, "Can't contact LDAP server"):
            ldap = LDAPUsers(
                "ldap://localhost",
                base_dn,
                admin_dn,
                admin_passwd,
                user_rdn,
                uid_attr,
                email_attr,
                secondary_user_rdns=secondary_user_rdns,
                requires_email=False,
                timeout=5,
            )
            ldap.query_users("cool")

    def test_iterate_group_members(self):
        with mock_ldap() as ldap:
            (it, err) = ldap.iterate_group_members(
                {"group_dn": "cn=AwesomeFolk"}, disable_pagination=True
            )
            self.assertIsNone(err)

            results = list(it)
            self.assertEqual(4, len(results))

            first = results[0][0]
            second = results[1][0]
            third = results[2][0]
            fourth = results[3][0]

            assert all(
                x in [u[0].id for u in results]
                for x in ["testy", "someuser", "somesuperuser", "somerestricteduser"]
            )

            for i in results:
                u = i[0]
                if u.id == "testy":
                    self.assertEqual("testy", u.id)
                    self.assertEqual("testy", u.username)
                    self.assertEqual("bar@baz.com", u.email)

                if u.id == "someuser":
                    self.assertEqual("someuser", u.id)
                    self.assertEqual("someuser", u.username)
                    self.assertEqual("foo@bar.com", u.email)

                if u.id == "somesuperuser":
                    self.assertEqual("somesuperuser", u.id)
                    self.assertEqual("somesuperuser", u.username)
                    self.assertEqual("superfoo@bar.com", u.email)

                if u.id == "somerestricteduser":
                    self.assertEqual("somerestricteduser", u.id)
                    self.assertEqual("somerestricteduser", u.username)
                    self.assertEqual("restrictedfoo@bar.com", u.email)

    def test_iterate_group_members_with_pagination(self):
        with mock_ldap() as ldap:
            for dn in ["cn=AwesomeFolk", "cn=*Guys"]:
                (it, err) = ldap.iterate_group_members({"group_dn": dn}, page_size=1)
                self.assertIsNone(err)

                results = list(it)
                self.assertEqual(2, len(results))

                first = results[0][0]
                second = results[1][0]

                if first.id == "testy":
                    testy, someuser = first, second
                else:
                    testy, someuser = second, first

                self.assertEqual("testy", testy.id)
                self.assertEqual("testy", testy.username)
                self.assertEqual("bar@baz.com", testy.email)

                self.assertEqual("someuser", someuser.id)
                self.assertEqual("someuser", someuser.username)
                self.assertEqual("foo@bar.com", someuser.email)

    def test_check_group_lookup_args(self):
        with mock_ldap() as ldap:
            (result, err) = ldap.check_group_lookup_args(
                {"group_dn": "cn=invalid"}, disable_pagination=True
            )
            self.assertFalse(result)
            self.assertIsNotNone(err)

            (result, err) = ldap.check_group_lookup_args(
                {"group_dn": "cn=AwesomeFolk"}, disable_pagination=True
            )
            self.assertTrue(result)
            self.assertIsNone(err)

            (result, err) = ldap.check_group_lookup_args(
                {"group_dn": "cn=*Guys"}, disable_pagination=True
            )
            self.assertTrue(result)
            self.assertIsNone(err)

    def test_metadata(self):
        with mock_ldap() as ldap:
            assert "base_dn" in ldap.service_metadata()

    def test_at_least_one_user_exists_invalid_creds(self):
        base_dn = ["dc=quay", "dc=io"]
        admin_dn = "uid=testy,ou=employees,dc=quay,dc=io"
        admin_passwd = "INVALIDPASSWORD"
        user_rdn = ["ou=employees"]
        uid_attr = "uid"
        email_attr = "mail"

        with mock_ldap():
            ldap = LDAPUsers(
                "ldap://localhost", base_dn, admin_dn, admin_passwd, user_rdn, uid_attr, email_attr
            )

            # Try to query with invalid credentials.
            (response, err_msg) = ldap.at_least_one_user_exists()
            self.assertFalse(response)
            self.assertEqual("LDAP Admin dn or password is invalid", err_msg)

    def test_at_least_one_user_exists_no_users(self):
        base_dn = ["dc=quay", "dc=io"]
        admin_dn = "uid=testy,ou=employees,dc=quay,dc=io"
        admin_passwd = "password"
        user_rdn = ["ou=nonexistent"]
        uid_attr = "uid"
        email_attr = "mail"

        with mock_ldap():
            ldap = LDAPUsers(
                "ldap://localhost", base_dn, admin_dn, admin_passwd, user_rdn, uid_attr, email_attr
            )

            # Try to find users in a nonexistent group.
            (response, err_msg) = ldap.at_least_one_user_exists()
            self.assertFalse(response)
            assert err_msg is not None

    def test_at_least_one_user_exists_true(self):
        with mock_ldap() as ldap:
            # Ensure we have at least a single user in the valid group
            (response, err_msg) = ldap.at_least_one_user_exists()
            self.assertIsNone(err_msg)
            self.assertTrue(response)

    def test_ldap_user_filter_format(self):
        some_user_filter = "(filterField=somevalue)"
        with mock_ldap(user_filter=some_user_filter) as ldap:
            search_flt = filter_format("(memberOf=%s,%s)", ("cn=AwesomeFolk", ldap._base_dn))
            search_flt = ldap._add_user_filter(search_flt)
            self.assertEqual(
                search_flt, "(&(memberOf=cn=AwesomeFolk,dc=quay,dc=io)(filterField=somevalue))"
            )

        some_other_user_filter = some_user_filter + "(filterField2=someothervalue)"
        with mock_ldap(user_filter=some_other_user_filter) as ldap:
            search_flt = filter_format("(memberOf=%s,%s)", ("cn=AwesomeFolk", ldap._base_dn))
            search_flt = ldap._add_user_filter(search_flt)
            self.assertEqual(
                search_flt,
                "(&(memberOf=cn=AwesomeFolk,dc=quay,dc=io)(filterField=somevalue)(filterField2=someothervalue))",
            )

        some_superuser_filter = "(filterField=somesuperuser)"
        some_restricted_user_filter = "(filterField=somerestricteduser)"
        with mock_ldap(
            user_filter=some_user_filter,
            superuser_filter=some_superuser_filter,
            restricted_user_filter=some_restricted_user_filter,
        ) as ldap:
            search_flt = filter_format("(memberOf=%s,%s)", ("cn=AwesomeFolk", ldap._base_dn))
            search_flt = ldap._add_user_filter(search_flt)
            superuser_search_flt = ldap._add_superuser_filter(search_flt)
            restricted_user_search_flt = ldap._add_restricted_user_filter(search_flt)
            self.assertEqual(
                superuser_search_flt,
                "(&(&(memberOf=cn=AwesomeFolk,dc=quay,dc=io)(filterField=somevalue))(filterField=somesuperuser))",
            )
            self.assertEqual(
                restricted_user_search_flt,
                "(&(&(memberOf=cn=AwesomeFolk,dc=quay,dc=io)(filterField=somevalue))(filterField=somerestricteduser))",
            )

    def test_ldap_user_filtering_no_users(self):
        no_user_filter = "(filterField=anothervalue)"
        with mock_ldap(user_filter=no_user_filter) as ldap:
            # Verify we cannot login.
            (response, _) = ldap.verify_and_link_user("someuser", "somepass")
            assert response is None

            (it, err) = ldap.iterate_group_members(
                {"group_dn": "cn=AwesomeFolk"}, disable_pagination=True
            )
            self.assertIsNone(err)

            results = list(it)
            self.assertEqual(0, len(results))

    def test_ldap_user_filtering_valid_users(self):
        valid_user_filter = "(filterField=somevalue)"
        with mock_ldap(user_filter=valid_user_filter) as ldap:
            # Verify we can login.
            (response, _) = ldap.verify_and_link_user("someuser", "somepass")
            self.assertEqual(response.username, "someuser")

            (it, err) = ldap.iterate_group_members(
                {"group_dn": "cn=AwesomeFolk"}, disable_pagination=True
            )
            self.assertIsNone(err)

            results = list(it)
            self.assertEqual(4, len(results))

    def test_ldap_superuser_and_restricted_user_filtering(self):
        valid_user_filter = "(filterField=somevalue)"
        valid_superuser_filter = "(filterField=superuser)"
        valid_restricted_user_filter = "(filterField=restricted)"

        with mock_ldap(user_filter=valid_user_filter) as ldap:
            # Verify we can login.
            (response, _) = ldap.verify_and_link_user("someuser", "somepass")
            self.assertEqual(response.username, "someuser")

        with mock_ldap(
            user_filter=valid_user_filter,
            superuser_filter=valid_superuser_filter,
            restricted_user_filter=valid_restricted_user_filter,
        ) as ldap:
            (it, err) = ldap.iterate_group_members(
                {"group_dn": "cn=AwesomeFolk"}, disable_pagination=True
            )
            self.assertIsNone(err)

            results = list(it)
            self.assertEqual(4, len(results))

            for u in results:
                user = u[0]

                is_superuser = ldap.is_superuser(user.username)
                is_restricted_user = ldap.is_restricted_user(user.username)

                if user.username == "somesuperuser":
                    self.assertTrue(is_superuser)
                    self.assertFalse(is_restricted_user)

                    self.assertEqual("somesuperuser", user.id)
                    self.assertEqual("somesuperuser", user.username)
                    self.assertEqual("superfoo@bar.com", user.email)

                elif user.username == "somerestricteduser":
                    self.assertTrue(is_restricted_user)
                    self.assertFalse(is_superuser)

                    self.assertEqual("somerestricteduser", user.id)
                    self.assertEqual("somerestricteduser", user.username)
                    self.assertEqual("restrictedfoo@bar.com", user.email)

                else:
                    self.assertFalse(is_superuser)
                    self.assertFalse(is_restricted_user)

            self.assertTrue(ldap.has_superusers())
            self.assertTrue(ldap.has_restricted_users())

    def test_ldap_superuser_and_restricted_user_invalid_filter(self):
        valid_user_filter = "(filterField=somevalue)"
        invalid_superuser_filter = "(filterField=notsuperuser)"
        invalid_restricted_user_filter = "(filterField=notrestricted)"

        with mock_ldap(user_filter=valid_user_filter) as ldap:
            # Verify we can login.
            (response, _) = ldap.verify_and_link_user("someuser", "somepass")
            self.assertEqual(response.username, "someuser")

        with mock_ldap(
            user_filter=valid_user_filter,
            superuser_filter=invalid_superuser_filter,
            restricted_user_filter=invalid_restricted_user_filter,
        ) as ldap:
            (it, err) = ldap.iterate_group_members(
                {"group_dn": "cn=AwesomeFolk"}, disable_pagination=True
            )
            self.assertIsNone(err)

            results = list(it)
            self.assertEqual(4, len(results))

            for u in results:
                user = u[0]

                is_superuser = ldap.is_superuser(user.username)
                is_restricted_user = ldap.is_restricted_user(user.username)
                self.assertFalse(is_superuser)
                self.assertFalse(is_restricted_user)

            self.assertFalse(ldap.has_superusers())
            self.assertFalse(ldap.has_restricted_users())

    def test_ldap_superuser_and_restricted_user_no_filter_set(self):
        valid_user_filter = "(filterField=somevalue)"
        superuser_filter = None
        restricted_user_filter = None

        with mock_ldap(user_filter=valid_user_filter) as ldap:
            # Verify we can login.
            (response, _) = ldap.verify_and_link_user("someuser", "somepass")
            self.assertEqual(response.username, "someuser")

        with mock_ldap(
            user_filter=valid_user_filter,
            superuser_filter=superuser_filter,
            restricted_user_filter=restricted_user_filter,
        ) as ldap:
            (it, err) = ldap.iterate_group_members(
                {"group_dn": "cn=AwesomeFolk"}, disable_pagination=True
            )
            self.assertIsNone(err)

            results = list(it)
            self.assertEqual(4, len(results))

            for u in results:
                user = u[0]

                is_superuser = ldap.is_superuser(user.username)
                is_restricted_user = ldap.is_restricted_user(user.username)
                self.assertFalse(is_superuser)
                self.assertTrue(is_restricted_user)

            self.assertFalse(ldap.has_superusers())
            self.assertTrue(ldap.has_restricted_users())

    def test_at_least_one_user_exists_filtered(self):
        base_dn = ["dc=quay", "dc=io"]
        admin_dn = "uid=testy,ou=employees,dc=quay,dc=io"
        admin_passwd = "password"
        user_rdn = ["ou=employees"]
        uid_attr = "uid"
        email_attr = "mail"
        secondary_user_rdns = ["ou=otheremployees"]

        with mock_ldap():
            ldap = LDAPUsers(
                "ldap://localhost",
                base_dn,
                admin_dn,
                admin_passwd,
                user_rdn,
                uid_attr,
                email_attr,
                ldap_user_filter="(filterField=somevalue)",
            )
            (response, err_msg) = ldap.at_least_one_user_exists()
            self.assertIsNone(err_msg)
            self.assertTrue(response)

    def test_at_least_one_user_exists_filtered_away(self):
        base_dn = ["dc=quay", "dc=io"]
        admin_dn = "uid=testy,ou=employees,dc=quay,dc=io"
        admin_passwd = "password"
        user_rdn = ["ou=employees"]
        uid_attr = "uid"
        email_attr = "mail"
        secondary_user_rdns = ["ou=otheremployees"]

        with mock_ldap():
            ldap = LDAPUsers(
                "ldap://localhost",
                base_dn,
                admin_dn,
                admin_passwd,
                user_rdn,
                uid_attr,
                email_attr,
                ldap_user_filter="(filterField=someothervalue)",
            )
            (response, err_msg) = ldap.at_least_one_user_exists()
            self.assertIsNone(err_msg)
            self.assertFalse(response)


if __name__ == "__main__":
    unittest.main()
