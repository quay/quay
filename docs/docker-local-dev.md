# Docker Local Development Environment

The Quay team has developed and supports a Docker based local development environment.
This environment can quickly setup Quay and Clair for developing and testing changes.
When utilizing the local development environment changes to your source code are automatically hot-reloaded, taking effect in real time.

## Usage

The local development environment is driven by the following `makefile` targets:

### make local-dev-up

Deploys Quay and necessary dependencies.

#### Details

| Infra | Local Adress | Docker Network Address |
|  ---  |     ---      |          ---           |
|  Quay | `localhost:8080` | `quay-quay:8080`   |
|  Quay Database | `localhost:5432` | `quay-db:5432` |
|  Quay Redis | `localhost:6379` | `quay-redis:6379` |

### make local-dev-up-with-clair

Deploys Quay and necessary dependencies along with Clair.
The version of Clair deployed can be determined by viewing the docker compose file at `/docker-compose.yaml`.
Updating this field and restarting the local development environment will deploy a specified Clair version.

#### Details

| Infra | Local Adress | Docker Network Address |
|  ---  |     ---      |          ---           |
|  Quay | `localhost:8080` | `quay-quay:8080`   |
|  Quay Database | `localhost:5432` | `quay-db:5432` |
|  Quay Redis | `localhost:6379` | `quay-redis:6379` |
|  Clair | (not exposed) | `localhost:6000 from Quay container` |
|  Clair Database | `localhost:5433` | `clair-db:5432` |

*Note: Clair is deployed in the network namespace of the Quay container.
This allows Quay to provide Clair layer location information over `localhost`.*

### make local-dev-down

Tears down the local development environment.

#### Details

This make target stops and removes any containers currently running, regardless of whether `make local-dev-up` or `make local-dev-up-with-clair` was ran.
After containers are cleanly removed the script in `./local-dev/scripts/clean.sh` is ran to remove any files created or modified by the local development environment.

### make local-dev-clean

Cleans any created or modified files in the repository as a result of a local development deployment.
This target is ran explicitly by the all targets listed above.

#### Details

Typically this make target will not be ran manually, however its available to do so.
It's possible your repository may get into an odd state due to docker crashing or some other unexpected issue.
If that occurs running this target will restore your repistory to a good state (sans any changes to source code you made).

## Pushing to Quay

Container images can be tagged and pushed to your local quay instance.

The follow steps outline how to accomplish this:

* Visit `http://localhost:8080` and create an account. (Using the username 'admin' will create a superuser account).

* Create an organization and repository, we will refer to these as {org} and {repo}.

* Use podman or docker to login (we will use podman as pushing to http is far easier).
  * `$ podman login --tls-verify=false localhost:8080`

* Tag any image with the local development repository hostname, org, repo, and tag.
  * `$ podman tag ubuntu:latest localhost:8080/{org}/{repo}:{tag}`

* Push the tagged image to Quay
  * `$ podman push --tls-verify=false localhost:8080/{org}/{repo}:{tag}`

## Hot-Reload

The local development environment supports hot-reload of Quay, Quay workers, and the front end UI code.

Quay registry runs in production as a gunicorn worker so no changes except enabling hot-reload is necessary.

Quay workers run as generic python modules in production.
To support hot-reloading each worker was modified to run as a gunicorn worker sub-process (only for local-dev).
When the source code is updated and saved to disk the gunicorn worker is restarted.

The front end code supports hot-reload by running `npm watch` in the background during container startup.

## Troubleshooting

If you are having trouble with the local development environment run through the following common issues first.

### Quay and Clair initialization

Both Quay and Clair take some time to fully initialize.
This time is also bound to your workstation's resources.
Give the environment a few minutes to fully initialize.

If a considerable amount of time has passed you are able to view Quay and Clair logs for a hint.

``` shell
docker logs -f quay-quay
```

for quay logs

``` shell
docker logs -f quay-clair
```

for clair logs

### Docker Resources

If using Docker on macOS its possible the virtual machine used is too resource restrainted to host Quay.
You can modify these resources by following this tutorial:
<https://docs.docker.com/docker-for-mac/#resources>

Provide the vm more memory and cpu so ensure smooth performance.

Linux machines should not have this issue as Docker runs directly on the host and resources are not constrained by a VM.

### Firewalld

In certain cases firewalld may block network traffic between the host and containers.
If you are experiencing connectivity issues try disabling Firewalld or any other firewall on your host machine.

### Port conflicts

If you are running any containers or services on the same ports the local development environment tries to bind to you will experience connectivity issues or errors.

Make sure no other software is bound to the ports listed above while utilizing the local development environment.

