from abc import ABCMeta, abstractmethod
from collections import namedtuple
from six import add_metaclass

Command = namedtuple("Command", ["command"])

# NOTE: FileCopy is done via `scp`, instead of `ssh` which is how Command is run.
FileCopy = namedtuple("FileCopy", ["source", "destination"])


@add_metaclass(ABCMeta)
class Client(object):
    """
    Client defines the interface for all clients being tested.
    """

    @abstractmethod
    def setup_client(self, registry_host, verify_tls):
        """
        Returns the commands necessary to setup the client inside the VM.
        """

    @abstractmethod
    def populate_test_image(self, registry_host, namespace, name):
        """
        Returns the commands necessary to populate the test image.
        """

    @abstractmethod
    def print_version(self):
        """
        Returns the commands necessary to print the version of the client.
        """

    @abstractmethod
    def login(self, registry_host, username, password):
        """
        Returns the commands necessary to login.
        """

    @abstractmethod
    def push(self, registry_host, namespace, name):
        """
        Returns the commands necessary to test pushing.
        """

    @abstractmethod
    def pre_pull_cleanup(self, registry_host, namespace, name):
        """
        Returns the commands necessary to cleanup before pulling.
        """

    @abstractmethod
    def pull(self, registry_host, namespace, name):
        """
        Returns the commands necessary to test pulling.
        """

    @abstractmethod
    def verify(self, registry_host, namespace, name):
        """
        Returns the commands necessary to verify the pulled image.
        """


class DockerClient(Client):
    def __init__(self, requires_v1=False, requires_email=False):
        self.requires_v1 = requires_v1
        self.requires_email = requires_email

    def setup_client(self, registry_host, verify_tls):
        if not verify_tls:
            cp_command = (
                "sudo cp /home/core/50-insecure-registry.conf "
                + "/etc/systemd/system/docker.service.d/50-insecure-registry.conf"
            )

            yield Command("sudo mkdir -p /etc/systemd/system/docker.service.d/")
            yield FileCopy("50-insecure-registry.conf", "/home/core")
            yield Command(cp_command)
            yield Command("sudo systemctl daemon-reload")

        yield FileCopy("Dockerfile.test", "/home/core/Dockerfile")

    def populate_test_image(self, registry_host, namespace, name):
        if self.requires_v1:
            # These versions of Docker don't support the new TLS cert on quay.io, so we need to pull
            # from v1.quay.io and then retag so the build works.
            yield Command("docker pull v1.quay.io/quay/busybox")
            yield Command("docker tag v1.quay.io/quay/busybox quay.io/quay/busybox")

        yield Command("docker build -t %s/%s/%s ." % (registry_host, namespace, name))

    def print_version(self):
        yield Command("docker version")

    def login(self, registry_host, username, password):
        email_param = ""
        if self.requires_email:
            # cli will block forever if email is not set for version under 1.10.3
            email_param = "--email=none "

        yield Command(
            "docker login --username=%s --password=%s %s %s"
            % (username, password, email_param, registry_host)
        )

    def push(self, registry_host, namespace, name):
        yield Command("docker push %s/%s/%s" % (registry_host, namespace, name))

    def pre_pull_cleanup(self, registry_host, namespace, name):
        prefix = "v1." if self.requires_v1 else ""
        yield Command("docker rmi -f %s/%s/%s" % (registry_host, namespace, name))
        yield Command("docker rmi -f %squay.io/quay/busybox" % prefix)

    def pull(self, registry_host, namespace, name):
        yield Command("docker pull %s/%s/%s" % (registry_host, namespace, name))

    def verify(self, registry_host, namespace, name):
        yield Command("docker run %s/%s/%s echo testfile" % (registry_host, namespace, name))


class PodmanClient(Client):
    def __init__(self):
        self.verify_tls = False

    def setup_client(self, registry_host, verify_tls):
        yield FileCopy("Dockerfile.test", "/home/vagrant/Dockerfile")
        self.verify_tls = verify_tls

    def populate_test_image(self, registry_host, namespace, name):
        yield Command(
            "sudo podman build -t %s/%s/%s /home/vagrant/" % (registry_host, namespace, name)
        )

    def print_version(self):
        yield Command("sudo podman version")

    def login(self, registry_host, username, password):
        yield Command(
            "sudo podman login --tls-verify=%s --username=%s --password=%s %s"
            % (self.verify_tls, username, password, registry_host)
        )

    def push(self, registry_host, namespace, name):
        yield Command(
            "sudo podman push --tls-verify=%s %s/%s/%s"
            % (self.verify_tls, registry_host, namespace, name)
        )

    def pre_pull_cleanup(self, registry_host, namespace, name):
        yield Command("sudo podman rmi -f %s/%s/%s" % (registry_host, namespace, name))
        yield Command("sudo podman rmi -f quay.io/quay/busybox")

    def pull(self, registry_host, namespace, name):
        yield Command(
            "sudo podman pull --tls-verify=%s %s/%s/%s"
            % (self.verify_tls, registry_host, namespace, name)
        )

    def verify(self, registry_host, namespace, name):
        yield Command("sudo podman run %s/%s/%s echo testfile" % (registry_host, namespace, name))
