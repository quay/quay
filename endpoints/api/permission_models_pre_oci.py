from app import avatar
from data import model
from .permission_models_interface import (
    PermissionDataInterface,
    UserPermission,
    TeamPermission,
    Role,
    SaveException,
    DeleteException,
)


class PreOCIModel(PermissionDataInterface):
    """
    PreOCIModel implements the data model for Permission using a database schema before it was
    changed to support the OCI specification.
    """

    def get_repo_permissions_by_user(self, namespace_name, repository_name):
        org = None
        try:
            org = model.organization.get_organization(
                namespace_name
            )  # Will raise an error if not org
        except model.InvalidOrganizationException:
            # This repository isn't under an org
            pass

        # Load the permissions.
        repo_perms = model.user.get_all_repo_users(namespace_name, repository_name)

        if org:
            users_filter = {perm.user for perm in repo_perms}
            org_members = model.organization.get_organization_member_set(
                org, users_filter=users_filter
            )

        def is_org_member(user):
            if not org:
                return False

            return user.robot or user.username in org_members

        return [
            self._user_permission(perm, org is not None, is_org_member(perm.user))
            for perm in repo_perms
        ]

    def get_repo_roles(self, username, namespace_name, repository_name):
        user = model.user.get_user(username)
        if not user:
            return None

        repo = model.repository.get_repository(namespace_name, repository_name)
        if not repo:
            return None

        return [self._role(r) for r in model.permission.get_user_repo_permissions(user, repo)]

    def get_repo_permission_for_user(self, username, namespace_name, repository_name):
        perm = model.permission.get_user_reponame_permission(
            username, namespace_name, repository_name
        )
        org = None
        try:
            org = model.organization.get_organization(namespace_name)
            org_members = model.organization.get_organization_member_set(
                org, users_filter={perm.user}
            )
            is_org_member = perm.user.robot or perm.user.username in org_members
        except model.InvalidOrganizationException:
            # This repository is not part of an organization
            is_org_member = False

        return self._user_permission(perm, org is not None, is_org_member)

    def set_repo_permission_for_user(self, username, namespace_name, repository_name, role_name):
        try:
            perm = model.permission.set_user_repo_permission(
                username, namespace_name, repository_name, role_name
            )
            org = None
            try:
                org = model.organization.get_organization(namespace_name)
                org_members = model.organization.get_organization_member_set(
                    org, users_filter={perm.user}
                )
                is_org_member = perm.user.robot or perm.user.username in org_members
            except model.InvalidOrganizationException:
                # This repository is not part of an organization
                is_org_member = False
            return self._user_permission(perm, org is not None, is_org_member)
        except model.DataModelException as ex:
            raise SaveException(ex)

    def delete_repo_permission_for_user(self, username, namespace_name, repository_name):
        try:
            model.permission.delete_user_permission(username, namespace_name, repository_name)
        except model.DataModelException as ex:
            raise DeleteException(ex)

    def get_repo_permissions_by_team(self, namespace_name, repository_name):
        repo_perms = model.permission.get_all_repo_teams(namespace_name, repository_name)
        return [self._team_permission(perm, perm.team.name) for perm in repo_perms]

    def get_repo_role_for_team(self, team_name, namespace_name, repository_name):
        return self._role(
            model.permission.get_team_reponame_permission(
                team_name, namespace_name, repository_name
            )
        )

    def set_repo_permission_for_team(self, team_name, namespace_name, repository_name, role_name):
        try:
            return self._team_permission(
                model.permission.set_team_repo_permission(
                    team_name, namespace_name, repository_name, role_name
                ),
                team_name,
            )
        except model.DataModelException as ex:
            raise SaveException(ex)

    def delete_repo_permission_for_team(self, team_name, namespace_name, repository_name):
        try:
            model.permission.delete_team_permission(team_name, namespace_name, repository_name)
        except model.DataModelException as ex:
            raise DeleteException(ex)

    def _role(self, permission_obj):
        return Role(role_name=permission_obj.role.name)

    def _user_permission(self, permission_obj, has_org, is_org_member):
        return UserPermission(
            role_name=permission_obj.role.name,
            username=permission_obj.user.username,
            is_robot=permission_obj.user.robot,
            avatar=avatar.get_data_for_user(permission_obj.user),
            is_org_member=is_org_member,
            has_org=has_org,
        )

    def _team_permission(self, permission_obj, team_name):
        return TeamPermission(
            role_name=permission_obj.role.name,
            team_name=permission_obj.team.name,
            avatar=avatar.get_data_for_team(permission_obj.team),
        )


pre_oci_model = PreOCIModel()
