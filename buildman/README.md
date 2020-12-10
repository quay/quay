# Quay build manager
The build manager handles the state of build jobs and spawning/cleaning up build workers on specified control planes (AWS/k8s/...).
The general flow is:
- A build is created and queued.
- A build is picked from the queue by a build manager.
  - The build manager attempts to schedule the build on the control plane(s) based on what is configured.
    This starts a build worker bootstrapped with the necessary registration token. At this point, the image build has not started yet.
  - The build worker invoke the build manager's RPC endpoint to register the build job. This is done within a max_startup_time frame,
    otherwise the build should expire. If successful, the build manager will return a buildpack with the necessary data to start the build.
- At this point, the buils has started on the worker node.
  - A "heartbeat" stream is started by the worker on the `Heartbeat` rpc to prevent the job from expiring.
  - The build phase is updated through the `SetPhase` rpc.
  - Build logs from the building phase (`docker build`'s stdout) are streamed to the `LogMessage` rpc.
- Once the build reaches a "completed" state, or expires, the build manager handles updating the queue + cleaning any worker nodes.

To enable build:
```
FEATURE_BUILD_SUPPORT: True
BUILD_MANAGER:
- ephemeral
- <manager_config>
```

To set an upper bound to the number of simultaneous build that can run:
```
  ALLOWED_WORKER_COUNT: 10
```

## Orchestrator
The orchestrator keeps track of the running jobs, and publishes job events for the build manager to consume.
Redis is the currently supported orchestrator backend.
```
  ORCHESTRATOR_PREFIX: buildman/production/
  ORCHESTRATOR:
    REDIS_HOST: quay-redis-host
    REDIS_PASSWORD: quay-redis-password
    REDIS_SSL: true
    REDIS_SKIP_KEYSPACE_EVENT_SETUP: false
```

## Executors
The executors provides an interface to the control planes running the worker nodes.
Currently supported are Kubernetes and EC2.

In the case of Kubernetes, a `Job` resource is created on the cluster.
For EC2, a reservation is created for an instance.

When multiple executors are configured, the build manager will fallback to the next one in the list when the current one cannot be reached.

### Kubernetes
```
  EXECUTORS:
  - EXECUTOR: kubernetes
    NAME: openshift
    QUAY_USERNAME: quayusertopullworker
    QUAY_PASSWORD: quaypass
    WORKER_IMAGE: quay.io/quay/quay-builder
    WORKER_TAG: master
    SETUP_TIME: 180 # Time the instance has to start

    # Number of tries remaining the job needs to use this executor
    MINIMUM_RETRY_THRESHOLD: 1 

    # Container VM image (Kubernetes specific)
    BUILDER_VM_CONTAINER_IMAGE: quay.io/quay/quay-builder-qemu-fedoracoreos:stable
    
    # "basic" or "openshift"
    KUBERNETES_DISTRIBUTION: openshift

    # Kube apiserver
    #
    # Apiserver endpoint
    K8S_API_SERVER: api.openshift.somehost.org:6443
    #
    # Kube apiserver authentication
    # The following config options sets up authentication to the kube apiserver.
    # If both token auth AND client certs auth are set, token auth will be used.
    #
    # Bearer token authentication
    SERVICE_ACCOUNT_TOKEN: *****
    # Kubernetes API client certificates
    K8S_API_TLS_CERT: /path/to/cert.crt
    K8S_API_TLS_KEY: /path/to/server.key
    K8S_API_TLS_CA: /path/to/ca.crt

    # Namespace in which resources (jobs, pods, sa, ...) are located (assumes a default "builder" namespace)
    BUILDER_NAMESPACE: builder
    # Service account's name to attach to worker pods (assumes a default "quay-builder-sa" in the BUILDER_NAMESPACE, preferably with no permissions to any resources)
    SERVICE_ACCOUNT_NAME: quay-builder-sa

    # Node selector to target resource creation
    NODE_SELECTOR_LABEL_KEY: beta.kubernetes.io/instance-type # defaults to "beta.kubernetes.io/instance-type"
    NODE_SELECTOR_LABEL_VALUE: n1-standard-4 # defaults to ""

    # Kubernetes container resource options (default values below)
    CONTAINER_MEMORY_LIMITS: 5120Mi
    CONTAINER_CPU_LIMITS: 1000m
    CONTAINER_MEMORY_REQUEST: 3968Mi
    CONTAINER_CPU_REQUEST: 500m
    VOLUME_SIZE: 32G
```

#### Trusting a Kubernetes cluster using a self signed certificate
If the `kube-apiserver` is setup with a self signed certificate, Quay will need to add it to its extra certificates, otherwise a verification error will occur whenever the build manager tries to make an api call to the kube api.
The `kube-apiserver` certificate can usually be obtained from the `kube-apiserver`'s `service account` (if not, the cluster's administrator):
- In the `kube-apiserver`'s `service account token`, import the `ca.crt` (or equivalent) to Quay using Quay's the config tool (recommended).
- Alernatively, the certificate's path could be specified by the `K8S_API_TLS_CA` key in the app config.

#### Client Certificate verification
If client certificate authentication is required, the TLS cert, TLS key and TLS CA can be specified by `K8S_API_TLS_CERT`, `K8S_API_TLS_KEY` and `K8S_API_TLS_CA`, respectively.
  
### EC2
```
  EXECUTORS:
  - EXECUTOR: ec2
    QUAY_USERNAME: quayusertopullworker
    QUAY_PASSWORD: quaypass
    WORKER_IMAGE: quay.io/quay/quay-builder
    WORKER_TAG: master
    SETUP_TIME: 180 # Time the instance has to start

    # Number of tries remaining the job needs to use this executor
    MINIMUM_RETRY_THRESHOLD: 1 
    
    # AWS specific options
    EC2_REGION: us-east-1
    COREOS_AMI: ami-02545325b519192df # Fedora CoreOS
    AWS_ACCESS_KEY: *****
    AWS_SECRET_KEY: *****
    EC2_INSTANCE_TYPE: t2.large
    EC2_VPC_SUBNET_ID: subnet-somesubnet
    EC2_SECURITY_GROUP_IDS:
    - sg-somesg
    EC2_KEY_NAME: Some key
    BLOCK_DEVICE_SIZE: 58
```
