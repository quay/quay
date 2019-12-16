import json
import time
import unittest

from app import app, storage, notification_queue, url_scheme_and_hostname
from .data import model
from .data.database import Image, IMAGE_NOT_SCANNED_ENGINE_VERSION
from endpoints.v2 import v2_bp
from initdb import setup_database_for_testing, finished_database_for_testing
from notifications.notificationevent import VulnerabilityFoundEvent
from util.secscan.secscan_util import get_blob_download_uri_getter
from util.morecollections import AttrDict
from util.secscan.api import SecurityScannerAPI, APIRequestFailure
from util.secscan.analyzer import LayerAnalyzer
from util.secscan.fake import fake_security_scanner
from util.secscan.notifier import SecurityNotificationHandler, ProcessNotificationPageResult
from util.security.instancekeys import InstanceKeys
from workers.security_notification_worker import SecurityNotificationWorker


ADMIN_ACCESS_USER = "devtable"
SIMPLE_REPO = "simple"
COMPLEX_REPO = "complex"


def process_notification_data(legacy_api, notification_data):
    handler = SecurityNotificationHandler(legacy_api, 100)
    result = handler.process_notification_page_data(notification_data)
    handler.send_notifications()
    return result == ProcessNotificationPageResult.FINISHED_PROCESSING


class TestSecurityScanner(unittest.TestCase):
    def setUp(self):
        # Enable direct download in fake storage.
        storage.put_content(["local_us"], "supports_direct_download", "true")

        # Have fake storage say all files exist for the duration of the test.
        storage.put_content(["local_us"], "all_files_exist", "true")

        # Setup the database with fake storage.
        setup_database_for_testing(self)
        self.app = app.test_client()
        self.ctx = app.test_request_context()
        self.ctx.__enter__()

        instance_keys = InstanceKeys(app)
        self.api = SecurityScannerAPI(
            app.config,
            storage,
            app.config["SERVER_HOSTNAME"],
            app.config["HTTPCLIENT"],
            uri_creator=get_blob_download_uri_getter(
                app.test_request_context("/"), url_scheme_and_hostname
            ),
            instance_keys=instance_keys,
        )

    def tearDown(self):
        storage.remove(["local_us"], "supports_direct_download")
        storage.remove(["local_us"], "all_files_exist")

        finished_database_for_testing(self)
        self.ctx.__exit__(True, None, None)

    def assertAnalyzed(self, layer, security_scanner, isAnalyzed, engineVersion):
        self.assertEqual(isAnalyzed, layer.security_indexed)
        self.assertEqual(engineVersion, layer.security_indexed_engine)

        if isAnalyzed:
            self.assertTrue(security_scanner.has_layer(security_scanner.layer_id(layer)))

            # Ensure all parent layers are marked as analyzed.
            parents = model.image.get_parent_images(ADMIN_ACCESS_USER, SIMPLE_REPO, layer)
            for parent in parents:
                self.assertTrue(parent.security_indexed)
                self.assertEqual(engineVersion, parent.security_indexed_engine)
                self.assertTrue(security_scanner.has_layer(security_scanner.layer_id(parent)))

    def test_get_layer(self):
        """
        Test for basic retrieval of layers from the security scanner.
        """
        layer = model.tag.get_tag_image(
            ADMIN_ACCESS_USER, SIMPLE_REPO, "latest", include_storage=True
        )

        with fake_security_scanner() as security_scanner:
            # Ensure the layer doesn't exist yet.
            self.assertFalse(security_scanner.has_layer(security_scanner.layer_id(layer)))
            self.assertIsNone(self.api.get_layer_data(layer))

            # Add the layer.
            security_scanner.add_layer(security_scanner.layer_id(layer))

            # Retrieve the results.
            result = self.api.get_layer_data(layer, include_vulnerabilities=True)
            self.assertIsNotNone(result)
            self.assertEqual(result["Layer"]["Name"], security_scanner.layer_id(layer))

    def test_analyze_layer_nodirectdownload_success(self):
        """
        Tests analyzing a layer when direct download is disabled.
        """

        # Disable direct download in fake storage.
        storage.put_content(["local_us"], "supports_direct_download", "false")

        try:
            app.register_blueprint(v2_bp, url_prefix="/v2")
        except:
            # Already registered.
            pass

        layer = model.tag.get_tag_image(
            ADMIN_ACCESS_USER, SIMPLE_REPO, "latest", include_storage=True
        )
        self.assertFalse(layer.security_indexed)
        self.assertEqual(-1, layer.security_indexed_engine)

        # Ensure that the download is a registry+JWT download.
        uri, auth_header = self.api._get_image_url_and_auth(layer)
        self.assertIsNotNone(uri)
        self.assertIsNotNone(auth_header)

        # Ensure the download doesn't work without the header.
        rv = self.app.head(uri)
        self.assertEqual(rv.status_code, 401)

        # Ensure the download works with the header. Note we use a HEAD here, as GET causes DB
        # access which messes with the test runner's rollback.
        rv = self.app.head(uri, headers=[("authorization", auth_header)])
        self.assertEqual(rv.status_code, 200)

        # Ensure the code works when called via analyze.
        with fake_security_scanner() as security_scanner:
            analyzer = LayerAnalyzer(app.config, self.api)
            analyzer.analyze_recursively(layer)

            layer = model.tag.get_tag_image(ADMIN_ACCESS_USER, SIMPLE_REPO, "latest")
            self.assertAnalyzed(layer, security_scanner, True, 1)

    def test_analyze_layer_success(self):
        """
        Tests that analyzing a layer successfully marks it as analyzed.
        """

        layer = model.tag.get_tag_image(
            ADMIN_ACCESS_USER, SIMPLE_REPO, "latest", include_storage=True
        )
        self.assertFalse(layer.security_indexed)
        self.assertEqual(-1, layer.security_indexed_engine)

        with fake_security_scanner() as security_scanner:
            analyzer = LayerAnalyzer(app.config, self.api)
            analyzer.analyze_recursively(layer)

            layer = model.tag.get_tag_image(ADMIN_ACCESS_USER, SIMPLE_REPO, "latest")
            self.assertAnalyzed(layer, security_scanner, True, 1)

    def test_analyze_layer_failure(self):
        """
        Tests that failing to analyze a layer (because it 422s) marks it as analyzed but failed.
        """

        layer = model.tag.get_tag_image(
            ADMIN_ACCESS_USER, SIMPLE_REPO, "latest", include_storage=True
        )
        self.assertFalse(layer.security_indexed)
        self.assertEqual(-1, layer.security_indexed_engine)

        with fake_security_scanner() as security_scanner:
            security_scanner.set_fail_layer_id(security_scanner.layer_id(layer))

            analyzer = LayerAnalyzer(app.config, self.api)
            analyzer.analyze_recursively(layer)

            layer = model.tag.get_tag_image(ADMIN_ACCESS_USER, SIMPLE_REPO, "latest")
            self.assertAnalyzed(layer, security_scanner, False, 1)

    def test_analyze_layer_internal_error(self):
        """
        Tests that failing to analyze a layer (because it 500s) marks it as not analyzed.
        """

        layer = model.tag.get_tag_image(
            ADMIN_ACCESS_USER, SIMPLE_REPO, "latest", include_storage=True
        )
        self.assertFalse(layer.security_indexed)
        self.assertEqual(-1, layer.security_indexed_engine)

        with fake_security_scanner() as security_scanner:
            security_scanner.set_internal_error_layer_id(security_scanner.layer_id(layer))

            analyzer = LayerAnalyzer(app.config, self.api)
            with self.assertRaises(APIRequestFailure):
                analyzer.analyze_recursively(layer)

            layer = model.tag.get_tag_image(ADMIN_ACCESS_USER, SIMPLE_REPO, "latest")
            self.assertAnalyzed(layer, security_scanner, False, -1)

    def test_analyze_layer_error(self):
        """
        Tests that failing to analyze a layer (because it 400s) marks it as analyzed but failed.
        """

        layer = model.tag.get_tag_image(
            ADMIN_ACCESS_USER, SIMPLE_REPO, "latest", include_storage=True
        )
        self.assertFalse(layer.security_indexed)
        self.assertEqual(-1, layer.security_indexed_engine)

        with fake_security_scanner() as security_scanner:
            # Make is so trying to analyze the parent will fail with an error.
            security_scanner.set_error_layer_id(security_scanner.layer_id(layer.parent))

            # Try to the layer and its parents, but with one request causing an error.
            analyzer = LayerAnalyzer(app.config, self.api)
            analyzer.analyze_recursively(layer)

            # Make sure it is marked as analyzed, but in a failed state.
            layer = model.tag.get_tag_image(ADMIN_ACCESS_USER, SIMPLE_REPO, "latest")
            self.assertAnalyzed(layer, security_scanner, False, 1)

    def test_analyze_layer_unexpected_status(self):
        """
        Tests that a response from a scanner with an unexpected status code fails correctly.
        """

        layer = model.tag.get_tag_image(
            ADMIN_ACCESS_USER, SIMPLE_REPO, "latest", include_storage=True
        )
        self.assertFalse(layer.security_indexed)
        self.assertEqual(-1, layer.security_indexed_engine)

        with fake_security_scanner() as security_scanner:
            # Make is so trying to analyze the parent will fail with an error.
            security_scanner.set_unexpected_status_layer_id(security_scanner.layer_id(layer.parent))

            # Try to the layer and its parents, but with one request causing an error.
            analyzer = LayerAnalyzer(app.config, self.api)
            with self.assertRaises(APIRequestFailure):
                analyzer.analyze_recursively(layer)

            # Make sure it isn't analyzed.
            layer = model.tag.get_tag_image(ADMIN_ACCESS_USER, SIMPLE_REPO, "latest")
            self.assertAnalyzed(layer, security_scanner, False, -1)

    def test_analyze_layer_missing_parent_handled(self):
        """
        Tests that a missing parent causes an automatic reanalysis, which succeeds.
        """

        layer = model.tag.get_tag_image(
            ADMIN_ACCESS_USER, SIMPLE_REPO, "latest", include_storage=True
        )
        self.assertFalse(layer.security_indexed)
        self.assertEqual(-1, layer.security_indexed_engine)

        with fake_security_scanner() as security_scanner:
            # Analyze the layer and its parents.
            analyzer = LayerAnalyzer(app.config, self.api)
            analyzer.analyze_recursively(layer)

            # Make sure it was analyzed.
            layer = model.tag.get_tag_image(ADMIN_ACCESS_USER, SIMPLE_REPO, "latest")
            self.assertAnalyzed(layer, security_scanner, True, 1)

            # Mark the layer as not yet scanned.
            layer.security_indexed_engine = IMAGE_NOT_SCANNED_ENGINE_VERSION
            layer.security_indexed = False
            layer.save()

            # Remove the layer's parent entirely from the security scanner.
            security_scanner.remove_layer(security_scanner.layer_id(layer.parent))

            # Analyze again, which should properly re-analyze the missing parent and this layer.
            analyzer.analyze_recursively(layer)

            layer = model.tag.get_tag_image(ADMIN_ACCESS_USER, SIMPLE_REPO, "latest")
            self.assertAnalyzed(layer, security_scanner, True, 1)

    def test_analyze_layer_invalid_parent(self):
        """
        Tests that trying to reanalyze a parent that is invalid causes the layer to be marked as
        analyzed, but failed.
        """

        layer = model.tag.get_tag_image(
            ADMIN_ACCESS_USER, SIMPLE_REPO, "latest", include_storage=True
        )
        self.assertFalse(layer.security_indexed)
        self.assertEqual(-1, layer.security_indexed_engine)

        with fake_security_scanner() as security_scanner:
            # Analyze the layer and its parents.
            analyzer = LayerAnalyzer(app.config, self.api)
            analyzer.analyze_recursively(layer)

            # Make sure it was analyzed.
            layer = model.tag.get_tag_image(ADMIN_ACCESS_USER, SIMPLE_REPO, "latest")
            self.assertAnalyzed(layer, security_scanner, True, 1)

            # Mark the layer as not yet scanned.
            layer.security_indexed_engine = IMAGE_NOT_SCANNED_ENGINE_VERSION
            layer.security_indexed = False
            layer.save()

            # Remove the layer's parent entirely from the security scanner.
            security_scanner.remove_layer(security_scanner.layer_id(layer.parent))

            # Make is so trying to analyze the parent will fail.
            security_scanner.set_error_layer_id(security_scanner.layer_id(layer.parent))

            # Try to analyze again, which should try to reindex the parent and fail.
            analyzer.analyze_recursively(layer)

            layer = model.tag.get_tag_image(ADMIN_ACCESS_USER, SIMPLE_REPO, "latest")
            self.assertAnalyzed(layer, security_scanner, False, 1)

    def test_analyze_layer_unsupported_parent(self):
        """
        Tests that attempting to analyze a layer whose parent is unanalyzable, results in the layer
        being marked as analyzed, but failed.
        """

        layer = model.tag.get_tag_image(
            ADMIN_ACCESS_USER, SIMPLE_REPO, "latest", include_storage=True
        )
        self.assertFalse(layer.security_indexed)
        self.assertEqual(-1, layer.security_indexed_engine)

        with fake_security_scanner() as security_scanner:
            # Make is so trying to analyze the parent will fail.
            security_scanner.set_fail_layer_id(security_scanner.layer_id(layer.parent))

            # Attempt to the layer and its parents. This should mark the layer itself as unanalyzable.
            analyzer = LayerAnalyzer(app.config, self.api)
            analyzer.analyze_recursively(layer)

            layer = model.tag.get_tag_image(ADMIN_ACCESS_USER, SIMPLE_REPO, "latest")
            self.assertAnalyzed(layer, security_scanner, False, 1)

    def test_analyze_layer_missing_storage(self):
        """
        Tests trying to analyze a layer with missing storage.
        """

        layer = model.tag.get_tag_image(
            ADMIN_ACCESS_USER, SIMPLE_REPO, "latest", include_storage=True
        )
        self.assertFalse(layer.security_indexed)
        self.assertEqual(-1, layer.security_indexed_engine)

        # Delete the storage for the layer.
        path = model.storage.get_layer_path(layer.storage)
        locations = app.config["DISTRIBUTED_STORAGE_PREFERENCE"]
        storage.remove(locations, path)
        storage.remove(locations, "all_files_exist")

        with fake_security_scanner() as security_scanner:
            analyzer = LayerAnalyzer(app.config, self.api)
            analyzer.analyze_recursively(layer)

            layer = model.tag.get_tag_image(ADMIN_ACCESS_USER, SIMPLE_REPO, "latest")
            self.assertAnalyzed(layer, security_scanner, False, 1)

    def assert_analyze_layer_notify(
        self, security_indexed_engine, security_indexed, expect_notification
    ):
        layer = model.tag.get_tag_image(
            ADMIN_ACCESS_USER, SIMPLE_REPO, "latest", include_storage=True
        )
        self.assertFalse(layer.security_indexed)
        self.assertEqual(-1, layer.security_indexed_engine)

        # Ensure there are no existing events.
        self.assertIsNone(notification_queue.get())

        # Add a repo event for the layer.
        repo = model.repository.get_repository(ADMIN_ACCESS_USER, SIMPLE_REPO)
        model.notification.create_repo_notification(
            repo, "vulnerability_found", "quay_notification", {}, {"level": 100}
        )

        # Update the layer's state before analyzing.
        layer.security_indexed_engine = security_indexed_engine
        layer.security_indexed = security_indexed
        layer.save()

        with fake_security_scanner() as security_scanner:
            security_scanner.set_vulns(
                security_scanner.layer_id(layer),
                [
                    {
                        "Name": "CVE-2014-9471",
                        "Namespace": "debian:8",
                        "Description": "Some service",
                        "Link": "https://security-tracker.debian.org/tracker/CVE-2014-9471",
                        "Severity": "Low",
                        "FixedBy": "9.23-5",
                    },
                    {
                        "Name": "CVE-2016-7530",
                        "Namespace": "debian:8",
                        "Description": "Some other service",
                        "Link": "https://security-tracker.debian.org/tracker/CVE-2016-7530",
                        "Severity": "Unknown",
                        "FixedBy": "19.343-2",
                    },
                ],
            )

            analyzer = LayerAnalyzer(app.config, self.api)
            analyzer.analyze_recursively(layer)

            layer = model.tag.get_tag_image(ADMIN_ACCESS_USER, SIMPLE_REPO, "latest")
            self.assertAnalyzed(layer, security_scanner, True, 1)

        # Ensure an event was written for the tag (if necessary).
        time.sleep(1)
        queue_item = notification_queue.get()

        if expect_notification:
            self.assertIsNotNone(queue_item)

            body = json.loads(queue_item.body)
            self.assertEqual(set(["latest", "prod"]), set(body["event_data"]["tags"]))
            self.assertEqual("CVE-2014-9471", body["event_data"]["vulnerability"]["id"])
            self.assertEqual("Low", body["event_data"]["vulnerability"]["priority"])
            self.assertTrue(body["event_data"]["vulnerability"]["has_fix"])

            self.assertEqual("CVE-2014-9471", body["event_data"]["vulnerabilities"][0]["id"])
            self.assertEqual(2, len(body["event_data"]["vulnerabilities"]))

            # Ensure we get the correct event message out as well.
            event = VulnerabilityFoundEvent()
            msg = "1 Low and 1 more vulnerabilities were detected in repository devtable/simple in 2 tags"
            self.assertEqual(msg, event.get_summary(body["event_data"], {}))
            self.assertEqual("info", event.get_level(body["event_data"], {}))
        else:
            self.assertIsNone(queue_item)

        # Ensure its security indexed engine was updated.
        updated_layer = model.tag.get_tag_image(ADMIN_ACCESS_USER, SIMPLE_REPO, "latest")
        self.assertEqual(updated_layer.id, layer.id)
        self.assertTrue(updated_layer.security_indexed_engine > 0)

    def test_analyze_layer_success_events(self):
        # Not previously indexed at all => Notification
        self.assert_analyze_layer_notify(IMAGE_NOT_SCANNED_ENGINE_VERSION, False, True)

    def test_analyze_layer_success_no_notification(self):
        # Previously successfully indexed => No notification
        self.assert_analyze_layer_notify(0, True, False)

    def test_analyze_layer_failed_then_success_notification(self):
        # Previously failed to index => Notification
        self.assert_analyze_layer_notify(0, False, True)

    def test_notification_new_layers_not_vulnerable(self):
        layer = model.tag.get_tag_image(
            ADMIN_ACCESS_USER, SIMPLE_REPO, "latest", include_storage=True
        )
        layer_id = "%s.%s" % (layer.docker_image_id, layer.storage.uuid)

        # Add a repo event for the layer.
        repo = model.repository.get_repository(ADMIN_ACCESS_USER, SIMPLE_REPO)
        model.notification.create_repo_notification(
            repo, "vulnerability_found", "quay_notification", {}, {"level": 100}
        )

        # Ensure that there are no event queue items for the layer.
        self.assertIsNone(notification_queue.get())

        # Fire off the notification processing.
        with fake_security_scanner() as security_scanner:
            analyzer = LayerAnalyzer(app.config, self.api)
            analyzer.analyze_recursively(layer)

            layer = model.tag.get_tag_image(ADMIN_ACCESS_USER, SIMPLE_REPO, "latest")
            self.assertAnalyzed(layer, security_scanner, True, 1)

            # Add a notification for the layer.
            notification_data = security_scanner.add_notification([layer_id], [], {}, {})

            # Process the notification.
            self.assertTrue(process_notification_data(self.api, notification_data))

            # Ensure that there are no event queue items for the layer.
            self.assertIsNone(notification_queue.get())

    def test_notification_delete(self):
        layer = model.tag.get_tag_image(
            ADMIN_ACCESS_USER, SIMPLE_REPO, "latest", include_storage=True
        )
        layer_id = "%s.%s" % (layer.docker_image_id, layer.storage.uuid)

        # Add a repo event for the layer.
        repo = model.repository.get_repository(ADMIN_ACCESS_USER, SIMPLE_REPO)
        model.notification.create_repo_notification(
            repo, "vulnerability_found", "quay_notification", {}, {"level": 100}
        )

        # Ensure that there are no event queue items for the layer.
        self.assertIsNone(notification_queue.get())

        # Fire off the notification processing.
        with fake_security_scanner() as security_scanner:
            analyzer = LayerAnalyzer(app.config, self.api)
            analyzer.analyze_recursively(layer)

            layer = model.tag.get_tag_image(ADMIN_ACCESS_USER, SIMPLE_REPO, "latest")
            self.assertAnalyzed(layer, security_scanner, True, 1)

            # Add a notification for the layer.
            notification_data = security_scanner.add_notification([layer_id], None, {}, None)

            # Process the notification.
            self.assertTrue(process_notification_data(self.api, notification_data))

            # Ensure that there are no event queue items for the layer.
            self.assertIsNone(notification_queue.get())

    def test_notification_new_layers(self):
        layer = model.tag.get_tag_image(
            ADMIN_ACCESS_USER, SIMPLE_REPO, "latest", include_storage=True
        )
        layer_id = "%s.%s" % (layer.docker_image_id, layer.storage.uuid)

        # Add a repo event for the layer.
        repo = model.repository.get_repository(ADMIN_ACCESS_USER, SIMPLE_REPO)
        model.notification.create_repo_notification(
            repo, "vulnerability_found", "quay_notification", {}, {"level": 100}
        )

        # Ensure that there are no event queue items for the layer.
        self.assertIsNone(notification_queue.get())

        # Fire off the notification processing.
        with fake_security_scanner() as security_scanner:
            analyzer = LayerAnalyzer(app.config, self.api)
            analyzer.analyze_recursively(layer)

            layer = model.tag.get_tag_image(ADMIN_ACCESS_USER, SIMPLE_REPO, "latest")
            self.assertAnalyzed(layer, security_scanner, True, 1)

            vuln_info = {
                "Name": "CVE-TEST",
                "Namespace": "debian:8",
                "Description": "Some service",
                "Link": "https://security-tracker.debian.org/tracker/CVE-2014-9471",
                "Severity": "Low",
                "FixedIn": {"Version": "9.23-5"},
            }
            security_scanner.set_vulns(layer_id, [vuln_info])

            # Add a notification for the layer.
            notification_data = security_scanner.add_notification(
                [], [layer_id], vuln_info, vuln_info
            )

            # Process the notification.
            self.assertTrue(process_notification_data(self.api, notification_data))

            # Ensure an event was written for the tag.
            time.sleep(1)
            queue_item = notification_queue.get()
            self.assertIsNotNone(queue_item)

            item_body = json.loads(queue_item.body)
            self.assertEqual(sorted(["prod", "latest"]), sorted(item_body["event_data"]["tags"]))
            self.assertEqual("CVE-TEST", item_body["event_data"]["vulnerability"]["id"])
            self.assertEqual("Low", item_body["event_data"]["vulnerability"]["priority"])
            self.assertTrue(item_body["event_data"]["vulnerability"]["has_fix"])

    def test_notification_no_new_layers(self):
        layer = model.tag.get_tag_image(
            ADMIN_ACCESS_USER, SIMPLE_REPO, "latest", include_storage=True
        )

        # Add a repo event for the layer.
        repo = model.repository.get_repository(ADMIN_ACCESS_USER, SIMPLE_REPO)
        model.notification.create_repo_notification(
            repo, "vulnerability_found", "quay_notification", {}, {"level": 100}
        )

        # Ensure that there are no event queue items for the layer.
        self.assertIsNone(notification_queue.get())

        # Fire off the notification processing.
        with fake_security_scanner() as security_scanner:
            analyzer = LayerAnalyzer(app.config, self.api)
            analyzer.analyze_recursively(layer)

            layer = model.tag.get_tag_image(ADMIN_ACCESS_USER, SIMPLE_REPO, "latest")
            self.assertAnalyzed(layer, security_scanner, True, 1)

            # Add a notification for the layer.
            notification_data = security_scanner.add_notification([], [], {}, {})

            # Process the notification.
            self.assertTrue(process_notification_data(self.api, notification_data))

            # Ensure that there are no event queue items for the layer.
            self.assertIsNone(notification_queue.get())

    def notification_tuple(self, notification):
        # TODO: Replace this with a method once we refactor the notification stuff into its
        # own module.
        return AttrDict(
            {
                "event_config_dict": json.loads(notification.event_config_json),
                "method_config_dict": json.loads(notification.config_json),
            }
        )

    def test_notification_no_new_layers_increased_severity(self):
        layer = model.tag.get_tag_image(
            ADMIN_ACCESS_USER, SIMPLE_REPO, "latest", include_storage=True
        )
        layer_id = "%s.%s" % (layer.docker_image_id, layer.storage.uuid)

        # Add a repo event for the layer.
        repo = model.repository.get_repository(ADMIN_ACCESS_USER, SIMPLE_REPO)
        notification = model.notification.create_repo_notification(
            repo, "vulnerability_found", "quay_notification", {}, {"level": 100}
        )

        # Ensure that there are no event queue items for the layer.
        self.assertIsNone(notification_queue.get())

        # Fire off the notification processing.
        with fake_security_scanner() as security_scanner:
            analyzer = LayerAnalyzer(app.config, self.api)
            analyzer.analyze_recursively(layer)

            layer = model.tag.get_tag_image(ADMIN_ACCESS_USER, SIMPLE_REPO, "latest")
            self.assertAnalyzed(layer, security_scanner, True, 1)

            old_vuln_info = {
                "Name": "CVE-TEST",
                "Namespace": "debian:8",
                "Description": "Some service",
                "Link": "https://security-tracker.debian.org/tracker/CVE-2014-9471",
                "Severity": "Low",
            }

            new_vuln_info = {
                "Name": "CVE-TEST",
                "Namespace": "debian:8",
                "Description": "Some service",
                "Link": "https://security-tracker.debian.org/tracker/CVE-2014-9471",
                "Severity": "Critical",
                "FixedIn": {"Version": "9.23-5"},
            }

            security_scanner.set_vulns(layer_id, [new_vuln_info])

            # Add a notification for the layer.
            notification_data = security_scanner.add_notification(
                [layer_id], [layer_id], old_vuln_info, new_vuln_info
            )

            # Process the notification.
            self.assertTrue(process_notification_data(self.api, notification_data))

            # Ensure an event was written for the tag.
            time.sleep(1)
            queue_item = notification_queue.get()
            self.assertIsNotNone(queue_item)

            item_body = json.loads(queue_item.body)
            self.assertEqual(sorted(["prod", "latest"]), sorted(item_body["event_data"]["tags"]))
            self.assertEqual("CVE-TEST", item_body["event_data"]["vulnerability"]["id"])
            self.assertEqual("Critical", item_body["event_data"]["vulnerability"]["priority"])
            self.assertTrue(item_body["event_data"]["vulnerability"]["has_fix"])

            # Verify that an event would be raised.
            event_data = item_body["event_data"]
            notification = self.notification_tuple(notification)
            self.assertTrue(VulnerabilityFoundEvent().should_perform(event_data, notification))

            # Create another notification with a matching level and verify it will be raised.
            notification = model.notification.create_repo_notification(
                repo, "vulnerability_found", "quay_notification", {}, {"level": 1}
            )

            notification = self.notification_tuple(notification)
            self.assertTrue(VulnerabilityFoundEvent().should_perform(event_data, notification))

            # Create another notification with a higher level and verify it won't be raised.
            notification = model.notification.create_repo_notification(
                repo, "vulnerability_found", "quay_notification", {}, {"level": 0}
            )
            notification = self.notification_tuple(notification)
            self.assertFalse(VulnerabilityFoundEvent().should_perform(event_data, notification))

    def test_select_images_to_scan(self):
        # Set all images to have a security index of a version to that of the config.
        expected_version = app.config["SECURITY_SCANNER_ENGINE_VERSION_TARGET"]
        Image.update(security_indexed_engine=expected_version).execute()

        # Ensure no images are available for scanning.
        self.assertIsNone(model.image.get_min_id_for_sec_scan(expected_version))
        self.assertTrue(len(model.image.get_images_eligible_for_scan(expected_version)) == 0)

        # Check for a higher version.
        self.assertIsNotNone(model.image.get_min_id_for_sec_scan(expected_version + 1))
        self.assertTrue(len(model.image.get_images_eligible_for_scan(expected_version + 1)) > 0)

    def test_notification_worker(self):
        layer1 = model.tag.get_tag_image(
            ADMIN_ACCESS_USER, SIMPLE_REPO, "latest", include_storage=True
        )
        layer2 = model.tag.get_tag_image(
            ADMIN_ACCESS_USER, COMPLEX_REPO, "prod", include_storage=True
        )

        # Add a repo events for the layers.
        simple_repo = model.repository.get_repository(ADMIN_ACCESS_USER, SIMPLE_REPO)
        complex_repo = model.repository.get_repository(ADMIN_ACCESS_USER, COMPLEX_REPO)

        model.notification.create_repo_notification(
            simple_repo, "vulnerability_found", "quay_notification", {}, {"level": 100}
        )
        model.notification.create_repo_notification(
            complex_repo, "vulnerability_found", "quay_notification", {}, {"level": 100}
        )

        # Ensure that there are no event queue items for the layer.
        self.assertIsNone(notification_queue.get())

        with fake_security_scanner() as security_scanner:
            # Test with an unknown notification.
            worker = SecurityNotificationWorker(None)
            self.assertFalse(worker.perform_notification_work({"Name": "unknownnotification"}))

            # Add some analyzed layers.
            analyzer = LayerAnalyzer(app.config, self.api)
            analyzer.analyze_recursively(layer1)
            analyzer.analyze_recursively(layer2)

            # Add a notification with pages of data.
            new_vuln_info = {
                "Name": "CVE-TEST",
                "Namespace": "debian:8",
                "Description": "Some service",
                "Link": "https://security-tracker.debian.org/tracker/CVE-2014-9471",
                "Severity": "Critical",
                "FixedIn": {"Version": "9.23-5"},
            }

            security_scanner.set_vulns(security_scanner.layer_id(layer1), [new_vuln_info])
            security_scanner.set_vulns(security_scanner.layer_id(layer2), [new_vuln_info])

            layer_ids = [security_scanner.layer_id(layer1), security_scanner.layer_id(layer2)]
            notification_data = security_scanner.add_notification(
                [], layer_ids, None, new_vuln_info
            )

            # Test with a known notification with pages.
            data = {
                "Name": notification_data["Name"],
            }

            worker = SecurityNotificationWorker(None)
            self.assertTrue(worker.perform_notification_work(data, layer_limit=2))

            # Make sure all pages were processed by ensuring we have two notifications.
            time.sleep(1)
            self.assertIsNotNone(notification_queue.get())
            self.assertIsNotNone(notification_queue.get())

    def test_notification_worker_offset_pages_not_indexed(self):
        # Try without indexes.
        self.assert_notification_worker_offset_pages(indexed=False)

    def test_notification_worker_offset_pages_indexed(self):
        # Try with indexes.
        self.assert_notification_worker_offset_pages(indexed=True)

    def assert_notification_worker_offset_pages(self, indexed=False):
        layer1 = model.tag.get_tag_image(
            ADMIN_ACCESS_USER, SIMPLE_REPO, "latest", include_storage=True
        )
        layer2 = model.tag.get_tag_image(
            ADMIN_ACCESS_USER, COMPLEX_REPO, "prod", include_storage=True
        )

        # Add a repo events for the layers.
        simple_repo = model.repository.get_repository(ADMIN_ACCESS_USER, SIMPLE_REPO)
        complex_repo = model.repository.get_repository(ADMIN_ACCESS_USER, COMPLEX_REPO)

        model.notification.create_repo_notification(
            simple_repo, "vulnerability_found", "quay_notification", {}, {"level": 100}
        )
        model.notification.create_repo_notification(
            complex_repo, "vulnerability_found", "quay_notification", {}, {"level": 100}
        )

        # Ensure that there are no event queue items for the layer.
        self.assertIsNone(notification_queue.get())

        with fake_security_scanner() as security_scanner:
            # Test with an unknown notification.
            worker = SecurityNotificationWorker(None)
            self.assertFalse(worker.perform_notification_work({"Name": "unknownnotification"}))

            # Add some analyzed layers.
            analyzer = LayerAnalyzer(app.config, self.api)
            analyzer.analyze_recursively(layer1)
            analyzer.analyze_recursively(layer2)

            # Add a notification with pages of data.
            new_vuln_info = {
                "Name": "CVE-TEST",
                "Namespace": "debian:8",
                "Description": "Some service",
                "Link": "https://security-tracker.debian.org/tracker/CVE-2014-9471",
                "Severity": "Critical",
                "FixedIn": {"Version": "9.23-5"},
            }

            security_scanner.set_vulns(security_scanner.layer_id(layer1), [new_vuln_info])
            security_scanner.set_vulns(security_scanner.layer_id(layer2), [new_vuln_info])

            # Define offsetting sets of layer IDs, to test cross-pagination support. In this test, we
            # will only serve 2 layer IDs per page: the first page will serve both of the 'New' layer IDs,
            # but since the first 2 'Old' layer IDs are "earlier" than the shared ID of
            # `devtable/simple:latest`, they won't get served in the 'New' list until the *second* page.
            # The notification handling system should correctly not notify for this layer, even though it
            # is marked 'New' on page 1 and marked 'Old' on page 2. Clair will served these
            # IDs sorted in the same manner.
            idx_old_layer_ids = [
                {"LayerName": "old1", "Index": 1},
                {"LayerName": "old2", "Index": 2},
                {"LayerName": security_scanner.layer_id(layer1), "Index": 3},
            ]

            idx_new_layer_ids = [
                {"LayerName": security_scanner.layer_id(layer1), "Index": 3},
                {"LayerName": security_scanner.layer_id(layer2), "Index": 4},
            ]

            old_layer_ids = [t["LayerName"] for t in idx_old_layer_ids]
            new_layer_ids = [t["LayerName"] for t in idx_new_layer_ids]

            if not indexed:
                idx_old_layer_ids = None
                idx_new_layer_ids = None

            notification_data = security_scanner.add_notification(
                old_layer_ids,
                new_layer_ids,
                None,
                new_vuln_info,
                max_per_page=2,
                indexed_old_layer_ids=idx_old_layer_ids,
                indexed_new_layer_ids=idx_new_layer_ids,
            )

            # Test with a known notification with pages.
            data = {
                "Name": notification_data["Name"],
            }

            worker = SecurityNotificationWorker(None)
            self.assertTrue(worker.perform_notification_work(data, layer_limit=2))

            # Make sure all pages were processed by ensuring we have only one notification. If the second
            # page was not processed, then the `Old` entry for layer1 will not be found, and we'd get two
            # notifications.
            time.sleep(1)
            self.assertIsNotNone(notification_queue.get())
            self.assertIsNone(notification_queue.get())

    def test_layer_gc(self):
        layer = model.tag.get_tag_image(
            ADMIN_ACCESS_USER, SIMPLE_REPO, "latest", include_storage=True
        )

        # Delete the prod tag so that only the `latest` tag remains.
        model.tag.delete_tag(ADMIN_ACCESS_USER, SIMPLE_REPO, "prod")

        with fake_security_scanner() as security_scanner:
            # Analyze the layer.
            analyzer = LayerAnalyzer(app.config, self.api)
            analyzer.analyze_recursively(layer)

            layer = model.tag.get_tag_image(ADMIN_ACCESS_USER, SIMPLE_REPO, "latest")
            self.assertAnalyzed(layer, security_scanner, True, 1)
            self.assertTrue(security_scanner.has_layer(security_scanner.layer_id(layer)))

            namespace_user = model.user.get_user(ADMIN_ACCESS_USER)
            model.user.change_user_tag_expiration(namespace_user, 0)

            # Delete the tag in the repository and GC.
            model.tag.delete_tag(ADMIN_ACCESS_USER, SIMPLE_REPO, "latest")
            time.sleep(1)

            repo = model.repository.get_repository(ADMIN_ACCESS_USER, SIMPLE_REPO)
            model.gc.garbage_collect_repo(repo)

            # Ensure that the security scanner no longer has the image.
            self.assertFalse(security_scanner.has_layer(security_scanner.layer_id(layer)))


if __name__ == "__main__":
    unittest.main()
