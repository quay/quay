import base64
import json
import logging
import os
import re
import subprocess
import urllib.parse
from collections import namedtuple
from shlex import quote
from tempfile import NamedTemporaryFile, SpooledTemporaryFile
from typing import Optional

logger = logging.getLogger(__name__)

_SANITIZE_PATTERNS = [
    (re.compile(r"(Authorization:\s*)\S+.*", re.IGNORECASE), r"\1[REDACTED]"),
    (re.compile(r"(--(src-creds|dest-creds|creds)[=\s]+)\S+", re.IGNORECASE), r"\1[REDACTED]"),
    (re.compile(r'("auth"\s*:\s*")[^"]+(")', re.IGNORECASE), r"\1[REDACTED]\2"),
]

SKOPEO_TIMEOUT_SECONDS = 300

_FILESYSTEM_TRANSPORTS = frozenset({"oci-archive", "oci", "dir", "docker-archive"})


def _registry_netloc(image: str) -> Optional[str]:
    """Return the registry hostname for an image URI, or None for filesystem transports.

    Filesystem transports (oci-archive, dir, docker-archive, oci) have no registry
    host; returning None prevents empty-string keys in the authfile.
    """
    transport = image.partition(":")[0].lower()
    if transport in _FILESYSTEM_TRANSPORTS:
        return None
    if transport == "docker-daemon":
        remainder = image.split(":", 1)[1].lstrip("/")
        parts = remainder.split("/")
        return parts[0] if len(parts) > 1 else None
    return urllib.parse.urlparse(image).netloc or None


def sanitize_skopeo_output(output: Optional[str]) -> Optional[str]:
    if not output:
        return output
    for pattern, replacement in _SANITIZE_PATTERNS:
        output = pattern.sub(replacement, output)
    return output


# success: True or False whether call was successful
# tags: list of tags or empty list
# stdout: stdout from skopeo subprocess
# stderr: stderr from skopeo subprocess
SkopeoResults = namedtuple("SkopeoResults", "success tags stdout stderr")
AuthContent = namedtuple("AuthContent", ["location", "username", "password"])


def wrap_anonymous(user: Optional[str] = None, passwd: Optional[str] = None) -> str:
    """Return 'user:passwd' for use in a Docker auth entry, or '' if either value is absent."""
    if user in ("", None):
        return ""
    if passwd in ("", None):
        return ""
    return f"{user}:{passwd}"


def create_authfile_content(content: list) -> dict:
    """Build a Docker-style auth.json dict from a list of AuthContent entries.

    Entries with a None/empty username or a None/empty location are excluded so
    the authfile only contains registries that actually require authentication
    and have a resolvable registry hostname.
    """
    return dict(
        auths=dict(
            map(
                lambda x: (
                    x.location,
                    {
                        "auth": base64.b64encode(
                            wrap_anonymous(x.username, x.password).encode("utf8")
                        ).decode("utf8")
                    },
                ),
                filter(
                    lambda y: y.username not in ("", None) and y.location not in ("", None),
                    content,
                ),
            )
        )
    )


class SkopeoMirror(object):

    # No DB calls here: This will be called from a separate worker that has no connection except
    # to/from the mirror worker
    def copy(
        self,
        src_image,
        dest_image,
        timeout,
        src_tls_verify=True,
        dest_tls_verify=True,
        src_username=None,
        src_password=None,
        dest_username=None,
        dest_password=None,
        proxy=None,
        verbose_logs=False,
        unsigned_images=False,
    ):
        """Copy src_image to dest_image via skopeo, using a temporary authfile for credentials."""
        args = ["/usr/bin/skopeo"]
        if verbose_logs:
            args = args + ["--debug"]
        if unsigned_images:
            args = args + ["--insecure-policy"]

        args = args + [
            "copy",
            "--all",
            "--remove-signatures",
            "--src-tls-verify=%s" % src_tls_verify,
            "--dest-tls-verify=%s" % dest_tls_verify,
        ]
        logger.debug(
            "Creating mirroring job: upstream image %s, local repository %s", src_image, dest_image
        )
        content = create_authfile_content(
            [
                AuthContent(_registry_netloc(src_image), src_username, src_password),
                AuthContent(_registry_netloc(dest_image), dest_username, dest_password),
            ]
        )

        with NamedTemporaryFile() as authfile:
            authfile.write(json.dumps(content).encode("utf8"))
            authfile.flush()
            args.extend(["--authfile", authfile.name])
            args = args + [quote(src_image), quote(dest_image)]
            return self.run_skopeo(args, proxy, timeout)

    def tags(
        self,
        repository: str,
        timeout: int,
        username: Optional[str] = None,
        password: Optional[str] = None,
        verify_tls: bool = True,
        proxy: Optional[dict[str, str]] = None,
        verbose_logs: bool = False,
    ) -> SkopeoResults:
        """
        Unless a specific tag is known, 'skopeo inspect' won't work.

        Here first 'latest' is checked and then the tag expression, split at commas, is each checked
        until one works.
        """

        args = ["/usr/bin/skopeo"]
        if verbose_logs:
            args = args + ["--debug"]
        args = args + ["list-tags", "--tls-verify=%s" % verify_tls]
        content = create_authfile_content(
            [
                AuthContent(_registry_netloc(repository), username, password),
            ]
        )

        all_tags = []
        with NamedTemporaryFile() as authfile:
            authfile.write(json.dumps(content).encode("utf8"))
            authfile.flush()
            args.extend(["--authfile", authfile.name])
            args = args + [repository]
            result = self.run_skopeo(args, proxy, timeout)
            if result.success:
                all_tags = json.loads(result.stdout)["Tags"]

        return SkopeoResults(result.success, all_tags, result.stdout, result.stderr)

    def inspect_raw(
        self,
        image: str,
        timeout: int,
        username: Optional[str] = None,
        password: Optional[str] = None,
        verify_tls: bool = True,
        proxy: Optional[dict[str, str]] = None,
        verbose_logs: bool = False,
    ) -> SkopeoResults:
        """
        Fetch the raw manifest (or manifest list) for an image.
        Uses: skopeo inspect --raw docker://image
        """
        args = ["/usr/bin/skopeo"]
        if verbose_logs:
            args = args + ["--debug"]
        args = args + ["inspect", "--raw", "--tls-verify=%s" % verify_tls]
        content = create_authfile_content(
            [AuthContent(_registry_netloc(image), username, password)]
        )
        with NamedTemporaryFile() as authfile:
            authfile.write(json.dumps(content).encode("utf8"))
            authfile.flush()
            args.extend(["--authfile", authfile.name])
            args = args + [image]
            return self.run_skopeo(args, proxy or {}, timeout)

    def inspect(
        self,
        image: str,
        timeout: int,
        username: Optional[str] = None,
        password: Optional[str] = None,
        verify_tls: bool = True,
        proxy: Optional[dict[str, str]] = None,
        verbose_logs: bool = False,
    ) -> SkopeoResults:
        """
        Inspect image metadata (resolves config blob).
        Uses: skopeo inspect docker://image
        Returns JSON with Architecture, Os, Digest, etc.
        """
        args = ["/usr/bin/skopeo"]
        if verbose_logs:
            args = args + ["--debug"]
        args = args + ["inspect", "--tls-verify=%s" % verify_tls]
        content = create_authfile_content(
            [AuthContent(_registry_netloc(image), username, password)]
        )
        with NamedTemporaryFile() as authfile:
            authfile.write(json.dumps(content).encode("utf8"))
            authfile.flush()
            args.extend(["--authfile", authfile.name])
            args = args + [image]
            return self.run_skopeo(args, proxy or {}, timeout)

    def copy_by_digest(
        self,
        src_image_with_digest: str,
        dest_image_with_digest: str,
        timeout: int,
        src_tls_verify: bool = True,
        dest_tls_verify: bool = True,
        src_username: Optional[str] = None,
        src_password: Optional[str] = None,
        dest_username: Optional[str] = None,
        dest_password: Optional[str] = None,
        proxy: Optional[dict[str, str]] = None,
        verbose_logs: bool = False,
        unsigned_images: bool = False,
    ) -> SkopeoResults:
        """
        Copy a specific manifest by digest (no --all flag).
        """
        args = ["/usr/bin/skopeo"]
        if verbose_logs:
            args = args + ["--debug"]
        if unsigned_images:
            args = args + ["--insecure-policy"]
        args = args + [
            "copy",
            "--preserve-digests",
            "--remove-signatures",
            "--src-tls-verify=%s" % src_tls_verify,
            "--dest-tls-verify=%s" % dest_tls_verify,
        ]
        content = create_authfile_content(
            [
                AuthContent(
                    _registry_netloc(src_image_with_digest),
                    src_username,
                    src_password,
                ),
                AuthContent(
                    _registry_netloc(dest_image_with_digest),
                    dest_username,
                    dest_password,
                ),
            ]
        )
        with NamedTemporaryFile() as authfile:
            authfile.write(json.dumps(content).encode("utf8"))
            authfile.flush()
            args.extend(["--authfile", authfile.name])
            args = args + [quote(src_image_with_digest), quote(dest_image_with_digest)]
            return self.run_skopeo(args, proxy or {}, timeout)

    def external_registry_credentials(
        self, arg: str, username: Optional[str], password: Optional[str]
    ) -> list[str]:
        credentials = []
        if username is not None and username != "":
            if password is not None and password != "":
                creds = "%s:%s" % (username, password)
            else:
                creds = "%s" % username
            credentials = [arg, creds]

        return credentials

    def setup_env(self, proxy):
        env = os.environ.copy()

        if proxy.get("http_proxy"):
            env["HTTP_PROXY"] = proxy.get("http_proxy")
        if proxy.get("https_proxy"):
            env["HTTPS_PROXY"] = proxy.get("https_proxy")
        if proxy.get("no_proxy"):
            env["NO_PROXY"] = proxy.get("no_proxy")

        return env

    def run_skopeo(self, args, proxy, timeout):
        # Using a tempfile makes sure that if --debug is set, the stdout and stderr output
        # doesn't get truncated by the system's pipe limit.

        with SpooledTemporaryFile() as stdoutpipe, SpooledTemporaryFile() as stderrpipe:
            logger.debug("Setting job timeout: %s s", timeout)
            job = subprocess.Popen(
                args,
                shell=False,
                stdout=stdoutpipe,
                stderr=stderrpipe,
                env=self.setup_env(proxy),
            )

            try:
                job.wait(timeout=timeout)
            except subprocess.TimeoutExpired:
                job.kill()
            finally:
                stdoutpipe.seek(0)
                stderrpipe.seek(0)
                stdout = sanitize_skopeo_output(stdoutpipe.read().decode("utf-8"))
                stderr = sanitize_skopeo_output(stderrpipe.read().decode("utf-8"))

                if job.returncode != 0:
                    logger.debug(
                        "Skopeo command failed (exit code %s): %s",
                        job.returncode,
                        stderr.strip(),
                    )

                return SkopeoResults(job.returncode == 0, [], stdout, stderr)
