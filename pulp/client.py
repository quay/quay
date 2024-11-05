"""
Pulp doesn't provide an API client, we are implementing it for ourselves

Ref: https://github.com/fedora-copr/copr/blob/main/backend/copr_backend/pulp.py
"""

import os
import time
# import toml
from urllib.parse import urlencode
import requests


class PulpClient():
    """
    A client for interacting with Pulp API.

    API documentation:
    - https://docs.pulpproject.org/pulp_rpm/restapi.html
    - https://docs.pulpproject.org/pulpcore/restapi.html

    A note regarding PUT vs PATCH:
    - PUT changes all data and therefore all required fields needs to be sent
    - PATCH changes only the data that we are sending

    A lot of the methods require repository, distribution, publication, etc,
    to be the full API endpoint (called "pulp_href"), not simply their name.
    If method argument doesn't have "name" in its name, assume it expects
    pulp_href. It looks like this:
    /pulp/api/v3/publications/rpm/rpm/5e6827db-260f-4a0f-8e22-7f17d6a2b5cc/
    """

    # @classmethod
    # def create_from_config_file(cls, path=None):
    #     """
    #     Create a Pulp client from a standard configuration file that is
    #     used by the `pulp` CLI tool
    #     """
    #     path = os.path.expanduser(path or "pulp/cli.toml")
    #     with open(path, "rb") as fp:
    #         config = toml.load(fp)
    #     return cls(config["cli"])

    def __init__(self, config):
        self.config = config
        self.timeout = 60

    @property
    def auth(self):
        """
        https://requests.readthedocs.io/en/latest/user/authentication/
        """
        return (self.config["username"], self.config["password"])

    @property
    def cert(self):
        """
        See Client Side Certificates
        https://docs.python-requests.org/en/latest/user/advanced/
        """
        return (self.config["cert"], self.config["key"])

    def url(self, endpoint):
        """
        A fully qualified URL for a given API endpoint
        """
        domain = self.config["domain"]
        if domain == "default":
            domain = ""

        relative = os.path.normpath("/".join([
            self.config["api_root"],
            domain,
            endpoint,
        ]))

        # Normpath removes the trailing slash. If it was there, put it back
        if endpoint[-1] == "/":
            relative += "/"
        return self.config["base_url"] + relative

    @property
    def request_params(self):
        """
        Default parameters for our requests
        """
        params = {"timeout": self.timeout}
        if all(self.cert):
            params["cert"] = self.cert
        else:
            params["auth"] = self.auth
        return params

    def create_repository(self, name):
        """
        Create an RPM repository
        https://docs.pulpproject.org/pulp_rpm/restapi.html#tag/Repositories:-Rpm/operation/repositories_rpm_rpm_create
        """
        url = self.url("api/v3/repositories/rpm/rpm/")
        data = {"name": name, "autopublish": True}
        return requests.post(url, json=data, **self.request_params)

    def get_repository(self, name):
        """
        Get a single RPM repository
        https://docs.pulpproject.org/pulp_rpm/restapi.html#tag/Repositories:-Rpm/operation/repositories_rpm_rpm_list
        """
        # There is no endpoint for querying a single repository by its name,
        # even Pulp CLI does this workaround
        url = self.url("api/v3/repositories/rpm/rpm/?")
        url += urlencode({"name": name, "offset": 0, "limit": 1})
        return requests.get(url, **self.request_params)

    def get_distribution(self, name):
        """
        Get a single RPM distribution
        https://docs.pulpproject.org/pulp_rpm/restapi.html#tag/Distributions:-Rpm/operation/distributions_rpm_rpm_list
        """
        # There is no endpoint for querying a single repository by its name,
        # even Pulp CLI does this workaround
        url = self.url("api/v3/distributions/rpm/rpm/?")
        url += urlencode({"name": name, "offset": 0, "limit": 1})
        return requests.get(url, **self.request_params)

    def get_task(self, task):
        """
        Get a detailed information about a task
        """
        url = self.config["base_url"] + task
        return requests.get(url, **self.request_params)

    def create_distribution(self, name, repository, basepath=None):
        """
        Create an RPM distribution
        https://docs.pulpproject.org/pulp_rpm/restapi.html#tag/Distributions:-Rpm/operation/distributions_rpm_rpm_create
        """
        url = self.url("api/v3/distributions/rpm/rpm/")
        data = {
            "name": name,
            "repository": repository,
            "base_path": basepath or name,
        }
        return requests.post(url, json=data, **self.request_params)

    def create_publication(self, repository):
        """
        Create an RPM publication
        https://docs.pulpproject.org/pulp_rpm/restapi.html#tag/Publications:-Rpm/operation/publications_rpm_rpm_create
        """
        url = self.url("api/v3/publications/rpm/rpm/")
        data = {"repository": repository}
        return requests.post(url, json=data, **self.request_params)

    def update_distribution(self, distribution, publication):
        """
        Update an RPM distribution
        https://docs.pulpproject.org/pulp_rpm/restapi.html#tag/Distributions:-Rpm/operation/distributions_rpm_rpm_update
        """
        url = self.config["base_url"] + distribution
        data = {
            "publication": publication,
            # When we create a distribution, we point it to a repository. Now we
            # want to point it to a publication, so we need to reset the,
            # repository. Otherwise we will get "Only one of the attributes
            # 'repository' and 'publication' may be used simultaneously."
            "repository": None,
        }
        return requests.patch(url, json=data, **self.request_params)

    def create_content(self, repository, path=None, f=None):
        """
        Create content for a given artifact
        https://docs.pulpproject.org/pulp_rpm/restapi.html#tag/Content:-Packages/operation/content_rpm_packages_create
        """
        url = self.url("api/v3/content/rpm/packages/")
        data = {"repository": repository}
        if f is not None:
            files = {"file": f}
            return requests.post(
                url, data=data, files=files, **self.request_params
            )
        else:
            with open(path, "rb") as fp:
                data = {"repository": repository}
                files = {"file": fp}
                return requests.post(
                    url, data=data, files=files, **self.request_params
                )

    def delete_content(self, repository, artifacts):
        """
        Delete a list of artifacts from a repository
        https://pulpproject.org/pulp_rpm/restapi/#tag/Repositories:-Rpm/operation/repositories_rpm_rpm_modify
        """
        path = os.path.join(repository, "modify/")
        url = self.config["base_url"] + path
        data = {"remove_content_units": artifacts}
        return requests.post(url, json=data, **self.request_params)

    def delete_repository(self, repository):
        """
        Delete an RPM repository
        https://pulpproject.org/pulp_rpm/restapi/#tag/Repositories:-Rpm/operation/repositories_rpm_rpm_delete
        """
        url = self.config["base_url"] + repository
        return requests.delete(url, **self.request_params)

    def delete_distribution(self, distribution):
        """
        Delete an RPM distribution
        https://pulpproject.org/pulp_rpm/restapi/#tag/Distributions:-Rpm/operation/distributions_rpm_rpm_delete
        """
        url = self.config["base_url"] + distribution
        return requests.delete(url, **self.request_params)

    def wait_for_finished_task(self, task, timeout=86400):
        """
        Pulp task (e.g. creating a publication) can be running for an
        unpredictably long time. We need to wait until it is finished to know
        what it actually did.
        """
        start = time.time()
        while True:
            response = self.get_task(task)
            if not response.ok:
                break
            if response.json()["state"] not in ["waiting", "running"]:
                break
            if time.time() > start + timeout:
                break
            time.sleep(5)
        return response

    def list_distributions(self, prefix):
        """
        Get a list of distributions whose names match a given prefix
        https://pulpproject.org/pulp_rpm/restapi/#tag/Distributions:-Rpm/operation/distributions_rpm_rpm_list
        """
        url = self.url("api/v3/distributions/rpm/rpm/?")
        url += urlencode({"name__startswith": prefix})
        return requests.get(url, **self.request_params)
