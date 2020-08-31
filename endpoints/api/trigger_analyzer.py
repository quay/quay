from os import path

from auth import permissions
from data import model
from util import dockerfileparse


def is_parent(context, dockerfile_path):
    """
    This checks whether the context is a parent of the dockerfile_path.
    """
    if context == "" or dockerfile_path == "":
        return False

    normalized_context = path.normpath(context)
    if normalized_context[len(normalized_context) - 1] != path.sep:
        normalized_context += path.sep

    if normalized_context[0] != path.sep:
        normalized_context = path.sep + normalized_context

    normalized_subdir = path.normpath(path.dirname(dockerfile_path))
    if normalized_subdir[0] != path.sep:
        normalized_subdir = path.sep + normalized_subdir

    if normalized_subdir[len(normalized_subdir) - 1] != path.sep:
        normalized_subdir += path.sep

    return normalized_subdir.startswith(normalized_context)


class TriggerAnalyzer(object):
    """
    This analyzes triggers and returns the appropriate trigger and robot view to the frontend.
    """

    def __init__(
        self, handler, namespace_name, server_hostname, new_config_dict, admin_org_permission
    ):
        self.handler = handler
        self.namespace_name = namespace_name
        self.server_hostname = server_hostname
        self.new_config_dict = new_config_dict
        self.admin_org_permission = admin_org_permission

    def analyze_trigger(self):
        # Load the contents of the Dockerfile.
        contents = self.handler.load_dockerfile_contents()
        if not contents:
            return self.analyze_view(
                self.namespace_name,
                None,
                "warning",
                message="Specified Dockerfile path for the trigger was not found on the main "
                + "branch. This trigger may fail.",
            )

        # Parse the contents of the Dockerfile.
        parsed = dockerfileparse.parse_dockerfile(contents)
        if not parsed:
            return self.analyze_view(
                self.namespace_name,
                None,
                "error",
                message="Could not parse the Dockerfile specified",
            )

        # Check whether the dockerfile_path is correct
        if self.new_config_dict.get("context") and not is_parent(
            self.new_config_dict.get("context"), self.new_config_dict.get("dockerfile_path")
        ):
            return self.analyze_view(
                self.namespace_name,
                None,
                "error",
                message="Dockerfile, %s, is not a child of the context, %s."
                % (
                    self.new_config_dict.get("context"),
                    self.new_config_dict.get("dockerfile_path"),
                ),
            )

        # Determine the base image (i.e. the FROM) for the Dockerfile.
        base_image = parsed.get_base_image()
        if not base_image:
            return self.analyze_view(
                self.namespace_name, None, "warning", message="No FROM line found in the Dockerfile"
            )

        # Check to see if the base image lives in Quay.
        quay_registry_prefix = "%s/" % self.server_hostname
        if not base_image.startswith(quay_registry_prefix):
            return self.analyze_view(self.namespace_name, None, "publicbase")

        # Lookup the repository in Quay.
        result = str(base_image)[len(quay_registry_prefix) :].split("/", 2)
        if len(result) != 2:
            msg = '"%s" is not a valid Quay repository path' % base_image
            return self.analyze_view(self.namespace_name, None, "warning", message=msg)

        (base_namespace, base_repository) = result
        found_repository = model.repository.get_repository(base_namespace, base_repository)
        if not found_repository:
            return self.analyze_view(
                self.namespace_name,
                None,
                "error",
                message='Repository "%s" referenced by the Dockerfile was not found' % base_image,
            )

        # If the repository is private and the user cannot see that repo, then
        # mark it as not found.
        can_read = False
        if base_namespace == self.namespace_name:
            can_read = permissions.ReadRepositoryPermission(base_namespace, base_repository)

        if found_repository.visibility.name != "public" and not can_read:
            return self.analyze_view(
                self.namespace_name,
                None,
                "error",
                message='Repository "%s" referenced by the Dockerfile was not found' % base_image,
            )

        if found_repository.visibility.name == "public":
            return self.analyze_view(base_namespace, base_repository, "publicbase")

        return self.analyze_view(base_namespace, base_repository, "requiresrobot")

    def analyze_view(self, image_namespace, image_repository, status, message=None):
        # Retrieve the list of robots and mark whether they have read access already.
        robots = []
        if self.admin_org_permission and self.namespace_name == image_namespace:
            if image_repository is not None:
                perm_query = model.user.get_all_repo_users_transitive(
                    image_namespace, image_repository
                )
                user_ids_with_permission = set([user.id for user in perm_query])
            else:
                user_ids_with_permission = set()

            def robot_view(robot):
                assert robot.username.startswith(
                    self.namespace_name + "+"
                ), "Expected robot under namespace %s, Found: %s" % (
                    self.namespace_name,
                    robot.username,
                )
                result = {
                    "name": robot.username,
                    "kind": "user",
                    "is_robot": True,
                    "can_read": robot.id in user_ids_with_permission,
                }
                return result

            robots = [
                robot_view(robot) for robot in model.user.list_namespace_robots(self.namespace_name)
            ]

        return {
            "namespace": image_namespace,
            "name": image_repository,
            "robots": robots,
            "status": status,
            "message": message,
            "is_admin": self.admin_org_permission,
        }
