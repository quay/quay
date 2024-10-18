import datetime
import json
import os
import time

import pytest

import util
from app import notification_queue
from data import model
from data.database import (
    ExternalNotificationMethod,
    TagNotificationSuccess,
    get_epoch_timestamp_ms,
)
from data.model import notification, repository
from data.model.oci.tag import (
    delete_tag,
    fetch_repo_tags_for_image_expiry_expiry_event,
    list_alive_tags,
    list_repository_tag_history,
    set_tag_end_ms,
)
from endpoints.api.repositorynotification_models_pre_oci import pre_oci_model
from notifications.notificationevent import RepoImageExpiryEvent
from test.fixtures import *
from util.notification import *
from util.timedeltastring import convert_to_timedelta
from workers.test.test_autopruneworker import create_manifest, create_tag

namespace = "buynlarge"
repo = "orgrepo"


def _past_timestamp_ms(time_delta):
    return int(time.time() * 1000) - convert_to_timedelta(time_delta).total_seconds() * 1000


@pytest.fixture
def initial_set(initialized_db):
    slack = ExternalNotificationMethod.get(ExternalNotificationMethod.name == "slack")
    image_expiry_event = ExternalNotificationEvent.get(
        ExternalNotificationEvent.name == "repo_image_expiry"
    )
    repo_ref = repository.get_repository(namespace, repo)

    n_1 = pre_oci_model.create_repo_notification(
        namespace_name=namespace,
        repository_name=repo,
        event_name=image_expiry_event.name,
        method_name=slack.name,
        method_config={"url": "http://example.com"},
        event_config={"days": 5},
        title="Image(s) will expire in 5 days",
    )
    n_1 = notification.get_repo_notification(n_1.uuid)
    n_2 = notification.create_repo_notification(
        repo_ref,
        image_expiry_event.name,
        slack.name,
        {"url": "http://example.com"},
        {"days": 10},
        title="Image(s) will expire in 10 days",
    )
    n_2 = notification.get_repo_notification(n_2.uuid)

    tags = list_alive_tags(repo_ref)
    for tag in tags:
        TagNotificationSuccess.create(notification=n_1.id, tag=tag.id, method=slack.id)
        TagNotificationSuccess.create(notification=n_2.id, tag=tag.id, method=slack.id)
    return {
        "repo_ref": repo_ref,
        "image_expiry_event": image_expiry_event,
        "slack": slack,
        "n_1": n_1,
        "n_2": n_2,
        "tags": tags,
    }


@pytest.fixture
def new_notification(initial_set):
    return notification.create_repo_notification(
        initial_set["repo_ref"],
        initial_set["image_expiry_event"].name,
        initial_set["slack"].name,
        {"url": "http://example.com"},
        {"days": 7},
        title="Image(s) will expire in 7 days",
    )


def test_tag_notifications_for_delete_repo_notification(initial_set):
    tag_event_count = (
        TagNotificationSuccess.select()
        .where(TagNotificationSuccess.notification == initial_set["n_1"].id)
        .count()
    )
    assert tag_event_count == len(initial_set["tags"])

    notification.delete_repo_notification(namespace, repo, initial_set["n_1"].uuid)
    tag_event_count = (
        TagNotificationSuccess.select()
        .where(TagNotificationSuccess.notification == initial_set["n_1"].id)
        .count()
    )
    assert tag_event_count == 0


def test_delete_tag_notifications_for_notification(initial_set):
    tag_event_count = (
        TagNotificationSuccess.select()
        .where(TagNotificationSuccess.notification == initial_set["n_1"].id)
        .count()
    )
    assert tag_event_count == len(initial_set["tags"])

    notification.delete_tag_notifications_for_notification(initial_set["n_1"].id)
    tag_event_count = (
        TagNotificationSuccess.select()
        .where(TagNotificationSuccess.notification == initial_set["n_1"].id)
        .count()
    )
    assert tag_event_count == 0


def test_delete_tag_notifications_for_tag(initial_set):
    tag_event_count = (
        TagNotificationSuccess.select()
        .where(TagNotificationSuccess.tag == initial_set["tags"][0].id)
        .count()
    )
    assert tag_event_count == 2

    notification.delete_tag_notifications_for_tag(initial_set["tags"][0])
    tag_event_count = (
        TagNotificationSuccess.select()
        .where(TagNotificationSuccess.tag == initial_set["tags"][0].id)
        .count()
    )
    assert tag_event_count == 0


def test_fetch_tags_to_notify(initial_set, new_notification):
    tag_event_count = (
        TagNotificationSuccess.select()
        .where(TagNotificationSuccess.notification == new_notification.id)
        .count()
    )
    assert tag_event_count == 0

    track_tags_to_notify(initial_set["tags"], new_notification)

    tag_event_count = (
        TagNotificationSuccess.select()
        .where(TagNotificationSuccess.notification == new_notification.id)
        .count()
    )
    assert tag_event_count == len(initial_set["tags"])


def test_fetch_notified_tag_ids_for_event(initial_set):
    tag_ids = fetch_notified_tag_ids_for_event(initial_set["n_2"])
    for tag in initial_set["tags"]:
        assert tag.id in tag_ids


def test_fetch_active_notification(initial_set, new_notification):
    if "mysql+pymysql" in os.environ.get("TEST_DATABASE_URI", ""):
        util.notification.SKIP_LOCKED = False

    # causing the event to failure
    for i in range(3):
        notification.increment_notification_failure_count(new_notification.uuid)

    # creating a `repo_push` event type
    notification.create_repo_notification(
        initial_set["repo_ref"],
        "repo_push",
        initial_set["slack"].name,
        {"url": "http://example.com"},
        {"days": 7},
        title="Image(s) will expire in 7 days",
    )

    time_now = get_epoch_timestamp_ms()
    event = fetch_active_notification(initial_set["image_expiry_event"])
    assert event.id == initial_set["n_1"].id
    event = (
        RepositoryNotification.select()
        .where(RepositoryNotification.id == initial_set["n_1"].id)
        .get()
    )
    assert event.last_ran_ms >= time_now


def test_scan_for_image_expiry_notifications(initial_set):
    if "mysql+pymysql" in os.environ.get("TEST_DATABASE_URI", ""):
        util.notification.SKIP_LOCKED = False
    future_ms = (datetime.datetime.now() + datetime.timedelta(days=1)).timestamp() * 1000
    for tag in initial_set["tags"]:
        set_tag_end_ms(tag, future_ms)
    scan_for_image_expiry_notifications(initial_set["image_expiry_event"].name)

    time.sleep(2)
    job1 = notification_queue.get()
    assert job1 is not None
    job1 = json.loads(job1["body"])
    for tag in initial_set["tags"]:
        assert tag.name in job1["event_data"]["tags"]

    job2 = notification_queue.get()
    assert job2 is not None
    job2 = json.loads(job2["body"])
    for tag in initial_set["tags"]:
        assert tag.name in job2["event_data"]["tags"]


def test_fetch_repo_tags_for_image_expiry_expiry_event(initial_set):
    future_ms = (datetime.datetime.now() + datetime.timedelta(days=1)).timestamp() * 1000
    expected_tags = []
    for tag in initial_set["tags"]:
        if tag.name == "prod":
            continue
        set_tag_end_ms(tag, future_ms)
        expected_tags.append(tag.id)
    tags = fetch_repo_tags_for_image_expiry_expiry_event(
        initial_set["repo_ref"].id, days=2, notified_tags=[]
    )
    assert len(tags) == len(expected_tags)
    for tag in tags:
        assert tag.id in expected_tags


def test_notifications_on_tag_expiry_update(initial_set):
    tag_event_count = (
        TagNotificationSuccess.select()
        .where(TagNotificationSuccess.notification == initial_set["n_1"].id)
        .count()
    )
    assert tag_event_count == len(initial_set["tags"])

    for tag in initial_set["tags"]:
        set_tag_end_ms(tag, get_epoch_timestamp_ms())

    tag_event_count = (
        TagNotificationSuccess.select()
        .where(TagNotificationSuccess.notification == initial_set["n_1"].id)
        .count()
    )
    assert tag_event_count == 0


def test_notifications_on_tag_delete(initial_set):
    for tag in initial_set["tags"]:
        delete_tag(initial_set["repo_ref"].id, tag.name)

    tag_event_count = (
        TagNotificationSuccess.select()
        .where(TagNotificationSuccess.notification == initial_set["n_1"].id)
        .count()
    )
    assert tag_event_count == 0


def test_list_repo_notifications(initial_set):
    email_event = notification.create_repo_notification(
        initial_set["repo_ref"],
        RepoImageExpiryEvent.event_name(),
        "email",
        {"email": "sunanda@test.com"},
        {"days": 10},
        title="Image(s) will expire in 10 days",
    )
    repo_notifications = notification.list_repo_notifications(namespace, repo)
    # 2 notifications created in initial_set() and 1 in this test case
    assert len(repo_notifications) == 3

    email_notification = notification.list_repo_notifications(
        namespace, repo, notification_uuid=email_event.uuid
    )
    assert len(email_notification) == 1

    email_notification = notification.list_repo_notifications(
        namespace,
        repo,
        event_name=RepoImageExpiryEvent.event_name(),
        notification_uuid=email_event.uuid,
    )
    assert len(email_notification) == 1

    email_notification = notification.list_repo_notifications(
        namespace, repo, event_name="repo_push", notification_uuid=email_event.uuid
    )
    assert len(email_notification) == 0

    email_notification = notification.list_repo_notifications(
        namespace, repo, event_name=RepoImageExpiryEvent.event_name()
    )
    assert len(email_notification) == 3


@pytest.mark.parametrize(
    "tags, expected, policy1, policy2",
    [
        (
            [
                "test1",
                "test2",
                "test3",
                "test4",
                "test5",
                "test6",
                "test7",
                "test8",
                "test9",
                "test10",
            ],
            ["test1", "test2", "test3", "test4", "test5"],
            ["creation_date", "4d"],
            ["number_of_tags", 5],
        ),
        (
            [
                "test1",
                "test2",
                "test3",
                "test4",
                "test5",
                "test6",
                "test7",
                "test8",
                "test9",
                "test10",
            ],
            ["test1", "test2", "test3", "test4", "test5", "test6", "test7"],
            ["number_of_tags", 3],
            ["number_of_tags", 5],
        ),
    ],
)
def test_notifications_with_namespace_autoprune_policy(
    tags, expected, policy1, policy2, initialized_db
):
    if "mysql+pymysql" in os.environ.get("TEST_DATABASE_URI", ""):
        util.notification.SKIP_LOCKED = False
    slack = ExternalNotificationMethod.get(ExternalNotificationMethod.name == "slack")
    image_expiry_event = ExternalNotificationEvent.get(
        ExternalNotificationEvent.name == "repo_image_expiry"
    )
    ns = model.user.get_namespace_user(namespace)

    # deleting existing autoprune policies
    existing_policies = model.autoprune.get_namespace_autoprune_policies_by_id(ns.id)
    for policy in existing_policies:
        model.autoprune.delete_namespace_autoprune_policy(namespace, policy.uuid)

    model.autoprune.create_namespace_autoprune_policy(
        namespace, {"method": policy1[0], "value": policy1[1]}, create_task=True
    )
    model.autoprune.create_namespace_autoprune_policy(
        namespace, {"method": policy2[0], "value": policy2[1]}, create_task=True
    )

    repo1 = model.repository.create_repository(
        namespace, "repo1", None, repo_kind="image", visibility="public"
    )

    manifest_repo = create_manifest(namespace, repo1)

    for i, tag in enumerate(tags):
        # Set the first 4 tags to be old enough to be eligible for pruning
        # We do the -1 to ensure that the creation time is less than the current time
        # + i * 10000 is to ensure time difference between consecutive tags
        creation_time = (
            _past_timestamp_ms("4d") - 1 + i * 1000
            if i < 4
            else int(time.time() * 1000) + i * 10000
        )
        create_tag(repo1, manifest_repo.manifest, start=creation_time, name=tag)

    active_tags, _ = list_repository_tag_history(repo1, 1, 100, active_tags_only=True)
    assert len(active_tags) == len(tags)

    notification.create_repo_notification(
        repo1,
        image_expiry_event.name,
        slack.name,
        {"url": "http://example.com"},
        {"days": 10},
        title="Image(s) will expire in 10 days",
    )
    scan_for_image_expiry_notifications(image_expiry_event.name)
    time.sleep(2)

    job = notification_queue.get()
    assert job is not None
    job = json.loads(job["body"])

    notified_tags = job["event_data"]["tags"]
    assert len(notified_tags) == len(expected)
    for tag_name in expected:
        assert tag_name in notified_tags


@pytest.mark.parametrize(
    "tags, expected, policy1, policy2",
    [
        (
            [
                "test1",
                "test2",
                "test3",
                "test4",
                "test5",
            ],
            ["test1", "test2", "test3"],
            ["creation_date", "4d"],
            ["number_of_tags", 2],
        ),
        (
            [
                "test1",
                "test2",
                "test3",
                "test4",
                "test5",
            ],
            ["test1", "test2", "test3"],
            ["number_of_tags", 2],
            ["number_of_tags", 3],
        ),
    ],
)
def test_notifications_with_repository_autoprune_policy(
    tags, expected, policy1, policy2, initialized_db
):
    if "mysql+pymysql" in os.environ.get("TEST_DATABASE_URI", ""):
        util.notification.SKIP_LOCKED = False
    slack = ExternalNotificationMethod.get(ExternalNotificationMethod.name == "slack")
    image_expiry_event = ExternalNotificationEvent.get(
        ExternalNotificationEvent.name == "repo_image_expiry"
    )
    ns = model.user.get_namespace_user(namespace)

    # deleting existing autoprune policies
    existing_policies = model.autoprune.get_namespace_autoprune_policies_by_id(ns.id)
    for policy in existing_policies:
        model.autoprune.delete_namespace_autoprune_policy(namespace, policy.uuid)

    repo1 = model.repository.create_repository(
        namespace, "repo1", None, repo_kind="image", visibility="public"
    )

    model.autoprune.create_namespace_autoprune_policy(
        namespace, {"method": "number_of_tags", "value": 3}, create_task=True
    )

    model.autoprune.create_repository_autoprune_policy(
        namespace,
        "repo1",
        {
            "method": policy1[0],
            "value": policy1[1],
        },
    )

    model.autoprune.create_repository_autoprune_policy(
        namespace,
        "repo1",
        {
            "method": policy2[0],
            "value": policy2[1],
        },
    )

    manifest_repo = create_manifest(namespace, repo1)

    for i, tag in enumerate(tags):
        # Set the first 2 tags to be old enough to be eligible for pruning
        # We do the -1 to ensure that the creation time is less than the current time
        # + i * 10000 is to ensure time difference between consecutive tags
        creation_time = (
            (_past_timestamp_ms("4d") - 1) + i * 10000
            if i < 2
            else int(time.time() * 1000) + i * 10000
        )
        create_tag(repo1, manifest_repo.manifest, start=creation_time, name=tag)

    active_tags, _ = list_repository_tag_history(repo1, 1, 100, active_tags_only=True)
    assert len(active_tags) == len(tags)

    notification.create_repo_notification(
        repo1,
        image_expiry_event.name,
        slack.name,
        {"url": "http://example.com"},
        {"days": 5},
        title="Image(s) will expire in 5 days",
    )
    scan_for_image_expiry_notifications(image_expiry_event.name)
    time.sleep(2)

    job = notification_queue.get()
    assert job is not None
    job = json.loads(job["body"])

    notified_tags = job["event_data"]["tags"]
    assert len(notified_tags) == len(expected)
    for tag_name in expected:
        assert tag_name in notified_tags


def test_notifications_with_no_tags_expiring_by_autoprune_policy(initialized_db):
    if "mysql+pymysql" in os.environ.get("TEST_DATABASE_URI", ""):
        util.notification.SKIP_LOCKED = False
    slack = ExternalNotificationMethod.get(ExternalNotificationMethod.name == "slack")
    image_expiry_event = ExternalNotificationEvent.get(
        ExternalNotificationEvent.name == "repo_image_expiry"
    )
    ns = model.user.get_namespace_user(namespace)

    # deleting existing autoprune policies
    existing_policies = model.autoprune.get_namespace_autoprune_policies_by_id(ns.id)
    for policy in existing_policies:
        model.autoprune.delete_namespace_autoprune_policy(namespace, policy.uuid)

    repo1 = model.repository.create_repository(
        namespace, "repo1", None, repo_kind="image", visibility="public"
    )

    model.autoprune.create_namespace_autoprune_policy(
        namespace, {"method": "creation_date", "value": "4d"}, create_task=True
    )

    manifest_repo = create_manifest(namespace, repo1)
    tags = ["test1", "test2", "test3", "test4"]

    for i, tag in enumerate(tags):
        create_tag(repo1, manifest_repo.manifest, name=tag)

    active_tags, _ = list_repository_tag_history(repo1, 1, 100, active_tags_only=True)
    assert len(active_tags) == len(tags)

    notification.create_repo_notification(
        repo1,
        image_expiry_event.name,
        slack.name,
        {"url": "http://example.com"},
        {"days": 5},
        title="Image(s) will expire in 5 days",
    )
    scan_for_image_expiry_notifications(image_expiry_event.name)
    time.sleep(2)

    job = notification_queue.get()
    assert job is None
