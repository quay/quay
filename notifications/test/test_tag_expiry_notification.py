import datetime
import json
import os
import unittest

import util
from app import notification_queue
from data.database import (
    ExternalNotificationMethod,
    TagNotificationSuccess,
    get_epoch_timestamp_ms,
)
from data.model import notification, organization, repository, user
from data.model.oci.tag import (
    delete_tag,
    fetch_repo_tags_for_image_expiry_expiry_event,
    get_most_recent_tag,
    list_alive_tags,
    set_tag_end_ms,
)
from endpoints.api.repositorynotification_models_pre_oci import pre_oci_model
from initdb import finished_database_for_testing, setup_database_for_testing
from test.fixtures import *
from util.notification import *


class TagExpiryNotificationTests(unittest.TestCase):
    def create_tag_expiry_notifications(self):
        self.namespace = "buynlarge"
        self.repo = "orgrepo"
        self.user_1 = user.create_user("user_1", "password", "user_1@testuser.com")
        self.org_1 = organization.create_organization("org1", "org1@devtable.com", self.user_1)
        self.slack = ExternalNotificationMethod.get(ExternalNotificationMethod.name == "slack")
        self.image_expiry_event = ExternalNotificationEvent.get(
            ExternalNotificationEvent.name == "repo_image_expiry"
        )
        self.repo_ref = repository.get_repository(self.namespace, self.repo)
        self.n_1 = pre_oci_model.create_repo_notification(
            namespace_name=self.namespace,
            repository_name=self.repo,
            event_name=self.image_expiry_event.name,
            method_name=self.slack.name,
            method_config={"url": "http://example.com"},
            event_config={"days": 5},
            title="Image(s) will expire in 5 days",
        )
        self.n_2 = notification.create_repo_notification(
            self.repo_ref,
            self.image_expiry_event.name,
            self.slack.name,
            {"url": "http://example.com"},
            {"days": 10},
            title="Image(s) will expire in 10 days",
        )
        self.tag = get_most_recent_tag(self.repo_ref)
        self.tags = list_alive_tags(self.repo_ref)
        for tag in self.tags:
            TagNotificationSuccess.create(
                notification=self.n_1.id, tag=tag.id, method=self.slack.id
            )
            TagNotificationSuccess.create(
                notification=self.n_2.id, tag=tag.id, method=self.slack.id
            )

    def create_new_notification(self):
        return notification.create_repo_notification(
            self.repo_ref,
            self.image_expiry_event.name,
            self.slack.name,
            {"url": "http://example.com"},
            {"days": 7},
            title="Image(s) will expire in 7 days",
        )

    def setUp(self):
        setup_database_for_testing(self)
        self.create_tag_expiry_notifications()

    def tearDown(self):
        finished_database_for_testing(self)

    def test_tag_notifications_for_delete_repo_notification(self):
        tag_event_count = (
            TagNotificationSuccess.select()
            .where(TagNotificationSuccess.notification == self.n_1.id)
            .count()
        )
        assert tag_event_count == len(self.tags)

        notification.delete_repo_notification(self.namespace, self.repo, self.n_1.uuid)
        tag_event_count = (
            TagNotificationSuccess.select()
            .where(TagNotificationSuccess.notification == self.n_1.id)
            .count()
        )
        assert tag_event_count == 0

    def test_delete_tag_notifications_for_notification(self):
        tag_event_count = (
            TagNotificationSuccess.select()
            .where(TagNotificationSuccess.notification == self.n_1.id)
            .count()
        )
        assert tag_event_count == len(self.tags)

        notification.delete_tag_notifications_for_notification(self.n_1.id)
        tag_event_count = (
            TagNotificationSuccess.select()
            .where(TagNotificationSuccess.notification == self.n_1.id)
            .count()
        )
        assert tag_event_count == 0

    def test_delete_tag_notifications_for_tag(self):
        tag_event_count = (
            TagNotificationSuccess.select()
            .where(TagNotificationSuccess.tag == self.tags[0].id)
            .count()
        )
        assert tag_event_count == 2

        notification.delete_tag_notifications_for_tag(self.tags[0])
        tag_event_count = (
            TagNotificationSuccess.select()
            .where(TagNotificationSuccess.tag == self.tags[0].id)
            .count()
        )
        assert tag_event_count == 0

    def test_fetch_tags_to_notify(self):
        event = self.create_new_notification()
        tag_event_count = (
            TagNotificationSuccess.select()
            .where(TagNotificationSuccess.notification == event.id)
            .count()
        )
        assert tag_event_count == 0

        track_tags_to_notify(self.tags, event)

        tag_event_count = (
            TagNotificationSuccess.select()
            .where(TagNotificationSuccess.notification == event.id)
            .count()
        )
        assert tag_event_count == len(self.tags)

    def test_fetch_notified_tag_ids_for_event(self):
        tag_ids = fetch_notified_tag_ids_for_event(self.n_2)
        for tag in self.tags:
            assert tag.id in tag_ids

    def test_fetch_active_notification(self):
        if "mysql+pymysql" in os.environ.get("TEST_DATABASE_URI", ""):
            util.notification.SKIP_LOCKED = False
        event = self.create_new_notification()
        # causing the event to failure
        for i in range(3):
            notification.increment_notification_failure_count(event)

        # creating a `repo_push` event type
        notification.create_repo_notification(
            self.repo_ref,
            "repo_push",
            self.slack.name,
            {"url": "http://example.com"},
            {"days": 7},
            title="Image(s) will expire in 7 days",
        )

        time_now = get_epoch_timestamp_ms()
        event = fetch_active_notification(self.image_expiry_event)
        assert event.id == self.n_1.id
        event = (
            RepositoryNotification.select().where(RepositoryNotification.id == self.n_1.id).get()
        )
        assert event.last_ran_ms >= time_now

    def test_scan_for_image_expiry_notifications(self):
        if "mysql+pymysql" in os.environ.get("TEST_DATABASE_URI", ""):
            util.notification.SKIP_LOCKED = False
        future_ms = (datetime.datetime.now() + datetime.timedelta(days=1)).timestamp() * 1000
        for tag in self.tags:
            set_tag_end_ms(tag, future_ms)
        scan_for_image_expiry_notifications(self.image_expiry_event.name)

        job1 = notification_queue.get()
        assert job1 is not None
        job1 = json.loads(job1["body"])
        for tag in self.tags:
            assert tag.name in job1["event_data"]["tags"]

        job2 = notification_queue.get()
        assert job2 is not None
        job2 = json.loads(job2["body"])
        for tag in self.tags:
            assert tag.name in job2["event_data"]["tags"]

    def test_fetch_repo_tags_for_image_expiry_expiry_event(self):
        future_ms = (datetime.datetime.now() + datetime.timedelta(days=1)).timestamp() * 1000
        expected_tags = []
        for tag in self.tags:
            if tag.name == "prod":
                continue
            set_tag_end_ms(tag, future_ms)
            expected_tags.append(tag.id)
        tags = fetch_repo_tags_for_image_expiry_expiry_event(
            self.repo_ref.id, days=2, notified_tags=[]
        )
        assert len(tags) == len(expected_tags)
        for tag in tags:
            assert tag.id in expected_tags

    def test_notifications_on_tag_expiry_update(self):
        tag_event_count = (
            TagNotificationSuccess.select()
            .where(TagNotificationSuccess.notification == self.n_1.id)
            .count()
        )
        assert tag_event_count == len(self.tags)

        for tag in self.tags:
            set_tag_end_ms(tag, get_epoch_timestamp_ms())

        tag_event_count = (
            TagNotificationSuccess.select()
            .where(TagNotificationSuccess.notification == self.n_1.id)
            .count()
        )
        assert tag_event_count == 0

    def test_notifications_on_tag_delete(self):
        for tag in self.tags:
            delete_tag(self.repo_ref.id, tag.name)

        tag_event_count = (
            TagNotificationSuccess.select()
            .where(TagNotificationSuccess.notification == self.n_1.id)
            .count()
        )
        assert tag_event_count == 0
