import asyncio
import datetime
import hashlib
import io
import json
import logging
import os
import socket
import subprocess
import threading
import time
import uuid

from functools import partial, wraps

import boto3
import botocore
import cachetools.func
import requests

from jinja2 import FileSystemLoader, Environment
from prometheus_client import Histogram

import release

from _init import ROOT_DIR
from app import app
from buildman.asyncutil import AsyncWrapper
from buildman.container_cloud_config import CloudConfigContext


logger = logging.getLogger(__name__)


ONE_HOUR = 60 * 60

_TAG_RETRY_COUNT = 3  # Number of times to retry adding tags.
_TAG_RETRY_SLEEP = 2  # Number of seconds to wait between tag retries.

ENV = Environment(loader=FileSystemLoader(os.path.join(ROOT_DIR, "buildman/templates")))
CloudConfigContext().populate_jinja_environment(ENV)
TEMPLATE = ENV.get_template("cloudconfig.json")


build_start_duration = Histogram(
    "quay_build_start_duration_seconds",
    "seconds taken for a executor to start executing a queued build",
    labelnames=["executor"],
)


def async_observe(metric, *labels):
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            trigger_time = time.time()
            try:
                rv = func(*args, **kwargs)
            except Return as e:
                metric.labels(*labels).observe(time.time() - trigger_time)
                raise e
            return rv

        return wrapper

    return decorator


class ExecutorException(Exception):
    """
    Exception raised when there is a problem starting or stopping a builder.
    """

    pass


class BuilderExecutor(object):
    def __init__(self, executor_config, manager_hostname):
        """
        Interface which can be plugged into the EphemeralNodeManager to provide a strategy for
        starting and stopping builders.
        """
        self.executor_config = executor_config
        self.manager_hostname = manager_hostname

        default_websocket_scheme = "wss" if app.config["PREFERRED_URL_SCHEME"] == "https" else "ws"
        self.websocket_scheme = executor_config.get("WEBSOCKET_SCHEME", default_websocket_scheme)

    @property
    def name(self):
        """
        Name returns the unique name for this executor.
        """
        return self.executor_config.get("NAME") or self.__class__.__name__

    @property
    def setup_time(self):
        """
        Returns the amount of time (in seconds) to wait for the execution to start for the build.

        If None, the manager's default will be used.
        """
        return self.executor_config.get("SETUP_TIME")

    async def start_builder(self, realm, token, build_uuid):
        """
        Create a builder with the specified config.

        Returns a unique id which can be used to manage the builder.
        """
        raise NotImplementedError

    async def stop_builder(self, builder_id):
        """
        Stop a builder which is currently running.
        """
        raise NotImplementedError

    def allowed_for_namespace(self, namespace):
        """
        Returns true if this executor can be used for builds in the given namespace.
        """

        # Check for an explicit namespace whitelist.
        namespace_whitelist = self.executor_config.get("NAMESPACE_WHITELIST")
        if namespace_whitelist is not None and namespace in namespace_whitelist:
            return True

        # Check for a staged rollout percentage. If found, we hash the namespace and, if it is found
        # in the first X% of the character space, we allow this executor to be used.
        staged_rollout = self.executor_config.get("STAGED_ROLLOUT")
        if staged_rollout is not None:
            bucket = int(hashlib.sha256(namespace.encode("utf-8")).hexdigest()[-2:], 16)
            return bucket < (256 * staged_rollout)

        # If there are no restrictions in place, we are free to use this executor.
        return staged_rollout is None and namespace_whitelist is None

    @property
    def minimum_retry_threshold(self):
        """
        Returns the minimum number of retries required for this executor to be used or 0 if none.
        """
        return self.executor_config.get("MINIMUM_RETRY_THRESHOLD", 0)

    def generate_cloud_config(
        self,
        realm,
        token,
        build_uuid,
        coreos_channel,
        manager_hostname,
        quay_username=None,
        quay_password=None,
    ):
        if quay_username is None:
            quay_username = self.executor_config["QUAY_USERNAME"]

        if quay_password is None:
            quay_password = self.executor_config["QUAY_PASSWORD"]

        rendered_json = json.load(
            io.StringIO(TEMPLATE.render(
                realm=realm,
                token=token,
                build_uuid=build_uuid,
                quay_username=quay_username,
                quay_password=quay_password,
                manager_hostname=manager_hostname,
                websocket_scheme=self.websocket_scheme,
                coreos_channel=coreos_channel,
                worker_image=self.executor_config.get(
                    "WORKER_IMAGE", "quay.io/coreos/registry-build-worker"
                ),
                worker_tag=self.executor_config["WORKER_TAG"],
                volume_size=self.executor_config.get("VOLUME_SIZE", "42G"),
                max_lifetime_s=self.executor_config.get("MAX_LIFETIME_S", 10800),
                ssh_authorized_keys=self.executor_config.get("SSH_AUTHORIZED_KEYS", []),
            ))
        )

        return json.dumps(rendered_json)


class EC2Executor(BuilderExecutor):
    """
    Implementation of BuilderExecutor which uses libcloud to start machines on a variety of cloud
    providers.
    """
    COREOS_STACK_ARCHITECTURE = "x86_64"
    COREOS_STACK_URL = (
        "https://builds.coreos.fedoraproject.org/streams/%s.json"
    )

    def __init__(self, *args, **kwargs):
        self._loop = asyncio.get_event_loop()
        super(EC2Executor, self).__init__(*args, **kwargs)

    def _get_conn(self):
        """
        Creates an ec2 connection which can be used to manage instances.
        """
        return AsyncWrapper(
            boto3.client(
                "ec2",
                region_name=self.executor_config["EC2_REGION"],
                aws_access_key_id=self.executor_config["AWS_ACCESS_KEY"],
                aws_secret_access_key=self.executor_config["AWS_SECRET_KEY"],
            )
        )

    @classmethod
    @cachetools.func.ttl_cache(ttl=ONE_HOUR)
    def _get_coreos_ami(cls, ec2_region, coreos_channel):
        """
        Retrieve the CoreOS AMI id from the canonical listing.
        """
        stack_list_json = requests.get(EC2Executor.COREOS_STACK_URL % coreos_channel).json()
        stack_amis = stack_list_json['architectures'][EC2Executor.COREOS_STACK_ARCHITECTURE]['images']['aws']['regions']
        return stack_amis[ec2_region]['image']

    @async_observe(build_start_duration, "ec2")
    async def start_builder(self, realm, token, build_uuid):
        region = self.executor_config["EC2_REGION"]
        channel = self.executor_config.get("COREOS_CHANNEL", "stable")

        coreos_ami = self.executor_config.get("COREOS_AMI", None)
        if coreos_ami is None:
            get_ami_callable = partial(self._get_coreos_ami, region, channel)
            coreos_ami = await self._loop.run_in_executor(None, get_ami_callable)

        user_data = self.generate_cloud_config(
            realm, token, build_uuid, channel, self.manager_hostname
        )
        logger.debug("Generated cloud config for build %s: %s", build_uuid, user_data)

        ec2_conn = self._get_conn()

        block_device_mappings = [
            {
                "DeviceName": "/dev/xvda",
                "Ebs": {
                    "VolumeSize": int(self.executor_config.get("BLOCK_DEVICE_SIZE", 48)),
                    "VolumeType": "gp2",
                    "DeleteOnTermination":True,
                }
            }
        ]

        interfaces = None
        if self.executor_config.get("EC2_VPC_SUBNET_ID", None) is not None:
            interfaces = [
                {
                    "DeviceIndex": 0,
                    "SubnetId": self.executor_config["EC2_VPC_SUBNET_ID"],
                    "Groups": self.executor_config["EC2_SECURITY_GROUP_IDS"],
                    "AssociatePublicIpAddress": True,
                }
            ]

        try:
            reservation = await (
                ec2_conn.run_instances(
                    ImageId=coreos_ami,
                    InstanceType=self.executor_config["EC2_INSTANCE_TYPE"],
                    KeyName=self.executor_config.get("EC2_KEY_NAME", None),
                    UserData=user_data,
                    InstanceInitiatedShutdownBehavior="terminate",
                    BlockDeviceMappings=block_device_mappings,
                    NetworkInterfaces=interfaces,
                    MinCount=1,
                    MaxCount=1,
                )
            )
        except (ec2_conn.exceptions.ClientError, botocore.exceptions.ClientError) as ec2e:
            logger.exception("Unable to spawn builder instance")
            raise ec2e

        instances = reservation.get("Instances", [])
        if not instances:
            raise ExecutorException("Unable to spawn builder instance.")
        elif len(instances) != 1:
            raise ExecutorException("EC2 started wrong number of instances!")

        launched = instances[0]

        # Sleep a few seconds to wait for AWS to spawn the instance.
        await asyncio.sleep(_TAG_RETRY_SLEEP)

        # Tag the instance with its metadata.
        for i in range(0, _TAG_RETRY_COUNT):
            try:
                await (
                    ec2_conn.create_tags(
                        Resources=[
                            launched["InstanceId"]
                        ],
                        Tags=[
                            {"Key": "Name", "Value": "Quay Ephemeral Builder"},
                            {"Key": "Realm", "Value": realm},
                            {"Key": "Token", "Value": token},
                            {"Key": "BuildUUID", "Value": build_uuid},
                        ]
                    )
                )
            except (ec2_conn.exceptions.ClientError, botocore.exceptions.ClientError) as ec2e:
                if ec2e.response["Error"]["Code"] == "InvalidInstanceID.NotFound":
                    if i < _TAG_RETRY_COUNT - 1:
                        logger.warning(
                            "Failed to write EC2 tags for instance %s for build %s (attempt #%s)",
                            launched["InstanceId"],
                            build_uuid,
                            i,
                        )
                        await asyncio.sleep(_TAG_RETRY_SLEEP)
                        continue

                    raise ExecutorException("Unable to find builder instance.")

                logger.exception("Failed to write EC2 tags (attempt #%s)", i)

        logger.debug("Machine with ID %s started for build %s", launched["InstanceId"], build_uuid)
        return launched["InstanceId"]

    async def stop_builder(self, builder_id):
        try:
            ec2_conn = self._get_conn()
            terminated_instances = await ec2_conn.terminate_instances(InstanceIds=[builder_id])
        except (ec2_conn.exceptions.ClientError, botocore.exceptions.ClientError) as ec2e:
            if ec2e.response["Error"]["Code"] == "InvalidInstanceID.NotFound":
                logger.debug("Instance %s already terminated", builder_id)
                return

            logger.exception("Exception when trying to terminate instance %s", builder_id)
            raise

        if builder_id not in [si["InstanceId"] for si in terminated_instances["TerminatingInstances"]]:
            raise ExecutorException("Unable to terminate instance: %s" % builder_id)


class PopenExecutor(BuilderExecutor):
    """
    Implementation of BuilderExecutor which uses Popen to fork a quay-builder process.
    """

    def __init__(self, executor_config, manager_hostname):
        self._jobs = {}
        super(PopenExecutor, self).__init__(executor_config, manager_hostname)

    @async_observe(build_start_duration, "fork")
    async def start_builder(self, realm, token, build_uuid):
        # Now start a machine for this job, adding the machine id to the etcd information
        logger.debug("Forking process for build")

        ws_host = os.environ.get("BUILDMAN_WS_HOST", "localhost")
        ws_port = os.environ.get("BUILDMAN_WS_PORT", "8787")
        builder_env = {
            "TOKEN": token,
            "REALM": realm,
            "ENDPOINT": "ws://%s:%s" % (ws_host, ws_port),
            "DOCKER_TLS_VERIFY": os.environ.get("DOCKER_TLS_VERIFY", ""),
            "DOCKER_CERT_PATH": os.environ.get("DOCKER_CERT_PATH", ""),
            "DOCKER_HOST": os.environ.get("DOCKER_HOST", ""),
            "PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
        }

        logpipe = LogPipe(logging.INFO)
        spawned = subprocess.Popen(
            os.environ.get("BUILDER_BINARY_LOCATION", "/usr/local/bin/quay-builder"),
            stdout=logpipe,
            stderr=logpipe,
            env=builder_env,
        )

        builder_id = str(uuid.uuid4())
        self._jobs[builder_id] = (spawned, logpipe)
        logger.debug("Builder spawned with id: %s", builder_id)
        return builder_id

    async def stop_builder(self, builder_id):
        if builder_id not in self._jobs:
            raise ExecutorException("Builder id not being tracked by executor.")

        logger.debug("Killing builder with id: %s", builder_id)
        spawned, logpipe = self._jobs[builder_id]

        if spawned.poll() is None:
            spawned.kill()
        logpipe.close()


class KubernetesExecutor(BuilderExecutor):
    """
    Executes build jobs by creating Kubernetes jobs which run a qemu-kvm virtual machine in a pod.
    """

    def __init__(self, *args, **kwargs):
        super(KubernetesExecutor, self).__init__(*args, **kwargs)
        self._loop = asyncio.get_event_loop()
        self.namespace = self.executor_config.get("BUILDER_NAMESPACE", "builder")
        self.image = self.executor_config.get(
            "BUILDER_VM_CONTAINER_IMAGE", "quay.io/quay/quay-builder-qemu-fedoracoreos:stable"
        )

    async def _request(self, method, path, **kwargs):
        request_options = dict(kwargs)

        tls_cert = self.executor_config.get("K8S_API_TLS_CERT")
        tls_key = self.executor_config.get("K8S_API_TLS_KEY")
        tls_ca = self.executor_config.get("K8S_API_TLS_CA")
        service_account_token = self.executor_config.get("SERVICE_ACCOUNT_TOKEN")

        if "timeout" not in request_options:
            request_options["timeout"] = self.executor_config.get("K8S_API_TIMEOUT", 20)

        if service_account_token:
            scheme = "https"
            request_options["headers"] = {"Authorization": "Bearer " + service_account_token}
            logger.debug("Using service account token for Kubernetes authentication")
        elif tls_cert and tls_key:
            scheme = "https"
            request_options["cert"] = (tls_cert, tls_key)
            logger.debug("Using tls certificate and key for Kubernetes authentication")
            if tls_ca:
                request_options["verify"] = tls_ca
        else:
            scheme = "http"

        server = self.executor_config.get("K8S_API_SERVER", "localhost:8080")
        url = "%s://%s%s" % (scheme, server, path)

        logger.debug("Executor config: %s", self.executor_config)
        logger.debug("Kubernetes request: %s %s: %s", method, url, request_options)
        res = requests.request(method, url, **request_options)
        logger.debug("Kubernetes response: %s: %s", res.status_code, res.text)
        return res

    def _jobs_path(self):
        return "/apis/batch/v1/namespaces/%s/jobs" % self.namespace

    def _job_path(self, build_uuid):
        return "%s/%s" % (self._jobs_path(), build_uuid)

    def _kubernetes_distribution(self):
        return self.executor_config.get("KUBERNETES_DISTRIBUTION", "basic").lower()

    def _is_basic_kubernetes_distribution(self):
        return self._kubernetes_distribution() == "basic"

    def _is_openshift_kubernetes_distribution(self):
        return self._kubernetes_distribution() == "openshift"

    def _build_job_container_resources(self):
        # Minimum acceptable free resources for this container to "fit" in a quota
        # These may be lower than the absolute limits if the cluster is knowingly
        # oversubscribed by some amount.
        container_requests = {
            "memory": self.executor_config.get("CONTAINER_MEMORY_REQUEST", "3968Mi"),
        }

        container_limits = {
            "memory": self.executor_config.get("CONTAINER_MEMORY_LIMITS", "5120Mi"),
            "cpu": self.executor_config.get("CONTAINER_CPU_LIMITS", "1000m"),
        }

        resources = {
            "requests": container_requests,
        }

        if self._is_openshift_kubernetes_distribution():
            resources["requests"]["cpu"] = self.executor_config.get("CONTAINER_CPU_REQUEST", "500m")
            resources["limits"] = container_limits

        return resources

    def _build_job_containers(self, user_data):
        vm_memory_limit = self.executor_config.get("VM_MEMORY_LIMIT", "4G")
        vm_volume_size = self.executor_config.get("VOLUME_SIZE", "32G")

        container = {
            "name": "builder",
            "imagePullPolicy": "IfNotPresent",
            "image": self.image,
            "securityContext": {"privileged": True},
            "env": [
                {"name": "USERDATA", "value": user_data},
                {"name": "VM_MEMORY", "value": vm_memory_limit},
                {"name": "VM_VOLUME_SIZE", "value": vm_volume_size},
            ],
            "resources": self._build_job_container_resources(),
        }

        if self._is_basic_kubernetes_distribution():
            container["volumeMounts"] = [
                {
                    "name": "secrets-mask",
                    "mountPath": "/var/run/secrets/kubernetes.io/serviceaccount",
                }
            ]

        return container

    def _job_resource(self, build_uuid, user_data, coreos_channel="stable"):
        image_pull_secret_name = self.executor_config.get("IMAGE_PULL_SECRET_NAME", "builder")
        service_account = self.executor_config.get("SERVICE_ACCOUNT_NAME", "quay-builder-sa")
        node_selector_label_key = self.executor_config.get(
            "NODE_SELECTOR_LABEL_KEY", "beta.kubernetes.io/instance-type"
        )
        node_selector_label_value = self.executor_config.get("NODE_SELECTOR_LABEL_VALUE", "")

        node_selector = {node_selector_label_key: node_selector_label_value}

        release_sha = release.GIT_HEAD or "none"
        if " " in release_sha:
            release_sha = "HEAD"

        job_resource = {
            "apiVersion": "batch/v1",
            "kind": "Job",
            "metadata": {
                "namespace": self.namespace,
                "generateName": build_uuid + "-",
                "labels": {
                    "build": build_uuid,
                    "time": datetime.datetime.now().strftime("%Y-%m-%d-%H"),
                    "manager": socket.gethostname(),
                    "quay-sha": release_sha,
                },
            },
            "spec": {
                "activeDeadlineSeconds": self.executor_config.get("MAXIMUM_JOB_TIME", 7200),
                "template": {
                    "metadata": {
                        "labels": {
                            "build": build_uuid,
                            "time": datetime.datetime.now().strftime("%Y-%m-%d-%H"),
                            "manager": socket.gethostname(),
                            "quay-sha": release_sha,
                        },
                    },
                    "spec": {
                        "imagePullSecrets": [{"name": image_pull_secret_name}],
                        "restartPolicy": "Never",
                        "dnsPolicy": "Default",
                        "containers": [self._build_job_containers(user_data)],
                    },
                },
            },
        }

        if self._is_openshift_kubernetes_distribution():
            # Setting `automountServiceAccountToken` to false will prevent automounting API credentials for a service account.
            job_resource["spec"]["template"]["spec"]["automountServiceAccountToken"] = False

            # Use dedicated service account that has no authorization to any resources.
            job_resource["spec"]["template"]["spec"]["serviceAccount"] = service_account

            # Setting `enableServiceLinks` to false prevents information about other services from being injected into pod's
            # environment variables. Pod has no visibility into other services on the cluster.
            job_resource["spec"]["template"]["spec"]["enableServiceLinks"] = False

            if node_selector_label_value.strip() != "":
                job_resource["spec"]["template"]["spec"]["nodeSelector"] = node_selector

        if self._is_basic_kubernetes_distribution():
            # This volume is a hack to mask the token for the namespace's
            # default service account, which is placed in a file mounted under
            # `/var/run/secrets/kubernetes.io/serviceaccount` in all pods.
            # There's currently no other way to just disable the service
            # account at either the pod or namespace level.
            #
            #   https://github.com/kubernetes/kubernetes/issues/16779
            #
            job_resource["spec"]["template"]["spec"]["volumes"] = [
                {"name": "secrets-mask", "emptyDir": {"medium": "Memory"}}
            ]

        return job_resource

    @async_observe(build_start_duration, "k8s")
    async def start_builder(self, realm, token, build_uuid):
        # generate resource
        channel = self.executor_config.get("COREOS_CHANNEL", "stable")
        user_data = self.generate_cloud_config(
            realm, token, build_uuid, channel, self.manager_hostname
        )
        resource = self._job_resource(build_uuid, user_data, channel)
        logger.debug("Using Kubernetes Distribution: %s", self._kubernetes_distribution())
        logger.debug("Generated kubernetes resource:\n%s", resource)

        # schedule
        create_job = await self._request("POST", self._jobs_path(), json=resource)
        if int(create_job.status_code / 100) != 2:
            raise ExecutorException(
                "Failed to create job: %s: %s: %s"
                % (build_uuid, create_job.status_code, create_job.text)
            )

        job = create_job.json()
        return job["metadata"]["name"]

    async def stop_builder(self, builder_id):
        pods_path = "/api/v1/namespaces/%s/pods" % self.namespace

        # Delete the job itself.
        try:
            await self._request("DELETE", self._job_path(builder_id))
        except:
            logger.exception("Failed to send delete job call for job %s", builder_id)

        # Delete the pod(s) for the job.
        selectorString = "job-name=%s" % builder_id
        try:
            await (self._request("DELETE", pods_path, params=dict(labelSelector=selectorString)))
        except:
            logger.exception("Failed to send delete pod call for job %s", builder_id)


class LogPipe(threading.Thread):
    """
    Adapted from http://codereview.stackexchange.com/a/17959.
    """

    def __init__(self, level):
        """
        Setup the object with a logger and a loglevel and start the thread.
        """
        threading.Thread.__init__(self)
        self.daemon = False
        self.level = level
        self.fd_read, self.fd_write = os.pipe()
        self.pipe_reader = os.fdopen(self.fd_read)
        self.start()

    def fileno(self):
        """
        Return the write file descriptor of the pipe.
        """
        return self.fd_write

    def run(self):
        """
        Run the thread, logging everything.
        """
        for line in iter(self.pipe_reader.readline, ""):
            logging.log(self.level, line.strip("\n"))

        self.pipe_reader.close()

    def close(self):
        """
        Close the write end of the pipe.
        """
        os.close(self.fd_write)
