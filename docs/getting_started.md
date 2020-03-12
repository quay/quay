# Getting Started With Quay

This guide is meant to show how to get Quay up and running with a minimum of external dependencies for testing or evaluation.  It aims to illustrate the components of a Quay installation to understand how the pieces fit together.  Please don't use this configuration for production or a highly available Quay installation.

NOTE: This guide uses [podman](https://podman.io/) which assumes a Linux environment- on MacOS or Windows you should be able to substitute with `docker` without trouble.

As a starting point, create or locate a directory where you want to store Quay's configuration and image blobs- we will refer to this as $QUAY going forward.

## Add 'quay' to your /etc/hosts mapping to localhost

This step isn't strictly required but makes things go a bit smoother in the ConfigTool steps.

```
$ cat /etc/hosts
...
127.0.0.1   quay
```

## Set Up Postgres

Quay will need a database to hold its image metadata (we will store images themselves on local disk in this tutorial).  Postgres is the recommended database, especially for highly available configurations.  Below we are pulling Red Hat's Postgres image but you should be able to use an image from other sources 

```
$ mkdir -p $QUAY/postgres
$ setfacl -m u:26:-wx $QUAY/postgres
$ sudo podman run -d --rm --name postgresql \
	-e POSTGRES_USER=user \
	-e POSTGRES_PASSWORD=pass \
	-e POSTGRES_DB=quay \
	-p 5432:5432 \
	-v $QUAY/postgres:/var/lib/postgresql/data:Z \
	postgres:10.12
```
Quay needs the `pg_trgm` module installed, so we can do so as follows:

```
$ sudo podman exec -it postgresql /bin/bash -c 'echo "CREATE EXTENSION IF NOT EXISTS pg_trgm" | psql -d quay -U user'
CREATE EXTENSION
```
Let's also grab the IP address of our Postgres container so we can refer to it later:
```
$ sudo podman inspect -f "{{.NetworkSettings.IPAddress}}" postgresql
10.88.0.13
```

## Set Up Redis

Quay also requires a Redis runtime to hold user events and if configured, build coordination and build logs.  This instance can be ephemeral as it doesn't hold any data we can't live without.  We should also get the redis IP address at this time:

```
$ sudo podman run -d --rm --name redis \
        -p 6379:6379 \
        redis:5.0.7 \
        --requirepass strongpassword

$ sudo podman inspect -f "{{.NetworkSettings.IPAddress}}" redis
10.88.0.14
```



## Build the Quay Configuration via ConfigTool. 

The ConfigTool resides on the Quay image and lets you generate Quay configuration files and set up your Postgres database.  It is a web application that guides you through the Quay configuration process.  The Quay configuration is a tar/zipped YAML file that you can save locally for Quay to read at startup time.

We run the Quay image with runtime flags set to launch ConfigTool accepting the password 'secret':

```
$ sudo podman run --rm -it --name quay_config -p 8443:8443 quay.io/projectquay/quay config secret
```

1. Open https://localhost:8443 in browser
1. Log in with quayconfig/secret
1. Start New Registry Setup

### Database Setup

1. Choose Postgres database type...
1. host: (enter the postgres IP address you obtained previously)
1. user: `user`
1. password: `pass`
1. database: `quay`

Hit `Validate Database Settings`.  This will begin setting up your database automatically.

On the next screen, set up a Quay super user account.  Click `Create Super User`.

On main config screen, you will have a few fields to fill out:

#### Server Configuration

1. For `Server Hostname` use `quay:8080` (or `localhost` however the UI will complain).  
1. For `TLS` choose `None (Not for Production)` - verify that you've included the port number in step above.

#### redis

1. For `Redis Hostname` enter the IP address for your Redis container obtained earlier.
2. For `Redis password` enter `strongpassword` or whatever you used when you launched the redis container.


Click on `Save Configuration Changes` at bottom of page.  Popup window should show settings confirmed.

On next screen, you will have the ability to download the Quay config.yaml as a gzipped tarball.  Click `Download Configuration`- we'll assume it goes into $DOWNLOADS.

Unpack the config so Quay can use it:

```
$ mkdir $QUAY/config
$ cp quay-config.tar.gz $QUAY/config
$ cd $QUAY/config
$ tar xvf quay-config.tar.gz

```

While we're here, let's set up a directory to hold image blobs:

```
$ mkdir $QUAY/storage
```

Stop the Config Tool with `CTRL-C` (or `podman stop` depending on how you ran it)- we won't need it anymore.

## Run Quay

With our config ready, database and redis running, all we need to do now is launch the Quay container again this time running the registry:

```
$ sudo podman run --rm -p 8080:8080 \
   --name=quay \
   --privileged=true \
   -v $QUAY/config:/conf/stack:Z \
   -v $QUAY/storage:/datastorage:Z \
   -d quay.io/projectquay/quay:latest
```

### Check the logs if necessary
```
$ podman logs -f quay
```

## Test out Quay

```
$ podman login --tls-verify=false quay:8080
Username: quay
Password: 
Login Succeeded!

$ podman pull busybox
Trying to pull docker.io/library/busybox...
Getting image source signatures
Copying blob 0669b0daf1fb done  
Copying config 83aa35aa1c done  
Writing manifest to image destination
Storing signatures
83aa35aa1c79e4b6957e018da6e322bfca92bf3b4696a211b42502543c242d6f
$ podman tag docker.io/library/busybox:latest quay:8080/quay/busybox:latest
$ podman push --tls-verify=false quay:8080/quay/busybox:latest
Getting image source signatures
Copying blob 195be5f8be1d done  
Copying config 6d5fcfe5ff done  
Writing manifest to image destination
Storing signatures

$ podman rmi quay:8080/quay/busybox:latest
$ podman pull --tls-verify=false quay:8080/quay/busybox:latest
Trying to pull quay:8080/quay/busybox:latest...
Getting image source signatures
Copying blob c23833bba716 [--------------------------------------] 0.0b / 0.0b
Copying config 6d5fcfe5ff done  
Writing manifest to image destination
Storing signatures
6d5fcfe5ff170471fcc3c8b47631d6d71202a1fd44cf3c147e50c8de21cf0648
```
Congratulations you have a local Quay instance running!  Of course this deployment is not production-grade since it is not using highly available storage or even TLS for its connections.  Please see the [Quay HA Docs](https://docs.projectquay.io/deploy_quay_ha.html) for details on how to deploy a production-grade storage/database configuration and the [Manage Quay Docs](https://docs.projectquay.io/manage_quay.html) for details on how to set up SSL/TLS.


## Getting Clair Running
 
coming soon

## Next Steps

Quay and Clair can also be run as services on a Kubernetes cluster.  This is becoming a more common deployment architecture and simplifies many of the operational aspects of running Quay and Clair.  Check out the [Quay on OpenShift Docs](https://docs.projectquay.io/deploy_quay_on_openshift.html#_appendix_a_project_quay_on_openshift_configuration_files) for more details on how set up Quay and Clair on OpenShift. 

## Troubleshooting

### I need to change my Quay configuration!  This can be done by uploading your config tarball back into the ConfigTool:
```
$ cd $QUAY/config
$ tar cvzf myconfig.tar.gz config.yaml
```
Run the ConfigTool and choose 'Modify Existing Config'.  You can upload the tarball, make changes and then re-download it.



### I'd like to see inside the Quay database!
```
$  podman exec -it postgresql /bin/bash
bash-4.4$ psql -d quay -U user
psql (10.6)
Type "help" for help.
```