# Quay config tool

The Quay config tool is a project to ease the setup, modification, and deployment of Red Hat Quay (sometimes referred to as Red Hat Quay).

The project was built by [Sam Chow] in the summer of 2018.

[Sam Chow]: https://github.com/blueish

## Project Features
* Isolated setup tool for creating the config
* Ability to download config as a tarball
* Ability to load your config from a tarball and modify it
* When running on Kubernetes, allows you to deploy your changes to the current cluster and cycles all pods
* When running on Kubernetes, allows you to modify the existing configuration


## Project Layout
- `conf/` - nginx/gunicorn configuration

- `config_endpoints/` - backend flask endpoints for serving web and all other API endpoints

- `config_util/` - utils used by api endpoints for accessing k8s, etc.

- `config_util/config` - config providers used to manipulate the local config directory before being tarred, uploaded, etc.

- `docs/` - some updated documentation on how to run the app in both a docker container and on kubernetes

- `init/` - initial scripts/services started by the docker image

- `js/` - all frontend javascript

- `js/components` - mix of the old components ported over, and new components written for the config tool.
(config-setup-app is the entrypoint of the frontend)

- `js/core-config-setup` - The main component responsible for modification of the config.
Holds most of the components that modify the configuration

- `js/setup` - The modal component that covers the setup of the DB and SuperUser

## Running the config tool
Currently, the config tool is still being built alongside the regular Quay container, and is started with the `config` argument to the image. A password is required to be
specified, which will then need to be entered with the username `quayconfig` in the browser.

```bash
docker run {quay-image} config {password}
```

The password can also be specified via the `CONFIG_APP_PASSWORD` environment variable:

```bash
docker run -e CONFIG_APP_PASSWORD={password} {quay-image} config
```


## Local development
If you wish to work on it locally, there's a script in the base dir of quay:
```bash
./local-config-app.sh
```
Webpack is setup for hot reloading so the JS will be rebuilt if you're working on it.


## Local development on kubernetes
Assuming you're running on minikube, you can build the docker image with the minikube docker daemon:
```bash
eval $(minikube docker-env)
docker built -t config-app . # run in quay dir, not quay/config_app
```

You'll now have to create the namespace, config secret (and optionally the quay-enterprise app and nodeport)
- [quay-enterprise-namespace.yml](files/quay-enterprise-namespace.yml)
- [quay-enterprise-config-secret.yml](files/quay-enterprise-config-secret.yml)
- [quay-enterprise-redis.yml](files/quay-enterprise-redis.yml)

(Optional, use if you're testing the deployment feature on kube)
- [quay-enterprise-app-rc.yml](files/quay-enterprise-app-rc.yml)
- [quay-enterprise-service-nodeport.yml](files/quay-enterprise-service-nodeport.yml)

And the following for the config-tool
- [config-tool-service-nodeport.yml](docs/k8s_templates/config-tool-service-nodeport.yml)
- [config-tool-serviceaccount.yml](docs/k8s_templates/config-tool-serviceaccount.yml)
- [config-tool-servicetoken-role.yml](docs/k8s_templates/config-tool-servicetoken-role.yml)
- [config-tool-servicetoken-role-binding.yml](docs/k8s_templates/config-tool-servicetoken-role-binding.yml)
- [qe-config-tool.yml](docs/k8s_templates/qe-config-tool.yml)
(Note: right now the config tool template uses the tag `config-tool:latest`, which will be the image you created in the minikube docker)

Apply all of these onto the cluster
```bash
kubectl apply -f <name-of-file>
```

You can get minikube to route you to the services:
```bash
minikube service quay-enterprise-config-tool -n quay-enterprise
```

It should open up on your default browser.

(Note: The config tool is only available through SSL and self-signs certs on startup, so you'll have to use https://\<route>
and pass through the warning on your browser to access it.)

When you make changes to the app, you'll have to rebuild the image and cycle the deployment:
```bash
kubectl scale deploy --replicas=0 quay-enterprise-config-tool -n quay-enterprise
kubectl scale deploy --replicas=1 quay-enterprise-config-tool -n quay-enterprise
```
