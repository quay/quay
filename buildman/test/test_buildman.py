import asyncio
import unittest
import json
import uuid

from mock import Mock, ANY
from six import iteritems

from buildman.asyncutil import AsyncWrapper
from buildman.component.buildcomponent import BuildComponent
from buildman.manager.ephemeral import EphemeralBuilderManager, REALM_PREFIX, JOB_PREFIX
from buildman.manager.executor import BuilderExecutor, ExecutorException
from buildman.orchestrator import KeyEvent, KeyChange
from buildman.server import BuildJobResult
from util import slash_join


BUILD_UUID = "deadbeef-dead-beef-dead-deadbeefdead"
REALM_ID = "1234-realm"


def async_test(f):
    def wrapper(*args, **kwargs):
        coro = asyncio.coroutine(f)
        future = coro(*args, **kwargs)
        loop = asyncio.get_event_loop()
        loop.run_until_complete(future)

    return wrapper


class TestExecutor(BuilderExecutor):
    job_started = None
    job_stopped = None

    async def start_builder(self, realm, token, build_uuid):
        self.job_started = str(uuid.uuid4())
        return self.job_started

    async def stop_builder(self, execution_id):
        self.job_stopped = execution_id


class BadExecutor(BuilderExecutor):
    async def start_builder(self, realm, token, build_uuid):
        raise ExecutorException("raised on purpose!")


class EphemeralBuilderTestCase(unittest.TestCase):
    def __init__(self, *args, **kwargs):
        self.etcd_client_mock = None
        super(EphemeralBuilderTestCase, self).__init__(*args, **kwargs)

    @staticmethod
    def _create_completed_future(result=None):
        def inner(*args, **kwargs):
            new_future = asyncio.Future()
            new_future.set_result(result)
            return new_future

        return inner

    def setUp(self):
        self._existing_executors = dict(EphemeralBuilderManager.EXECUTORS)

    def tearDown(self):
        EphemeralBuilderManager.EXECUTORS = self._existing_executors

    async def _register_component(self, realm_spec, build_component, token):
        return "hello"

    def _create_build_job(self, namespace="namespace", retries=3):
        mock_job = Mock()
        mock_job.job_details = {"build_uuid": BUILD_UUID}
        mock_job.job_item = {
            "body": json.dumps(mock_job.job_details),
            "id": 1,
        }

        mock_job.namespace = namespace
        mock_job.retries_remaining = retries
        mock_job.build_uuid = BUILD_UUID
        return mock_job


class TestEphemeralLifecycle(EphemeralBuilderTestCase):
    """
    Tests the various lifecycles of the ephemeral builder and its interaction with etcd.
    """

    def __init__(self, *args, **kwargs):
        super(TestEphemeralLifecycle, self).__init__(*args, **kwargs)
        self.etcd_client_mock = None
        self.test_executor = None

    def _create_completed_future(self, result=None):
        def inner(*args, **kwargs):
            new_future = asyncio.Future()
            new_future.set_result(result)
            return new_future

        return inner

    def _create_mock_executor(self, *args, **kwargs):
        self.test_executor = Mock(spec=BuilderExecutor)
        self.test_executor.start_builder = Mock(side_effect=self._create_completed_future("123"))
        self.test_executor.stop_builder = Mock(side_effect=self._create_completed_future())
        self.test_executor.setup_time = 60
        self.test_executor.name = "MockExecutor"
        self.test_executor.minimum_retry_threshold = 0
        return self.test_executor

    def setUp(self):
        super(TestEphemeralLifecycle, self).setUp()

        EphemeralBuilderManager.EXECUTORS["test"] = self._create_mock_executor

        self.register_component_callback = Mock()
        self.unregister_component_callback = Mock()
        self.job_heartbeat_callback = Mock()
        self.job_complete_callback = AsyncWrapper(Mock())

        self.manager = EphemeralBuilderManager(
            self.register_component_callback,
            self.unregister_component_callback,
            self.job_heartbeat_callback,
            self.job_complete_callback,
            "127.0.0.1",
            30,
        )

        self.manager.initialize(
            {
                "EXECUTOR": "test",
                "ORCHESTRATOR": {"MEM_CONFIG": None},
            }
        )

        # Ensure that that the realm and building callbacks have been registered
        callback_keys = [key for key in self.manager._orchestrator.callbacks]
        self.assertIn(REALM_PREFIX, callback_keys)
        self.assertIn(JOB_PREFIX, callback_keys)

        self.mock_job = self._create_build_job()
        self.mock_job_key = slash_join("building", BUILD_UUID)

    def tearDown(self):
        super(TestEphemeralLifecycle, self).tearDown()
        self.manager.shutdown()

    async def _setup_job_for_managers(self):
        test_component = Mock(spec=BuildComponent)
        test_component.builder_realm = REALM_ID
        test_component.start_build = Mock(side_effect=self._create_completed_future())
        self.register_component_callback.return_value = test_component

        is_scheduled = await self.manager.schedule(self.mock_job)
        self.assertTrue(is_scheduled)
        self.assertEqual(self.test_executor.start_builder.call_count, 1)

        # Ensure that that the job, realm, and metric callbacks have been registered
        callback_keys = [key for key in self.manager._orchestrator.callbacks]
        self.assertIn(self.mock_job_key, self.manager._orchestrator.state)
        self.assertIn(REALM_PREFIX, callback_keys)
        # TODO: assert metric key has been set

        realm_for_build = self._find_realm_key(self.manager._orchestrator, BUILD_UUID)

        raw_realm_data = await (
            self.manager._orchestrator.get_key(slash_join("realm", realm_for_build))
        )
        realm_data = json.loads(raw_realm_data)
        realm_data["realm"] = REALM_ID

        # Right now the job is not registered with any managers because etcd has not accepted the job
        self.assertEqual(self.register_component_callback.call_count, 0)

        # Fire off a realm changed with the same data.
        await (
            self.manager._realm_callback(
                KeyChange(
                    KeyEvent.CREATE, slash_join(REALM_PREFIX, REALM_ID), json.dumps(realm_data)
                )
            )
        )

        # Ensure that we have at least one component node.
        self.assertEqual(self.register_component_callback.call_count, 1)
        self.assertEqual(1, self.manager.num_workers())

        # Ensure that the build info exists.
        self.assertIsNotNone(self.manager._build_uuid_to_info.get(BUILD_UUID))

        return test_component

    @staticmethod
    def _find_realm_key(orchestrator, build_uuid):
        for key, value in iteritems(orchestrator.state):
            if key.startswith(REALM_PREFIX):
                parsed_value = json.loads(value)
                body = json.loads(parsed_value["job_queue_item"]["body"])
                if body["build_uuid"] == build_uuid:
                    return parsed_value["realm"]
                continue
        raise KeyError

    @async_test
    def test_schedule_and_complete(self):
        # Test that a job is properly registered with all of the managers
        test_component = await self._setup_job_for_managers()

        # Take the job ourselves
        await self.manager.build_component_ready(test_component)

        self.assertIsNotNone(self.manager._build_uuid_to_info.get(BUILD_UUID))

        # Finish the job
        await (self.manager.job_completed(self.mock_job, BuildJobResult.COMPLETE, test_component))

        # Ensure that the executor kills the job.
        self.assertEqual(self.test_executor.stop_builder.call_count, 1)

        # Ensure the build information is cleaned up.
        self.assertIsNone(self.manager._build_uuid_to_info.get(BUILD_UUID))
        self.assertEqual(0, self.manager.num_workers())

    @async_test
    def test_another_manager_takes_job(self):
        # Prepare a job to be taken by another manager
        test_component = await self._setup_job_for_managers()

        await (
            self.manager._realm_callback(
                KeyChange(
                    KeyEvent.DELETE,
                    slash_join(REALM_PREFIX, REALM_ID),
                    json.dumps(
                        {
                            "realm": REALM_ID,
                            "token": "beef",
                            "execution_id": "123",
                            "job_queue_item": self.mock_job.job_item,
                        }
                    ),
                )
            )
        )

        self.unregister_component_callback.assert_called_once_with(test_component)

        # Ensure that the executor does not kill the job.
        self.assertEqual(self.test_executor.stop_builder.call_count, 0)

        # Ensure that we still have the build info, but not the component.
        self.assertEqual(0, self.manager.num_workers())
        self.assertIsNotNone(self.manager._build_uuid_to_info.get(BUILD_UUID))

        # Delete the job once it has "completed".
        await (
            self.manager._job_callback(
                KeyChange(
                    KeyEvent.DELETE,
                    self.mock_job_key,
                    json.dumps({"had_heartbeat": False, "job_queue_item": self.mock_job.job_item}),
                )
            )
        )

        # Ensure the job was removed from the info, but stop was not called.
        self.assertIsNone(self.manager._build_uuid_to_info.get(BUILD_UUID))
        self.assertEqual(self.test_executor.stop_builder.call_count, 0)

    @async_test
    def test_job_started_by_other_manager(self):
        # Ensure that that the building callbacks have been registered
        callback_keys = [key for key in self.manager._orchestrator.callbacks]
        self.assertIn(JOB_PREFIX, callback_keys)

        # Send a signal to the callback that the job has been created.
        await (
            self.manager._job_callback(
                KeyChange(
                    KeyEvent.CREATE,
                    self.mock_job_key,
                    json.dumps({"had_heartbeat": False, "job_queue_item": self.mock_job.job_item}),
                )
            )
        )

        # Ensure the create does nothing.
        self.assertEqual(self.test_executor.stop_builder.call_count, 0)

    @async_test
    def test_expiring_worker_not_started(self):
        # Ensure that that the building callbacks have been registered
        callback_keys = [key for key in self.manager._orchestrator.callbacks]
        self.assertIn(JOB_PREFIX, callback_keys)

        # Send a signal to the callback that a worker has expired
        await (
            self.manager._job_callback(
                KeyChange(
                    KeyEvent.EXPIRE,
                    self.mock_job_key,
                    json.dumps({"had_heartbeat": True, "job_queue_item": self.mock_job.job_item}),
                )
            )
        )

        # Since the realm was never registered, expiration should do nothing.
        self.assertEqual(self.test_executor.stop_builder.call_count, 0)

    @async_test
    def test_expiring_worker_started(self):
        test_component = await self._setup_job_for_managers()

        # Ensure that that the building callbacks have been registered
        callback_keys = [key for key in self.manager._orchestrator.callbacks]
        self.assertIn(JOB_PREFIX, callback_keys)

        await (
            self.manager._job_callback(
                KeyChange(
                    KeyEvent.EXPIRE,
                    self.mock_job_key,
                    json.dumps({"had_heartbeat": True, "job_queue_item": self.mock_job.job_item}),
                )
            )
        )

        self.test_executor.stop_builder.assert_called_once_with("123")
        self.assertEqual(self.test_executor.stop_builder.call_count, 1)

    @async_test
    def test_buildjob_deleted(self):
        test_component = await self._setup_job_for_managers()

        # Ensure that that the building callbacks have been registered
        callback_keys = [key for key in self.manager._orchestrator.callbacks]
        self.assertIn(JOB_PREFIX, callback_keys)

        # Send a signal to the callback that a worker has expired
        await (
            self.manager._job_callback(
                KeyChange(
                    KeyEvent.DELETE,
                    self.mock_job_key,
                    json.dumps({"had_heartbeat": False, "job_queue_item": self.mock_job.job_item}),
                )
            )
        )

        self.assertEqual(self.test_executor.stop_builder.call_count, 0)
        self.assertEqual(self.job_complete_callback.call_count, 0)
        self.assertIsNone(self.manager._build_uuid_to_info.get(BUILD_UUID))

    @async_test
    def test_builder_never_starts(self):
        test_component = await self._setup_job_for_managers()

        # Ensure that that the building callbacks have been registered
        callback_keys = [key for key in self.manager._orchestrator.callbacks]
        self.assertIn(JOB_PREFIX, callback_keys)

        # Send a signal to the callback that a worker has expired
        await (
            self.manager._job_callback(
                KeyChange(
                    KeyEvent.EXPIRE,
                    self.mock_job_key,
                    json.dumps({"had_heartbeat": False, "job_queue_item": self.mock_job.job_item}),
                )
            )
        )

        self.test_executor.stop_builder.assert_called_once_with("123")
        self.assertEqual(self.test_executor.stop_builder.call_count, 1)

        # Ensure the job was marked as incomplete, with an update_phase to True (so the DB record and
        # logs are updated as well)
        await (
            self.job_complete_callback.assert_called_once_with(
                ANY, BuildJobResult.INCOMPLETE, "MockExecutor", update_phase=True
            )
        )

    @async_test
    def test_change_worker(self):
        # Send a signal to the callback that a worker key has been changed
        self.manager._job_callback(KeyChange(KeyEvent.SET, self.mock_job_key, "value"))
        self.assertEqual(self.test_executor.stop_builder.call_count, 0)

    @async_test
    def test_realm_expired(self):
        test_component = await self._setup_job_for_managers()

        # Send a signal to the callback that a realm has expired
        await (
            self.manager._realm_callback(
                KeyChange(
                    KeyEvent.EXPIRE,
                    self.mock_job_key,
                    json.dumps(
                        {
                            "realm": REALM_ID,
                            "execution_id": "foobar",
                            "executor_name": "MockExecutor",
                            "job_queue_item": {"body": '{"build_uuid": "fakeid"}'},
                        }
                    ),
                )
            )
        )

        # Ensure that the cleanup code for the executor was called.
        self.test_executor.stop_builder.assert_called_once_with("foobar")
        self.assertEqual(self.test_executor.stop_builder.call_count, 1)


class TestEphemeral(EphemeralBuilderTestCase):
    """
    Simple unit tests for the ephemeral builder around config management, starting and stopping
    jobs.
    """

    def setUp(self):
        super(TestEphemeral, self).setUp()

        unregister_component_callback = Mock()
        job_heartbeat_callback = Mock()

        async def job_complete_callback(*args, **kwargs):
            return

        self.manager = EphemeralBuilderManager(
            self._register_component,
            unregister_component_callback,
            job_heartbeat_callback,
            job_complete_callback,
            "127.0.0.1",
            30,
        )

    def tearDown(self):
        super(TestEphemeral, self).tearDown()
        self.manager.shutdown()

    def test_verify_executor_oldconfig(self):
        EphemeralBuilderManager.EXECUTORS["test"] = TestExecutor
        self.manager.initialize(
            {
                "EXECUTOR": "test",
                "EXECUTOR_CONFIG": dict(MINIMUM_RETRY_THRESHOLD=42),
                "ORCHESTRATOR": {"MEM_CONFIG": None},
            }
        )

        # Ensure that we have a single test executor.
        self.assertEqual(1, len(self.manager.registered_executors))
        self.assertEqual(42, self.manager.registered_executors[0].minimum_retry_threshold)
        self.assertEqual("TestExecutor", self.manager.registered_executors[0].name)

    def test_verify_executor_newconfig(self):
        EphemeralBuilderManager.EXECUTORS["test"] = TestExecutor
        self.manager.initialize(
            {
                "EXECUTORS": [{"EXECUTOR": "test", "MINIMUM_RETRY_THRESHOLD": 42}],
                "ORCHESTRATOR": {"MEM_CONFIG": None},
            }
        )

        # Ensure that we have a single test executor.
        self.assertEqual(1, len(self.manager.registered_executors))
        self.assertEqual(42, self.manager.registered_executors[0].minimum_retry_threshold)

    def test_multiple_executors_samename(self):
        EphemeralBuilderManager.EXECUTORS["test"] = TestExecutor
        EphemeralBuilderManager.EXECUTORS["anotherexecutor"] = TestExecutor

        with self.assertRaises(Exception):
            self.manager.initialize(
                {
                    "EXECUTORS": [
                        {"NAME": "primary", "EXECUTOR": "test", "MINIMUM_RETRY_THRESHOLD": 42},
                        {
                            "NAME": "primary",
                            "EXECUTOR": "anotherexecutor",
                            "MINIMUM_RETRY_THRESHOLD": 24,
                        },
                    ],
                    "ORCHESTRATOR": {"MEM_CONFIG": None},
                }
            )

    def test_verify_multiple_executors(self):
        EphemeralBuilderManager.EXECUTORS["test"] = TestExecutor
        EphemeralBuilderManager.EXECUTORS["anotherexecutor"] = TestExecutor

        self.manager.initialize(
            {
                "EXECUTORS": [
                    {"NAME": "primary", "EXECUTOR": "test", "MINIMUM_RETRY_THRESHOLD": 42},
                    {
                        "NAME": "secondary",
                        "EXECUTOR": "anotherexecutor",
                        "MINIMUM_RETRY_THRESHOLD": 24,
                    },
                ],
                "ORCHESTRATOR": {"MEM_CONFIG": None},
            }
        )

        # Ensure that we have a two test executors.
        self.assertEqual(2, len(self.manager.registered_executors))
        self.assertEqual(42, self.manager.registered_executors[0].minimum_retry_threshold)
        self.assertEqual(24, self.manager.registered_executors[1].minimum_retry_threshold)

    def test_skip_invalid_executor(self):
        self.manager.initialize(
            {
                "EXECUTORS": [
                    {"EXECUTOR": "unknown", "MINIMUM_RETRY_THRESHOLD": 42},
                ],
                "ORCHESTRATOR": {"MEM_CONFIG": None},
            }
        )

        self.assertEqual(0, len(self.manager.registered_executors))

    @async_test
    def test_schedule_job_namespace_filter(self):
        EphemeralBuilderManager.EXECUTORS["test"] = TestExecutor
        self.manager.initialize(
            {
                "EXECUTORS": [
                    {
                        "EXECUTOR": "test",
                        "NAMESPACE_WHITELIST": ["something"],
                    }
                ],
                "ORCHESTRATOR": {"MEM_CONFIG": None},
            }
        )

        # Try with a build job in an invalid namespace.
        build_job = self._create_build_job(namespace="somethingelse")
        result = await self.manager.schedule(build_job)
        self.assertFalse(result[0])

        # Try with a valid namespace.
        build_job = self._create_build_job(namespace="something")
        result = await self.manager.schedule(build_job)
        self.assertTrue(result[0])

    @async_test
    def test_schedule_job_retries_filter(self):
        EphemeralBuilderManager.EXECUTORS["test"] = TestExecutor
        self.manager.initialize(
            {
                "EXECUTORS": [
                    {
                        "EXECUTOR": "test",
                        "MINIMUM_RETRY_THRESHOLD": 2,
                    }
                ],
                "ORCHESTRATOR": {"MEM_CONFIG": None},
            }
        )

        # Try with a build job that has too few retries.
        build_job = self._create_build_job(retries=1)
        result = await self.manager.schedule(build_job)
        self.assertFalse(result[0])

        # Try with a valid job.
        build_job = self._create_build_job(retries=2)
        result = await self.manager.schedule(build_job)
        self.assertTrue(result[0])

    @async_test
    def test_schedule_job_executor_fallback(self):
        EphemeralBuilderManager.EXECUTORS["primary"] = TestExecutor
        EphemeralBuilderManager.EXECUTORS["secondary"] = TestExecutor

        self.manager.initialize(
            {
                "EXECUTORS": [
                    {
                        "NAME": "primary",
                        "EXECUTOR": "primary",
                        "NAMESPACE_WHITELIST": ["something"],
                        "MINIMUM_RETRY_THRESHOLD": 3,
                    },
                    {
                        "NAME": "secondary",
                        "EXECUTOR": "secondary",
                        "MINIMUM_RETRY_THRESHOLD": 2,
                    },
                ],
                "ALLOWED_WORKER_COUNT": 5,
                "ORCHESTRATOR": {"MEM_CONFIG": None},
            }
        )

        # Try a job not matching the primary's namespace filter. Should schedule on secondary.
        build_job = self._create_build_job(namespace="somethingelse")
        result = await self.manager.schedule(build_job)
        self.assertTrue(result[0])

        self.assertIsNone(self.manager.registered_executors[0].job_started)
        self.assertIsNotNone(self.manager.registered_executors[1].job_started)

        self.manager.registered_executors[0].job_started = None
        self.manager.registered_executors[1].job_started = None

        # Try a job not matching the primary's retry minimum. Should schedule on secondary.
        build_job = self._create_build_job(namespace="something", retries=2)
        result = await self.manager.schedule(build_job)
        self.assertTrue(result[0])

        self.assertIsNone(self.manager.registered_executors[0].job_started)
        self.assertIsNotNone(self.manager.registered_executors[1].job_started)

        self.manager.registered_executors[0].job_started = None
        self.manager.registered_executors[1].job_started = None

        # Try a job matching the primary. Should schedule on the primary.
        build_job = self._create_build_job(namespace="something", retries=3)
        result = await self.manager.schedule(build_job)
        self.assertTrue(result[0])

        self.assertIsNotNone(self.manager.registered_executors[0].job_started)
        self.assertIsNone(self.manager.registered_executors[1].job_started)

        self.manager.registered_executors[0].job_started = None
        self.manager.registered_executors[1].job_started = None

        # Try a job not matching either's restrictions.
        build_job = self._create_build_job(namespace="somethingelse", retries=1)
        result = await self.manager.schedule(build_job)
        self.assertFalse(result[0])

        self.assertIsNone(self.manager.registered_executors[0].job_started)
        self.assertIsNone(self.manager.registered_executors[1].job_started)

        self.manager.registered_executors[0].job_started = None
        self.manager.registered_executors[1].job_started = None

    @async_test
    def test_schedule_job_single_executor(self):
        EphemeralBuilderManager.EXECUTORS["test"] = TestExecutor

        self.manager.initialize(
            {
                "EXECUTOR": "test",
                "EXECUTOR_CONFIG": {},
                "ALLOWED_WORKER_COUNT": 5,
                "ORCHESTRATOR": {"MEM_CONFIG": None},
            }
        )

        build_job = self._create_build_job(namespace="something", retries=3)
        result = await self.manager.schedule(build_job)
        self.assertTrue(result[0])

        self.assertIsNotNone(self.manager.registered_executors[0].job_started)
        self.manager.registered_executors[0].job_started = None

        build_job = self._create_build_job(namespace="something", retries=0)
        result = await self.manager.schedule(build_job)
        self.assertTrue(result[0])

        self.assertIsNotNone(self.manager.registered_executors[0].job_started)
        self.manager.registered_executors[0].job_started = None

    @async_test
    def test_executor_exception(self):
        EphemeralBuilderManager.EXECUTORS["bad"] = BadExecutor

        self.manager.initialize(
            {
                "EXECUTOR": "bad",
                "EXECUTOR_CONFIG": {},
                "ORCHESTRATOR": {"MEM_CONFIG": None},
            }
        )

        build_job = self._create_build_job(namespace="something", retries=3)
        result = await self.manager.schedule(build_job)
        self.assertFalse(result[0])

    @async_test
    def test_schedule_and_stop(self):
        EphemeralBuilderManager.EXECUTORS["test"] = TestExecutor

        self.manager.initialize(
            {
                "EXECUTOR": "test",
                "EXECUTOR_CONFIG": {},
                "ORCHESTRATOR": {"MEM_CONFIG": None},
            }
        )

        # Start the build job.
        build_job = self._create_build_job(namespace="something", retries=3)
        result = await self.manager.schedule(build_job)
        self.assertTrue(result[0])

        executor = self.manager.registered_executors[0]
        self.assertIsNotNone(executor.job_started)

        # Register the realm so the build information is added.
        await (
            self.manager._register_realm(
                {
                    "realm": str(uuid.uuid4()),
                    "token": str(uuid.uuid4()),
                    "execution_id": executor.job_started,
                    "executor_name": "TestExecutor",
                    "build_uuid": build_job.build_uuid,
                    "job_queue_item": build_job.job_item,
                }
            )
        )

        # Stop the build job.
        await self.manager.kill_builder_executor(build_job.build_uuid)
        self.assertEqual(executor.job_stopped, executor.job_started)


if __name__ == "__main__":
    unittest.main()
