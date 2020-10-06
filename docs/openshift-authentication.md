# OpenShift Authentication #

OpenShift Integrated Authentication lets you re-use your sign on to OpenShift to log in to Quay.

In this way, it guarantees a one-to-one relationship between users provisioned in your OpenShift cluster, and
users that are able to access quay. This means that the end user does not need to develop a user provisioning
strategy, other than deploying Quay manually or via the Operator.

As the OpenShift OAuth service does not return any user information, we rely on the OpenShift API to get information 
about the logged/logging-in user. This information does *NOT* include an e-mail address. If you are relying on e-mail
functionality from Quay, the integrated users cannot receive E-mail without adding an e-mail address after the account
has been provisioned.

## Quay ON OpenShift ##

### Pre-requisites ###

To allow Quay to be a client of the OpenShift internal OAuth service, you must first create an OAuth client
configuration. This can be done by creating a Service Account with a special annotation. This can also be done
with an `OAuth` resource, but this is generally less secure.

### Creating an OAuth Client ###
 
For this guide, we will run through a brief tour of the steps to create the OAuth Service Account. 

If you have questions about any of the details, please consult the official 
OpenShift Container Platform Documentation,
[Using a service account as an OAuth client](https://docs.openshift.com/container-platform/latest/authentication/using-service-accounts-as-oauth-client.html)

In this example, we will be using a Service Account called `quay-oauth`.

*Example Manifest*

```yaml
apiVersion: v1
kind: ServiceAccount
metadata:
  name: quay-oauth
  annotations:
    serviceaccounts.openshift.io/oauth-redirecturi.quay: "https://quayecosystem-quay-quay-enterprise.apps.<clusterid>.<domain>/oauth2/openshift/callback"
```

*NOTE*: the OAuth Redirect URI will depend on the Route that you created for Quay, so the URL above may not be the same
as your cluster. If you can log in to Quay already, it will be this hostname with the `/oauth2/openshift/callback` path
appended.

Once the Service Account is created, the OAuth Client ID is determined using a combination of the service account name
and the namespace that it resides in, for example, if the `quay-oauth` service account is created in the namespace
`quay-enterprise`, the OAuth Client ID would be:

```
system:serviceaccount:quay-enterprise:quay-oauth
```

The Client Secret can be any one of the API tokens that were generated for the account. In openshift, these are
secrets that are prefixed with the name of the service account. Additionally you can retrieve one using the `oc`
command:

```
$ oc sa get-token quay-oauth
```

Note that you do not need to modify the cluster `OAuth` resource to support this configuration.

### Troubleshooting ###

#### invalid_request: The request is missing a required parameter, includes an invalid parameter value, ... ####

This may be because Quay is asking for a different redirect URL to the one you annotated the *ServiceAccount* with.

Have a look at the `redirect_uri` parameter in the URL to figure out what Quay is asking for, and compare it against
the annotation.

You can get more information about failed OAuth attempts from the Pods in the `openshift-authentication` namespace.

Keep in mind these configuration variables affect the `redirect_uri`:

- `PREFERRED_URL_SCHEME`
- `SERVER_HOSTNAME`

If you are using a different kind of TLS termination like Edge or Re-Encrypt, you will probably need to modify these 
to reflect the publicly accessible URL of the Quay application.

## Quay WITH OpenShift ##

You can still use an OpenShift OAuth service from an externally hosted Project Quay instance.

The only difference with the externally hosted instance, is that you need to provide a URL to the API of the OpenShift
cluster that you are connecting to, as the Quay application cannot discover this automatically from outside the cluster.

In addition to the Client ID and Client Secret, you will have to provide an `OPENSHIFT_API_URL` setting, which
will be in the following format:

```yaml
OPENSHIFT_LOGIN_CONFIG:
  ... other settings ...
  OPENSHIFT_API_URL: "https://api.<clusterid>.<domain>:6443/"
```

## Configuration using the Quay Config App ##

To help you manage OpenShift integrated authentication, the Quay Config application includes most of the settings
mentioned in this document.

You can enable the OpenShift provider exactly as you would with the Google or GitHub authentication types.



### Configuration Reference ###

OpenShift Integrated OAuth adds the following configuration items:

```yaml
# Enable OpenShift Integrated Login
FEATURE_OPENSHIFT_LOGIN: true

OPENSHIFT_LOGIN_CONFIG:
  # Show debug logs
  DEBUGGING: true

  # If you aren't hosting Quay on the cluster you are authenticating to, you can specify an external cluster
  OPENSHIFT_API_URL: "https://api.<clusterid>.<domain>:6443/"

  CLIENT_ID: "system:serviceaccount:quay-enterprise:quay-oauth"
  CLIENT_SECRET: "ABCDEF...."

# Custom Query Parameters sent to the OpenShift OAuth Service
OPENSHIFT_ENDPOINT_CUSTOM_PARAMS: ""
```
