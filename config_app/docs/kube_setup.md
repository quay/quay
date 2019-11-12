# Red Hat Quay Installation on Kubernetes

This guide walks through the deployment of [Red Hat Quay][quay-enterprise-tour] onto a Kubernetes cluster.
After completing the steps in this guide, a deployer will have a functioning instance of Red Hat Quay orchestrated as a Kubernetes service on a cluster, and will be able to access the Red Hat Quay Setup tool with a browser to complete configuration of image repositories, builders, and users.

[quay-enterprise-tour]: https://quay.io/tour/enterprise

## Prerequisites

A PostgreSQL database must be available for Red Hat Quay metadata storage.
We currently recommend running this database server outside of the cluster.

## Download Kubernetes Configuration Files

Visit the [RedHat Documentation][RedHat-documentation] and download the pre-formatted pull secret, under "Account Assets". There are several formats of the secret, be sure to download the "dockercfg" format resulting in a `config.json` file. This pull secret is used to download the Red Hat Quay containers.

This will be used later in the guide.

[RedHat-documentation]: https://access.redhat.com/documentation/en-us/

Next, download each of the following files to your workstation, placing them alongside your pull secret:

- [quay-enterprise-namespace.yml](k8s_templates/quay-enterprise-namespace.yml)
- [quay-enterprise-config-secret.yml](k8s_templates/quay-enterprise-config-secret.yml)
- [quay-enterprise-redis.yml](k8s_templates/quay-enterprise-redis.yml)
- [quay-enterprise-app-rc.yml](k8s_templates/quay-enterprise-app-rc.yml)
- [quay-enterprise-service-nodeport.yml](k8s_templates/quay-enterprise-service-nodeport.yml)
- [quay-enterprise-service-loadbalancer.yml](k8s_templates/quay-enterprise-service-loadbalancer.yml)

## Role Based Access Control

Red Hat Quay has native Kubernetes integrations. These integrations require Service Account to have access to Kubernetes API. When Kubernetes RBAC is enabled, Role Based Access Control policy manifests also have to be deployed.

Kubernetes API has minor changes between versions 1.4 and 1.5, Download appropiate versions of Role Based Access Control (RBAC) Policies.

### Kubernetes v1.6.x and later RBAC Policies 

- [quay-servicetoken-role.yaml](k8s_templates/quay-servicetoken-role-k8s1-6.yaml)
- [quay-servicetoken-role-binding.yaml](k8s_templates/quay-servicetoken-role-binding-k8s1-6.yaml)


## Deploy to Kubernetes

All Kubernetes objects will be deployed under the "quay-enterprise" namespace.
The first step is to create this namespace:

```sh
kubectl create -f quay-enterprise-namespace.yml
```

Next, add your pull secret to Kubernetes (make sure you specify the correct path to `config.json`):

```sh
kubectl create secret generic coreos-pull-secret --from-file=".dockerconfigjson=config.json" --type='kubernetes.io/dockerconfigjson' --namespace=quay-enterprise
```

### Kubernetes v1.6.x and later : Deploy RBAC Policies

```sh
kubectl create -f quay-servicetoken-role-k8s1-6.yaml
kubectl create -f quay-servicetoken-role-binding-k8s1-6.yaml
```

### Deploy Red Hat Quay objects

Finally, the remaining Kubernetes objects can be deployed onto Kubernetes:

```sh
kubectl create -f quay-enterprise-config-secret.yml -f quay-enterprise-redis.yml -f quay-enterprise-app-rc.yml
```

## Expose via Kubernetes Service

In order to access Red Hat Quay, a user must route to it through a Kubernetes Service.
It is up to the deployer to decide which Service type is appropriate for their use case: a [LoadBalancer](http://kubernetes.io/docs/user-guide/services/#type-loadbalancer) or a [NodePort](http://kubernetes.io/docs/user-guide/services/#type-nodeport).

A LoadBalancer is recommended if the Kubernetes cluster is integrated with a cloud provider, otherwise a NodePort will suffice.
Along with this guide are examples of this service.

### LoadBalancer

Using the sample provided, a LoadBalancer Kubernetes Service can be created like so:

```sh
kubectl create -f quay-enterprise-service-loadbalancer.yml
```

kubectl can be used to find the externally-accessible URL of the quay-enterprise service:

```sh
kubectl describe services quay-enterprise --namespace=quay-enterprise
```

### NodePort

Using the sample provided, a NodePort Kubernetes Service can be created like so:

```sh
kubectl create -f quay-enterprise-service-nodeport.yml
```

By default, the quay-enterprise service will be available on port 30080 on every node in the Kubernetes cluster.
If this port conflicts with an existing Kubernetes Service, simply modify the sample configuration file and change the value of NodePort.

## Continue with Red Hat Quay Setup

All that remains is to configure Red Hat Quay itself through the configuration tool.

Download the following files to your workstation:

- [config-tool-service-nodeport.yml](k8s_templates/config-tool-service-nodeport.yml)
- [config-tool-serviceaccount.yml](k8s_templates/config-tool-serviceaccount.yml)
- [config-tool-servicetoken-role.yml](k8s_templates/config-tool-servicetoken-role.yml)
- [config-tool-servicetoken-role-binding.yml](k8s_templates/config-tool-servicetoken-role-binding.yml)
- [qe-config-tool.yml](k8s_templates/qe-config-tool.yml)

### Configuring RBAC for the configuration tool

Apply the following policies to allow the config tool to make changes to the Q.E. deployment:
```bash
kubectl apply -f config-tool-serviceaccount.yaml
```
```bash
kubectl apply -f config-tool-servicetoken-role.yaml
```
```bash
kubectl apply -f config-tool-servicetoken-role-binding.yaml
```

### Deploy Config Tool 

Deploy the configuration tool and route a service to it:
```bash
kubectl apply -f qe-config-tool.yml -f config-tool-service-nodeport.yml
```

By default, the config-tool service will be available on port 30090 on every node in the Kubernetes cluster.
Similar to the Quay application service, if this port conflicts with an existing Kubernetes Service, simply modify the sample configuration file and change the value of NodePort.
Once at the Red Hat Quay setup UI, follow the setup instructions to finalize your installation.

## Using the Configuration Tool
Click on "Start New Configuration for this Cluster", and follow the instructions to create your configuration, downloading and saving it (to load as a backup or if you ever wish to change your settings).
You will also be able to deploy the configuration to all instances by hitting "Deploy". Allow for a minute for the Quay instances to cycle the pods, and your configuration will be enacted once the pods have started.
