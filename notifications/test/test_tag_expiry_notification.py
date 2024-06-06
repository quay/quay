import datetime
import json
import os
import time

import pytest

import util
from app import notification_queue
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
    set_tag_end_ms,
)
from endpoints.api.repositorynotification_models_pre_oci import pre_oci_model
from test.fixtures import *
from util.notification import *

namespace = "buynlarge"
repo = "orgrepo"


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
    n_2 = notification.create_repo_notification(
        repo_ref,
        image_expiry_event.name,
        slack.name,
        {"url": "http://example.com"},
        {"days": 10},
        title="Image(s) will expire in 10 days",
    )

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
