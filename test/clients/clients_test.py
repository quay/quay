import os
import subprocess
import sys
import time

import unicodedata

from threading import Thread

from termcolor import colored

from test.clients.client import DockerClient, PodmanClient, Command, FileCopy


def remove_control_characters(s):
    return "".join(ch for ch in str(s, "utf-8") if unicodedata.category(ch)[0] != "C")


# These tuples are the box&version and the client to use.
BOXES = [
    ("kleesc/centos7-podman --box-version=0.11.1.1", PodmanClient()),  # podman 0.11.1.1
    ("kleesc/coreos --box-version=1911.4.0", DockerClient()),  # docker 18.06.1
    ("kleesc/coreos --box-version=1800.7.0", DockerClient()),  # docker 18.03.1
    ("kleesc/coreos --box-version=1688.5.3", DockerClient()),  # docker 17.12.1
    ("kleesc/coreos --box-version=1632.3.0", DockerClient()),  # docker 17.09.1
    ("kleesc/coreos --box-version=1576.5.0", DockerClient()),  # docker 17.09.0
    ("kleesc/coreos --box-version=1520.9.0", DockerClient()),  # docker 1.12.6
    ("kleesc/coreos --box-version=1235.6.0", DockerClient()),  # docker 1.12.3
    ("kleesc/coreos --box-version=1185.5.0", DockerClient()),  # docker 1.11.2
    ("kleesc/coreos --box-version=1122.3.0", DockerClient(requires_email=True)),  # docker 1.10.3
    ("kleesc/coreos --box-version=899.17.0", DockerClient(requires_email=True)),  # docker 1.9.1
    ("kleesc/coreos --box-version=835.13.0", DockerClient(requires_email=True)),  # docker 1.8.3
    ("kleesc/coreos --box-version=766.5.0", DockerClient(requires_email=True)),  # docker 1.7.1
    ("kleesc/coreos --box-version=717.3.0", DockerClient(requires_email=True)),  # docker 1.6.2
    ("kleesc/coreos --box-version=647.2.0", DockerClient(requires_email=True)),  # docker 1.5.0
    ("kleesc/coreos --box-version=557.2.0", DockerClient(requires_email=True)),  # docker 1.4.1
    ("kleesc/coreos --box-version=522.6.0", DockerClient(requires_email=True)),  # docker 1.3.3
    ("yungsang/coreos --box-version=1.3.7", DockerClient(requires_email=True)),  # docker 1.3.2
    ("yungsang/coreos --box-version=1.2.9", DockerClient(requires_email=True)),  # docker 1.2.0
    ("yungsang/coreos --box-version=1.1.5", DockerClient(requires_email=True)),  # docker 1.1.2
    ("yungsang/coreos --box-version=1.0.0", DockerClient(requires_email=True)),  # docker 1.0.1
    ("yungsang/coreos --box-version=0.9.10", DockerClient(requires_email=True)),  # docker 1.0.0
    ("yungsang/coreos --box-version=0.9.6", DockerClient(requires_email=True)),  # docker 0.11.1
]


def _check_vagrant():
    vagrant_command = "vagrant"
    vagrant = any(
        os.access(os.path.join(path, vagrant_command), os.X_OK)
        for path in os.environ.get("PATH").split(":")
    )
    vagrant_plugins = subprocess.check_output([vagrant_command, "plugin", "list"])
    return (vagrant, "vagrant-scp" in vagrant_plugins.decode("utf-8"))


def _load_ca(box, ca_cert):
    if "coreos" in box:
        yield FileCopy(ca_cert, "/home/core/ca.pem")
        yield Command("sudo cp /home/core/ca.pem /etc/ssl/certs/ca.pem")
        yield Command("sudo update-ca-certificates")
        yield Command("sudo systemctl daemon-reload")
    elif "centos" in box:
        yield FileCopy(ca_cert, "/home/vagrant/ca.pem")
        yield Command("sudo cp /home/vagrant/ca.pem /etc/pki/ca-trust/source/anchors/")
        yield Command("sudo update-ca-trust enable")
        yield Command("sudo update-ca-trust extract")
    else:
        raise Exception("unknown box for loading CA cert")


# extra steps to initialize the system
def _init_system(box):
    if "coreos" in box:
        # disable the update-engine so that it's easier to debug
        yield Command("sudo systemctl stop update-engine")


class CommandFailedException(Exception):
    pass


class SpinOutputter(Thread):
    def __init__(self, initial_message):
        super(SpinOutputter, self).__init__()
        self.previous_line = ""
        self.next_line = initial_message
        self.running = True
        self.daemon = True

    @staticmethod
    def spinning_cursor():
        while 1:
            for cursor in "|/-\\":
                yield cursor

    def set_next(self, text):
        first_line = text.split(b"\n")[0].strip()
        first_line = remove_control_characters(first_line)
        self.next_line = first_line[:80]

    def _clear_line(self):
        sys.stdout.write("\r")
        sys.stdout.write(" " * (len(self.previous_line) + 2))
        sys.stdout.flush()

        sys.stdout.write("\r")
        sys.stdout.flush()
        self.previous_line = ""

    def stop(self):
        self._clear_line()
        self.running = False

    def run(self):
        spinner = SpinOutputter.spinning_cursor()
        while self.running:
            self._clear_line()
            sys.stdout.write("\r")
            sys.stdout.flush()

            sys.stdout.write(next(spinner))
            sys.stdout.write(" ")
            sys.stdout.write(colored(self.next_line, attrs=["dark"]))
            sys.stdout.flush()

            self.previous_line = self.next_line
            time.sleep(0.25)


def _run_and_wait(command, error_allowed=False):
    # Run the command itself.
    outputter = SpinOutputter("Running command %s" % command)
    outputter.start()

    output = b""
    process = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    for line in iter(process.stdout.readline, b""):
        output += line
        outputter.set_next(line)

    result = process.wait()
    outputter.stop()

    failed = result != 0 and not error_allowed
    # vagrant scp doesn't report auth failure as non-0 exit
    failed = failed or (
        len(command) > 1
        and command[1] == "scp"
        and "authentication failures" in output.decode("utf-8")
    )

    if failed:
        print(colored(">>> Command `%s` Failed:" % command, "red"))
        print(output.decode("utf-8"))
        raise CommandFailedException()

    return output.decode("utf-8")


def _indent(text, amount):
    return "".join((" " * amount) + line for line in text.splitlines(True))


def scp_to_vagrant(source, destination):
    """
    scp_to_vagrant copies the file from source to destination in the default vagrant box without
    vagrant scp, which may fail on some coreos boxes.
    """
    config = _run_and_wait(["vagrant", "ssh-config"])
    config_lines = config.split("\n")
    params = ["scp"]
    for i in range(len(config_lines)):
        if "Host default" in config_lines[i]:
            config_i = i + 1
            while config_i < len(config_lines):
                if config_lines[config_i].startswith("  "):
                    params += ["-o", "=".join(config_lines[config_i].split())]
                else:
                    break

                config_i += 1
            break

    params.append(source)
    params.append("core@localhost:" + destination)
    return _run_and_wait(params)


def _run_commands(commands):
    last_result = None
    for command in commands:
        if isinstance(command, Command):
            last_result = _run_and_wait(["vagrant", "ssh", "-c", command.command])
        else:
            try:
                last_result = _run_and_wait(
                    ["vagrant", "scp", "test/clients/%s" % command.source, command.destination]
                )
            except CommandFailedException as e:
                print(colored(">>> Retry FileCopy command without vagrant scp...", "red"))
                # sometimes the vagrant scp fails because of invalid ssh configuration.
                last_result = scp_to_vagrant(command.source, command.destination)

    return last_result


def _run_box(box, client, registry, ca_cert):
    vagrant, vagrant_scp = _check_vagrant()
    if not vagrant:
        print("vagrant command not found")
        return

    if not vagrant_scp:
        print("vagrant-scp plugin not installed")
        return

    namespace = "devtable"
    repo_name = "testrepo%s" % int(time.time())
    username = "devtable"
    password = "password"

    print(colored(">>> Box: %s" % box, attrs=["bold"]))
    print(colored(">>> Starting box", "yellow"))
    _run_and_wait(["vagrant", "destroy", "-f"], error_allowed=True)
    _run_and_wait(["rm", "Vagrantfile"], error_allowed=True)
    _run_and_wait(["vagrant", "init"] + box.split(" "))
    _run_and_wait(["vagrant", "up", "--provider", "virtualbox"])

    _run_commands(_init_system(box))

    if ca_cert:
        print(colored(">>> Setting up runtime with cert " + ca_cert, "yellow"))
        _run_commands(_load_ca(box, ca_cert))
        _run_commands(client.setup_client(registry, verify_tls=True))
    else:
        print(colored(">>> Setting up runtime with insecure HTTP(S)", "yellow"))
        _run_commands(client.setup_client(registry, verify_tls=False))

    print(colored(">>> Client version", "cyan"))
    runtime_version = _run_commands(client.print_version())
    print(_indent(runtime_version, 4))

    print(colored(">>> Populating test image", "yellow"))
    _run_commands(client.populate_test_image(registry, namespace, repo_name))

    print(colored(">>> Testing login", "cyan"))
    _run_commands(client.login(registry, username, password))

    print(colored(">>> Testing push", "cyan"))
    _run_commands(client.push(registry, namespace, repo_name))

    print(colored(">>> Removing all images", "yellow"))
    _run_commands(client.pre_pull_cleanup(registry, namespace, repo_name))

    print(colored(">>> Testing pull", "cyan"))
    _run_commands(client.pull(registry, namespace, repo_name))

    print(colored(">>> Verifying", "cyan"))
    _run_commands(client.verify(registry, namespace, repo_name))

    print(colored(">>> Tearing down box", "magenta"))
    _run_and_wait(["vagrant", "destroy", "-f"], error_allowed=True)

    print(colored(">>> Successfully tested box %s" % box, "green"))
    print("")


def test_clients(registry="10.0.2.2:5000", ca_cert=""):
    print(colored(">>> Running against registry ", attrs=["bold"]) + colored(registry, "cyan"))
    for box, client in BOXES:
        try:
            _run_box(box, client, registry, ca_cert)
        except CommandFailedException:
            sys.exit(-1)


if __name__ == "__main__":
    test_clients(
        sys.argv[1] if len(sys.argv) > 1 else "10.0.2.2:5000",
        sys.argv[2] if len(sys.argv) > 2 else "",
    )
