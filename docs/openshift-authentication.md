# OpenShift Authentication #

OpenShift Integrated Authentication lets you re-use your sign on to OpenShift to log in to Quay.

In this way, it guarantees a one-to-one relationship between users provisioned in your OpenShift cluster, and
users that are able to access quay. This means that the end user does not need to develop a user provisioning
strategy, other than deploying Quay manually or via the Operator.

## Pre-requisites ##

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

