# Table of Contents

 * [Deploying Quay](#deploying-quay)
 * [Running Quay For Development](#running-quay-for-development)
     * [Requirements](#requirements)
     * [Building and Running with Docker Compose](#building-and-running-with-docker-compose)
     * [Hot-Reload](#hot-reload)
     * [Troubleshooting](#troubleshooting)
     * [Running Tests](#running-tests)
     * [Contributing](#contributing)
 * [Using Quay](#using-quay)

# Deploying Quay

If your goal is not to develop Quay, see the below guides.

 * [Deploy a Quick Local Environment With Podman](quick-local-deployment.md)
 * [Deploy a Proof-of-Concept](https://docs.projectquay.io/deploy_quay.html)
 * [Deploy to OpenShift with the Quay Operator](https://docs.projectquay.io/deploy_quay_on_openshift_op_tng.html)
 * [Deploy with High Availability](https://docs.projectquay.io/deploy_quay_ha.html)

# Running Quay For Development

The Quay team has developed and supports a Docker based local development environment.
This environment can quickly setup Quay and Clair for developing and testing changes.
When utilizing the local development environment changes to your source code are automatically hot-reloaded, taking effect in real time.

Beyond Docker and docker-compose, to develop Quay you will also need Python and the full set of requirements in order to successfully run the test suite.
Python 3.9 and earlier are currently supported.

## Requirements

 - Docker
 - docker-compose
 - Python 3.9
 - Node 16.12.0
 - libmagic

:exclamation: Be mindful that overriding your operating system's default Python version is not a good idea. Check out [this guide](https://access.redhat.com/documentation/en-us/red_hat_enterprise_linux/8/html/configuring_basic_system_settings/assembly_installing-and-using-python_configuring-basic-system-settings) for instructions on installing Python 3 on RHEL 8, or alternatively use [pyenv](https://github.com/pyenv/pyenv#readme).

Run either of the following in the quay directory where the repository is forked. It installs the pre-commit checks like trailing-whitespace, new line at EOF, secret leaks and black required before pushing to git.

```
pip install pre-commit==2.20.0

pre-commit install
```

or you can run:

```
make install-pre-commit-hook
```

## Building and Running with Docker Compose

The below commands rely on Docker and Docker Compose to be installed. You can also run Quay with podman - refer to the project's [`docker-compose.yml`](https://github.com/quay/quay/blob/c507eeff2eae61efe1a18a4b0e6addce4d37bc5a/docker-compose.yaml) file to understand and reproduce the setup.

### Starting Quay

To run Quay's basic components and database, use the `local-dev-up` make target.

:exclamation: If using Docker Desktop it's possible the virtual machine used is too resource constrained to host Quay. Refer to the [Docker Desktop manual](https://docs.docker.com/desktop/mac/#resources) for instructions on increasing resources. Make sure to provide Docker Desktop with more memory and CPU to ensure smooth performance.

```shell
make local-dev-up
```

Components started:

| Infra | Local Adress | Docker Network Address |
|  ---  |     ---      |          ---           |
|  Quay | `localhost:8080` | `quay-quay:8080`   |
|  Quay Database | `localhost:5432` | `quay-db:5432` |
|  Quay Redis | `localhost:6379` | `quay-redis:6379` |

### Starting Quay With Clair

To also run Clair, use the `local-dev-up-with-clair` make target instead.

```shell
make local-dev-up-with-clair
```

Components started:

| Infra | Local Adress | Docker Network Address |
|  ---  |     ---      |          ---           |
|  Quay | `localhost:8080` | `quay-quay:8080`   |
|  Quay Database | `localhost:5432` | `quay-db:5432` |
|  Quay Redis | `localhost:6379` | `quay-redis:6379` |
|  Clair | (not exposed) | `localhost:6000 from Quay container` |
|  Clair Database | `localhost:5433` | `clair-db:5432` |

*Note: Clair is deployed in the network namespace of the Quay container.
This allows Quay to provide Clair layer location information over `localhost`.*

## Hot-Reload

The local development environment supports hot-reload of Quay, Quay workers, and the front end UI code.

Quay registry runs in production as a gunicorn worker so no changes except enabling hot-reload is necessary.

Quay workers run as generic python modules in production.
To support hot-reloading each worker was modified to run as a gunicorn worker sub-process (only for local-dev).
When the source code is updated and saved to disk the gunicorn worker is restarted.

The front end code supports hot-reload by running `npm watch` in the background during container startup.

## Container Reload

The make target `local-docker-rebuild` focuses on reloading all running docker containers. By default only `quay-quay`, `quay-db` and `quay-redis` are rebuilt. `quay-clair` and `clair-db` can be included in rebuild by passing an optional `CLAIR` variable.

```
CLAIR=true make local-docker-rebuild
```

## Troubleshooting

Here you'll find some common troubles people run into while setting up their local development environments.

### Not Enough Resources

If using Docker Desktop it's possible the virtual machine used is too resource constrained to host Quay. Refer to the [Docker Desktop manual](https://docs.docker.com/desktop/mac/#resources) for instructions on increasing resources. Make sure to provide Docker Desktop with more memory and CPU to ensure smooth performance.

### Blocked Traffic (Firewalld)

In certain cases firewalld may block network traffic between the host and containers.
If you are experiencing connectivity issues try disabling Firewalld or any other firewall on your host machine.

### Port conflicts

If you are running any containers or services on the same ports the local development environment tries to bind to you will experience connectivity issues or errors.
Make sure no other software is bound to the required ports (see [Starting Quay](#starting-quay) and [Starting Quay With Clair](#starting-quay-with-clair) for the full list) while utilizing the local development environment.

## Running Tests

Quay is covered by tests using various approaches. Read our [testing guide](/TESTING.md) for details.

## Contributing

How great that you want to contribute to Quay! Before starting make sure to check our [contributing guidelines](../.github/CONTRIBUTING.md).

# Using Quay

Container images can be tagged and pushed to your local quay instance.

The following steps outline how to accomplish this:

NOTE: if you're using docker instead of podman, make sure to configure the
docker daemon to accept insecure registries by following
[this guide](https://docs.docker.com/registry/insecure/).

* Visit `http://localhost:8080` and create an account. (Using the username 'admin' will create a superuser account).

* Create an organization and repository, we will refer to these as {org} and {repo}.

* Use podman or docker to login (we will use podman as pushing to http is far easier).
  * `$ podman login --tls-verify=false localhost:8080`

* Tag any image with the local development repository hostname, org, repo, and tag.
  * `$ podman tag ubuntu:latest localhost:8080/{org}/{repo}:{tag}`

* Push the tagged image to Quay
  * `$ podman push --tls-verify=false localhost:8080/{org}/{repo}:{tag}`
