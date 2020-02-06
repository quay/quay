import logging

from app import app
from data.database import User
from util.names import parse_robot_username

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def cleanup_old_robots(page_size=50, force=False):
    """
    Deletes any robots that live under namespaces that no longer exist.
    """
    if not force and not app.config.get("SETUP_COMPLETE", False):
        return

    # Collect the robot accounts to delete.
    page_number = 1
    to_delete = []
    encountered_namespaces = {}

    while True:
        found_bots = False
        for robot in list(User.select().where(User.robot == True).paginate(page_number, page_size)):
            found_bots = True
            logger.info("Checking robot %s (page %s)", robot.username, page_number)
            parsed = parse_robot_username(robot.username)
            if parsed is None:
                continue

            namespace, _ = parsed
            if namespace in encountered_namespaces:
                if not encountered_namespaces[namespace]:
                    logger.info("Marking %s to be deleted", robot.username)
                    to_delete.append(robot)
            else:
                try:
                    User.get(username=namespace)
                    encountered_namespaces[namespace] = True
                except User.DoesNotExist:
                    # Save the robot account for deletion.
                    logger.info("Marking %s to be deleted", robot.username)
                    to_delete.append(robot)
                    encountered_namespaces[namespace] = False

        if not found_bots:
            break

        page_number = page_number + 1

    # Cleanup any robot accounts whose corresponding namespace doesn't exist.
    logger.info("Found %s robots to delete", len(to_delete))
    for index, robot in enumerate(to_delete):
        logger.info("Deleting robot %s of %s (%s)", index, len(to_delete), robot.username)
        robot.delete_instance(recursive=True, delete_nullable=True)
