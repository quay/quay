import logging

from collections import namedtuple, defaultdict
from functools import partial

from flask_principal import identity_loaded, Permission, Identity, identity_changed


from app import app, superusers
from auth import scopes
from data import model


logger = logging.getLogger(__name__)


_ResourceNeed = namedtuple("resource", ["type", "namespace", "name", "role"])
_RepositoryNeed = partial(_ResourceNeed, "repository")
_NamespaceWideNeed = namedtuple("namespacewide", ["type", "namespace", "role"])
_OrganizationNeed = partial(_NamespaceWideNeed, "organization")
_OrganizationRepoNeed = partial(_NamespaceWideNeed, "organizationrepo")
_TeamTypeNeed = namedtuple("teamwideneed", ["type", "orgname", "teamname", "role"])
_TeamNeed = partial(_TeamTypeNeed, "orgteam")
_UserTypeNeed = namedtuple("userspecificneed", ["type", "username", "role"])
_UserNeed = partial(_UserTypeNeed, "user")
_SuperUserNeed = partial(namedtuple("superuserneed", ["type"]), "superuser")


REPO_ROLES = [None, "read", "write", "admin"]
TEAM_ROLES = [None, "member", "creator", "admin"]
USER_ROLES = [None, "read", "admin"]

TEAM_ORGWIDE_REPO_ROLES = {
    "admin": "admin",
    "creator": None,
    "member": None,
}

SCOPE_MAX_REPO_ROLES = defaultdict(lambda: None)
SCOPE_MAX_REPO_ROLES.update(
    {
        scopes.READ_REPO: "read",
        scopes.WRITE_REPO: "write",
        scopes.ADMIN_REPO: "admin",
        scopes.DIRECT_LOGIN: "admin",
    }
)

SCOPE_MAX_TEAM_ROLES = defaultdict(lambda: None)
SCOPE_MAX_TEAM_ROLES.update(
    {
        scopes.CREATE_REPO: "creator",
        scopes.DIRECT_LOGIN: "admin",
        scopes.ORG_ADMIN: "admin",
    }
)

SCOPE_MAX_USER_ROLES = defaultdict(lambda: None)
SCOPE_MAX_USER_ROLES.update(
    {
        scopes.READ_USER: "read",
        scopes.DIRECT_LOGIN: "admin",
        scopes.ADMIN_USER: "admin",
    }
)


def repository_read_grant(namespace, repository):
    return _RepositoryNeed(namespace, repository, "read")


def repository_write_grant(namespace, repository):
    return _RepositoryNeed(namespace, repository, "write")


def repository_admin_grant(namespace, repository):
    return _RepositoryNeed(namespace, repository, "admin")


class QuayDeferredPermissionUser(Identity):
    def __init__(self, uuid, auth_type, auth_scopes, user=None):
        super(QuayDeferredPermissionUser, self).__init__(uuid, auth_type)

        self._namespace_wide_loaded = set()
        self._repositories_loaded = set()
        self._personal_loaded = False

        self._scope_set = auth_scopes
        self._user_object = user

    @staticmethod
    def for_id(uuid, auth_scopes=None):
        auth_scopes = auth_scopes if auth_scopes is not None else {scopes.DIRECT_LOGIN}
        return QuayDeferredPermissionUser(uuid, "user_uuid", auth_scopes)

    @staticmethod
    def for_user(user, auth_scopes=None):
        auth_scopes = auth_scopes if auth_scopes is not None else {scopes.DIRECT_LOGIN}
        return QuayDeferredPermissionUser(user.uuid, "user_uuid", auth_scopes, user=user)

    def _translate_role_for_scopes(self, cardinality, max_roles, role):
        if self._scope_set is None:
            return role

        max_for_scopes = max({cardinality.index(max_roles[scope]) for scope in self._scope_set})

        if max_for_scopes < cardinality.index(role):
            logger.debug("Translated permission %s -> %s", role, cardinality[max_for_scopes])
            return cardinality[max_for_scopes]
        else:
            return role

    def _team_role_for_scopes(self, role):
        return self._translate_role_for_scopes(TEAM_ROLES, SCOPE_MAX_TEAM_ROLES, role)

    def _repo_role_for_scopes(self, role):
        return self._translate_role_for_scopes(REPO_ROLES, SCOPE_MAX_REPO_ROLES, role)

    def _user_role_for_scopes(self, role):
        return self._translate_role_for_scopes(USER_ROLES, SCOPE_MAX_USER_ROLES, role)

    def _populate_user_provides(self, user_object):
        """
        Populates the provides that naturally apply to a user, such as being the admin of their own
        namespace.
        """

        # Add the user specific permissions, only for non-oauth permission
        user_grant = _UserNeed(user_object.username, self._user_role_for_scopes("admin"))
        logger.debug("User permission: {0}".format(user_grant))
        self.provides.add(user_grant)

        # Every user is the admin of their own 'org'
        user_namespace = _OrganizationNeed(
            user_object.username, self._team_role_for_scopes("admin")
        )
        logger.debug("User namespace permission: {0}".format(user_namespace))
        self.provides.add(user_namespace)

        # Org repo roles can differ for scopes
        user_repos = _OrganizationRepoNeed(
            user_object.username, self._repo_role_for_scopes("admin")
        )
        logger.debug("User namespace repo permission: {0}".format(user_repos))
        self.provides.add(user_repos)

        if (
            scopes.SUPERUSER in self._scope_set or scopes.DIRECT_LOGIN in self._scope_set
        ) and superusers.is_superuser(user_object.username):
            logger.debug("Adding superuser to user: %s", user_object.username)
            self.provides.add(_SuperUserNeed())

    def _populate_namespace_wide_provides(self, user_object, namespace_filter):
        """
        Populates the namespace-wide provides for a particular user under a particular namespace.

        This method does *not* add any provides for specific repositories.
        """

        for team in model.permission.get_org_wide_permissions(
            user_object, org_filter=namespace_filter
        ):
            team_org_grant = _OrganizationNeed(
                team.organization.username, self._team_role_for_scopes(team.role.name)
            )
            logger.debug("Organization team added permission: {0}".format(team_org_grant))
            self.provides.add(team_org_grant)

            team_repo_role = TEAM_ORGWIDE_REPO_ROLES[team.role.name]
            org_repo_grant = _OrganizationRepoNeed(
                team.organization.username, self._repo_role_for_scopes(team_repo_role)
            )
            logger.debug("Organization team added repo permission: {0}".format(org_repo_grant))
            self.provides.add(org_repo_grant)

            team_grant = _TeamNeed(
                team.organization.username, team.name, self._team_role_for_scopes(team.role.name)
            )
            logger.debug("Team added permission: {0}".format(team_grant))
            self.provides.add(team_grant)

    def _populate_repository_provides(self, user_object, namespace_filter, repository_name):
        """
        Populates the repository-specific provides for a particular user and repository.
        """

        if namespace_filter and repository_name:
            permissions = model.permission.get_user_repository_permissions(
                user_object, namespace_filter, repository_name
            )
        else:
            permissions = model.permission.get_all_user_repository_permissions(user_object)

        for perm in permissions:
            repo_grant = _RepositoryNeed(
                perm.repository.namespace_user.username,
                perm.repository.name,
                self._repo_role_for_scopes(perm.role.name),
            )
            logger.debug("User added permission: {0}".format(repo_grant))
            self.provides.add(repo_grant)

    def can(self, permission):
        logger.debug("Loading user permissions after deferring for: %s", self.id)
        user_object = self._user_object or model.user.get_user_by_uuid(self.id)
        if user_object is None:
            return super(QuayDeferredPermissionUser, self).can(permission)

        # Add the user-specific provides.
        if not self._personal_loaded:
            self._populate_user_provides(user_object)
            self._personal_loaded = True

        # If we now have permission, no need to load any more permissions.
        if super(QuayDeferredPermissionUser, self).can(permission):
            return super(QuayDeferredPermissionUser, self).can(permission)

        # Check for namespace and/or repository permissions.
        perm_namespace = permission.namespace
        perm_repo_name = permission.repo_name
        perm_repository = None

        if perm_namespace and perm_repo_name:
            perm_repository = "%s/%s" % (perm_namespace, perm_repo_name)

        if not perm_namespace and not perm_repo_name:
            # Nothing more to load, so just check directly.
            return super(QuayDeferredPermissionUser, self).can(permission)

        # Lazy-load the repository-specific permissions.
        if perm_repository and perm_repository not in self._repositories_loaded:
            self._populate_repository_provides(user_object, perm_namespace, perm_repo_name)
            self._repositories_loaded.add(perm_repository)

            # If we now have permission, no need to load any more permissions.
            if super(QuayDeferredPermissionUser, self).can(permission):
                return super(QuayDeferredPermissionUser, self).can(permission)

        # Lazy-load the namespace-wide-only permissions.
        if perm_namespace and perm_namespace not in self._namespace_wide_loaded:
            self._populate_namespace_wide_provides(user_object, perm_namespace)
            self._namespace_wide_loaded.add(perm_namespace)

        return super(QuayDeferredPermissionUser, self).can(permission)


class QuayPermission(Permission):
    """
    Base for all permissions in Quay.
    """

    namespace = None
    repo_name = None


class ModifyRepositoryPermission(QuayPermission):
    def __init__(self, namespace, name):
        admin_need = _RepositoryNeed(namespace, name, "admin")
        write_need = _RepositoryNeed(namespace, name, "write")
        org_admin_need = _OrganizationRepoNeed(namespace, "admin")
        org_write_need = _OrganizationRepoNeed(namespace, "write")

        self.namespace = namespace
        self.repo_name = name

        super(ModifyRepositoryPermission, self).__init__(
            admin_need, write_need, org_admin_need, org_write_need
        )


class ReadRepositoryPermission(QuayPermission):
    def __init__(self, namespace, name):
        admin_need = _RepositoryNeed(namespace, name, "admin")
        write_need = _RepositoryNeed(namespace, name, "write")
        read_need = _RepositoryNeed(namespace, name, "read")
        org_admin_need = _OrganizationRepoNeed(namespace, "admin")
        org_write_need = _OrganizationRepoNeed(namespace, "write")
        org_read_need = _OrganizationRepoNeed(namespace, "read")

        self.namespace = namespace
        self.repo_name = name

        super(ReadRepositoryPermission, self).__init__(
            admin_need, write_need, read_need, org_admin_need, org_read_need, org_write_need
        )


class AdministerRepositoryPermission(QuayPermission):
    def __init__(self, namespace, name):
        admin_need = _RepositoryNeed(namespace, name, "admin")
        org_admin_need = _OrganizationRepoNeed(namespace, "admin")

        self.namespace = namespace
        self.repo_name = name

        super(AdministerRepositoryPermission, self).__init__(admin_need, org_admin_need)


class CreateRepositoryPermission(QuayPermission):
    def __init__(self, namespace):
        admin_org = _OrganizationNeed(namespace, "admin")
        create_repo_org = _OrganizationNeed(namespace, "creator")

        self.namespace = namespace

        super(CreateRepositoryPermission, self).__init__(admin_org, create_repo_org)


class SuperUserPermission(QuayPermission):
    def __init__(self):
        need = _SuperUserNeed()
        super(SuperUserPermission, self).__init__(need)


class UserAdminPermission(QuayPermission):
    def __init__(self, username):
        user_admin = _UserNeed(username, "admin")
        super(UserAdminPermission, self).__init__(user_admin)


class UserReadPermission(QuayPermission):
    def __init__(self, username):
        user_admin = _UserNeed(username, "admin")
        user_read = _UserNeed(username, "read")
        super(UserReadPermission, self).__init__(user_read, user_admin)


class AdministerOrganizationPermission(QuayPermission):
    def __init__(self, org_name):
        admin_org = _OrganizationNeed(org_name, "admin")

        self.namespace = org_name

        super(AdministerOrganizationPermission, self).__init__(admin_org)


class OrganizationMemberPermission(QuayPermission):
    def __init__(self, org_name):
        admin_org = _OrganizationNeed(org_name, "admin")
        repo_creator_org = _OrganizationNeed(org_name, "creator")
        org_member = _OrganizationNeed(org_name, "member")

        self.namespace = org_name

        super(OrganizationMemberPermission, self).__init__(admin_org, org_member, repo_creator_org)


class ViewTeamPermission(QuayPermission):
    def __init__(self, org_name, team_name):
        team_admin = _TeamNeed(org_name, team_name, "admin")
        team_creator = _TeamNeed(org_name, team_name, "creator")
        team_member = _TeamNeed(org_name, team_name, "member")
        admin_org = _OrganizationNeed(org_name, "admin")

        self.namespace = org_name

        super(ViewTeamPermission, self).__init__(team_admin, team_creator, team_member, admin_org)


class AlwaysFailPermission(QuayPermission):
    def can(self):
        return False


@identity_loaded.connect_via(app)
def on_identity_loaded(sender, identity):
    logger.debug("Identity loaded: %s" % identity)
    # We have verified an identity, load in all of the permissions

    if isinstance(identity, QuayDeferredPermissionUser):
        logger.debug("Deferring permissions for user with uuid: %s", identity.id)

    elif identity.auth_type == "user_uuid":
        logger.debug("Switching username permission to deferred object with uuid: %s", identity.id)
        switch_to_deferred = QuayDeferredPermissionUser.for_id(identity.id)
        identity_changed.send(app, identity=switch_to_deferred)

    elif identity.auth_type == "token":
        logger.debug("Loading permissions for token: %s", identity.id)
        token_data = model.token.load_token_data(identity.id)

        repo_grant = _RepositoryNeed(
            token_data.repository.namespace_user.username,
            token_data.repository.name,
            token_data.role.name,
        )
        logger.debug("Delegate token added permission: %s", repo_grant)
        identity.provides.add(repo_grant)

    elif identity.auth_type == "signed_grant" or identity.auth_type == "signed_jwt":
        logger.debug("Loaded %s identity for: %s", identity.auth_type, identity.id)

    else:
        logger.error("Unknown identity auth type: %s", identity.auth_type)
