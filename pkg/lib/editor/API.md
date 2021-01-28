# Quay Automated Deployment

This guide will walk you through a Quay deployment through the exposed API. This can be used for automated deployments and reconfigurations.

## Quay Install

First, you must download the Quay image. This can be pulled from quay.io.

```bash
$ docker pull quay.io/projectquay/quay:latest
```

Now that we have a Quay image, we can start building a configuration. This can be done through the config-tool API. If a config bundle isn't mounted, the config-tool will boot into a setup session. This will allow us to create a new config bundle from scratch. To start the config-tool from the Quay container, run the following command:

```bash
$ docker run -p 8080:8080 quay.io/projectquay/quay:latest config secret
```

This will start a config-tool session with the credentials `username: quayconfig, password: secret`

## Using the config-tool API

There are 4 endpoints exposed in the config-tool API that can be used to build, validate, bundle, and deploy a configuration. Since the config-tool was loaded in a setup session, hitting the following endpoint will return a base config. The base config.yaml will contain default values and can later be changed with custom configurations.

### GET - Get Mounted (or default) Config Bundle

```bash
$ curl -u quayconfig:secret localhost:8080/api/v1/config | jq

  % Total    % Received % Xferd  Average Speed   Time    Time     Time  Current
                                 Dload  Upload   Total   Spent    Left  Speed
100  1885  100  1885    0     0   368k      0 --:--:-- --:--:-- --:--:--  368k
{
  "config.yaml": {
    "AUTHENTICATION_TYPE": "Database",
    "AVATAR_KIND": "local",
    "DB_CONNECTION_ARGS": {
      "autorollback": true,
      "threadlocals": true
    },
    "DEFAULT_TAG_EXPIRATION": "2w",
    "EXTERNAL_TLS_TERMINATION": false,
    "FEATURE_ACTION_LOG_ROTATION": false,
    "FEATURE_BITBUCKET_BUILD": false,
    ...
    ...
    "TAG_EXPIRATION_OPTIONS": [
      "0s",
      "1d",
      "1w",
      "2w",
      "4w"
    ],
    "TEAM_RESYNC_STALE_TIME": "30m",
    "USER_RECOVERY_TOKEN_LIFETIME": "30m"
  }
}

```

### POST - Validate Config Bundle

```bash
$ curl --header "Content-Type: application/json" --request POST --data '{
  "config.yaml": {
    "AUTHENTICATION_TYPE": "Database",
    "AVATAR_KIND": "local",
    "DB_CONNECTION_ARGS": {
      "autorollback": true,
      "threadlocals": true
    },
    "DEFAULT_TAG_EXPIRATION": "2w",
    "EXTERNAL_TLS_TERMINATION": false,
    "FEATURE_ACTION_LOG_ROTATION": false,
    "FEATURE_BITBUCKET_BUILD": false,
    ...
    ...
    "TAG_EXPIRATION_OPTIONS": [
      "0s",
      "1d",
      "1w",
      "2w",
      "4w"
    ],
    "TEAM_RESYNC_STALE_TIME": "30m",
    "USER_RECOVERY_TOKEN_LIFETIME": "30m"
  }
}' -u quayconfig:password localhost:8080/api/v1/config/validate | jq

% Total    % Received % Xferd  Average Speed   Time    Time     Time  Current
                                 Dload  Upload   Total   Spent    Left  Speed
100  2827  100   531  100  2296   103k   448k --:--:-- --:--:-- --:--:--  552k
[
  {
    "FieldGroup": "Redis",
    "Tags": [
      "BUILDLOGS_REDIS"
    ],
    "Message": "BUILDLOGS_REDIS is required"
  },
  {
    "FieldGroup": "Database",
    "Tags": [
      "DB_URI"
    ],
    "Message": "DB_URI is required."
  },
  {
    "FieldGroup": "DistributedStorage",
    "Tags": [
      "DISTRIBUTED_STORAGE_CONFIG"
    ],
    "Message": "DISTRIBUTED_STORAGE_CONFIG must contain at least one storage location."
  },
  {
    "FieldGroup": "HostSettings",
    "Tags": [
      "SERVER_HOSTNAME"
    ],
    "Message": "SERVER_HOSTNAME is required"
  },
  {
    "FieldGroup": "HostSettings",
    "Tags": [
      "SERVER_HOSTNAME"
    ],
    "Message": "SERVER_HOSTNAME must be of type Hostname"
  }
]
```

Notice that this endpoint returns any validation errors that exist in the config. Here, we see that our base config was still missing a few required fields. When a configuration is fully validated, this endpoint will return an empty list. Once a config bundle has been successfully validated, we can use a third endpoint to bundle our config into a tar.gz.

## Create/Add Super Users

In order to add a super user to Quay, the username must be included in the `SUPER_USERS` field in the `config.yaml`. This can be done using the instructions in the previous step. Once the username has been set as a super user, the user can be created inside of Quay. This can be done through the Quay API. To create a user, start the Quay container in registry mode and run the following command:

```bash
$ curl --header "Content-Type: application/json" --request POST --data '{
 "username": <your_username>,
 "password": <your_password>
 }' localhost:8080/v1/superuser/users

```

This command will create a user in the database.
