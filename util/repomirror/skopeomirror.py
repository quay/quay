import base64
import json
import logging
import os
import subprocess
import urllib.parse
from collections import namedtuple
from pipes import quote
from tempfile import NamedTemporaryFile, SpooledTemporaryFile
from typing import Optional

logger = logging.getLogger(__name__)

SKOPEO_TIMEOUT_SECONDS = 300

# success: True or False whether call was successful
# tags: list of tags or empty list
# stdout: stdout from skopeo subprocess
# stderr: stderr from skopeo subprocess
SkopeoResults = namedtuple("SkopeoResults", "success tags stdout stderr")


def create_authfile_content(content):
    return dict(
        auths=dict(
            map(
                lambda x: (
                    f"{x[0]}",
                    {"auth": f"{base64.b64encode(x[1].encode('utf8')).decode('utf8')}"},
                ),
                filter(lambda y: y[1] != "", content),
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
        def wrap_anonymous(user, passwd):
            if user in ("", None):
                return ""
            if passwd in ("", None):
                return ""
            return f"{user}:{passwd}"

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
        content = create_authfile_content(
            [
                (
                    urllib.parse.urlparse(src_image).netloc,
                    f"{wrap_anonymous(src_username, src_password)}",
                ),
                (
                    urllib.parse.urlparse(dest_image).netloc,
                    f"{wrap_anonymous(dest_username, dest_password)}",
                ),
            ]
        )

        with NamedTemporaryFile() as authfile:
            authfile.write(json.dumps(content).encode("utf8"))
            authfile.flush()
            args.extend(["--authfile", authfile.name])
            args = args + [quote(src_image), quote(dest_image)]
            return self.run_skopeo(args, proxy)

    def tags(
        self,
        repository: str,
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
                (
                    urllib.parse.urlparse(repository).netloc,
                    f"{str(username)}:{str(password)}",
                ),
            ]
        )
        args = args + [repository]

        all_tags = []
        with NamedTemporaryFile() as authfile:
            authfile.write(json.dumps(content).encode("utf8"))
            authfile.flush()
            result = self.run_skopeo(args, proxy)
            if result.success:
                all_tags = json.loads(result.stdout)["Tags"]

        return SkopeoResults(result.success, all_tags, result.stdout, result.stderr)

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

    def run_skopeo(self, args, proxy):
        # Using a tempfile makes sure that if --debug is set, the stdout and stderr output
        # doesn't get truncated by the system's pipe limit.
        with SpooledTemporaryFile() as stdoutpipe, SpooledTemporaryFile() as stderrpipe:
            job = subprocess.Popen(
                args,
                shell=False,
                stdout=stdoutpipe,
                stderr=stderrpipe,
                env=self.setup_env(proxy),
            )

            try:
                job.wait(timeout=SKOPEO_TIMEOUT_SECONDS)
            except subprocess.TimeoutExpired:
                job.kill()
            finally:
                stdoutpipe.seek(0)
                stderrpipe.seek(0)
                stdout = stdoutpipe.read().decode("utf-8")
                stderr = stderrpipe.read().decode("utf-8")

                if job.returncode != 0:
                    logger.debug("Skopeo [STDERR]: %s" % stderr)
                    logger.debug("Skopeo [STDOUT]: %s" % stdout)

                return SkopeoResults(job.returncode == 0, [], stdout, stderr)
