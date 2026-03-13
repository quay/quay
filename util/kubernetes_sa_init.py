"""
Kubernetes ServiceAccount initialization for Quay startup.

This module handles eager initialization of K8s SA authentication resources
during application startup, creating the system organization and superuser
robot accounts before any authentication requests are processed.
"""

import logging
from typing import TYPE_CHECKING, Optional

if TYPE_CHECKING:
    from data.database import User

logger = logging.getLogger(__name__)


def create_kubernetes_sa_system_org(org_name: str) -> "User":
    """
    Create the system organization for Kubernetes SA robot accounts.

    This organization owns all robot accounts that correspond to Kubernetes
    ServiceAccounts. It is created without an owner as a system-level org.

    Args:
        org_name: Name of the organization to create

    Returns:
        The created organization object

    Raises:
        Exception if creation fails
    """
    from data.database import db_transaction
    from data.model import team, user

    with db_transaction():
        # Create org without an owner - it's a system org
        new_org = user.create_user_noverify(
            org_name,
            email=None,
            email_required=False,
        )
        new_org.organization = True
        new_org.save()

        # Create the owners team (required for org structure)
        team.create_team("owners", new_org, "admin")

    logger.info(f"Created Kubernetes SA system organization '{org_name}'")
    return new_org


def ensure_kubernetes_sa_system_org(org_name: str) -> "User":
    """
    Ensure the system organization exists, creating it if necessary.

    This is idempotent - if the org already exists, it is returned without
    modification.

    Args:
        org_name: Name of the organization

    Returns:
        The organization object (existing or newly created)
    """
    from data import model
    from data.model import organization

    try:
        return organization.get_organization(org_name)
    except model.InvalidOrganizationException:
        logger.info(f"System organization '{org_name}' does not exist, creating...")
        return create_kubernetes_sa_system_org(org_name)


def ensure_kubernetes_sa_robot(
    system_org: "User",
    namespace: str,
    sa_name: str,
    subject: str,
    robot_shortname: str,
) -> "User":
    """
    Ensure a robot account exists for the given Kubernetes SA, creating if needed.

    This is idempotent - if the robot already exists, it is returned without
    modification.

    Args:
        system_org: The system organization that owns the robot
        namespace: Kubernetes namespace of the ServiceAccount
        sa_name: Name of the ServiceAccount
        subject: Full SA subject string (e.g., system:serviceaccount:ns:name)
        robot_shortname: Generated robot shortname (e.g., kube_ns_name)

    Returns:
        The robot account (existing or newly created)
    """
    from data import model
    from data.model import team, user

    robot_username = f"{system_org.username}+{robot_shortname}"

    try:
        return user.lookup_robot(robot_username)
    except model.InvalidRobotException:
        # Robot doesn't exist, create it
        description = f"Kubernetes SA: {namespace}/{sa_name}"
        metadata = {
            "kubernetes_namespace": namespace,
            "kubernetes_sa_name": sa_name,
            "kubernetes_subject": subject,
        }

        robot, _ = user.create_robot(
            robot_shortname,
            system_org,
            description=description,
            unstructured_metadata=metadata,
        )
        logger.info(f"Created Kubernetes SA robot account: {robot_username}")

        # Add robot to owners team
        try:
            owners_team = team.get_organization_team(system_org.username, "owners")
            team.add_user_to_team(robot, owners_team)
        except Exception as e:
            logger.warning(f"Failed to add robot to owners team: {e}")

        return robot


def initialize_kubernetes_sa_resources(config: dict) -> bool:
    """
    Initialize Kubernetes SA authentication resources at application startup.

    This function should be called from gunicorn's when_ready hook to eagerly
    create the system organization and superuser robot account before any
    requests are processed.

    Creates:
    - System organization (e.g., 'quay-system') if it doesn't exist
    - Superuser robot account if SUPERUSER_SUBJECT is configured

    Args:
        config: Application configuration dictionary

    Returns:
        True if initialization was performed, False if skipped (feature disabled)
    """
    # Check if feature is enabled
    if not config.get("FEATURE_KUBERNETES_SA_AUTH", False):
        logger.debug("FEATURE_KUBERNETES_SA_AUTH is disabled, skipping initialization")
        return False

    kubernetes_config = config.get("KUBERNETES_SA_AUTH_CONFIG")
    if not kubernetes_config:
        logger.debug("KUBERNETES_SA_AUTH_CONFIG not configured, skipping initialization")
        return False

    # Import here to avoid circular imports and ensure app context is available
    from oauth.services.kubernetes_sa import KubernetesServiceAccountLoginService

    try:
        service = KubernetesServiceAccountLoginService(config)
        system_org_name = service.system_org_name

        # Ensure system org exists
        logger.info(f"Initializing Kubernetes SA system organization: {system_org_name}")
        system_org = ensure_kubernetes_sa_system_org(system_org_name)

        # Create superuser robots for all configured subjects
        superuser_subjects = service.superuser_subjects
        for superuser_subject in superuser_subjects:
            parsed = service.parse_sa_subject(superuser_subject)
            if not parsed:
                logger.warning(f"Invalid SUPERUSER_SUBJECTS entry: {superuser_subject}")
                continue

            namespace, sa_name = parsed
            robot_shortname = service.generate_robot_shortname(namespace, sa_name)

            logger.info(f"Initializing superuser robot for: {superuser_subject}")
            ensure_kubernetes_sa_robot(
                system_org,
                namespace,
                sa_name,
                superuser_subject,
                robot_shortname,
            )

            # Register as superuser
            robot_username = f"{system_org_name}+{robot_shortname}"
            try:
                from app import usermanager

                if not usermanager.is_superuser(robot_username):
                    usermanager.register_superuser(robot_username)
                    logger.info(f"Registered superuser: {robot_username}")
            except ImportError:
                logger.warning("Could not import usermanager, skipping superuser registration")
            except Exception:
                logger.exception(f"Failed to register superuser {robot_username}")

        logger.info("Kubernetes SA initialization complete")
        return True

    except Exception:
        logger.exception("Failed to initialize Kubernetes SA resources")
        # Don't raise - let lazy creation handle it as fallback
        return False
