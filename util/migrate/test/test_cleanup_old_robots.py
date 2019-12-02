import pytest

from data.database import User
from util.migrate.cleanup_old_robots import cleanup_old_robots

from test.fixtures import *


def test_cleanup_old_robots(initialized_db):
    before_robot_count = User.select().where(User.robot == True).count()
    before_user_count = User.select().count()

    # Run the cleanup once, and ensure it does nothing.
    cleanup_old_robots(force=True)

    after_robot_count = User.select().where(User.robot == True).count()
    after_user_count = User.select().count()

    assert before_robot_count == after_robot_count
    assert before_user_count == after_user_count

    # Create some orphan robots.
    created = set()
    for index in range(0, 50):
        created.add("doesnotexist+a%s" % index)
        created.add("anothernamespace+b%s" % index)

        User.create(username="doesnotexist+a%s" % index, robot=True)
        User.create(username="anothernamespace+b%s" % index, robot=True)

    before_robot_count = User.select().where(User.robot == True).count()
    before_user_count = User.select().count()

    cleanup_old_robots(page_size=10, force=True)

    after_robot_count = User.select().where(User.robot == True).count()
    after_user_count = User.select().count()

    assert before_robot_count == after_robot_count + len(created)
    assert before_user_count == after_user_count + len(created)

    for name in created:
        with pytest.raises(User.DoesNotExist):
            User.get(username=name)
