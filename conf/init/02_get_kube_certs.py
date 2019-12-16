import json
import os
import base64

from requests import Request, Session

QUAYPATH = os.environ.get("QUAYPATH", ".")
KUBE_EXTRA_CA_CERTDIR = os.environ.get(
    "KUBE_EXTRA_CA_CERTDIR", "%s/conf/kube_extra_certs" % QUAYPATH
)

KUBERNETES_API_HOST = os.environ.get("KUBERNETES_SERVICE_HOST", "")
port = os.environ.get("KUBERNETES_SERVICE_PORT")
if port:
    KUBERNETES_API_HOST += ":" + port

SERVICE_ACCOUNT_TOKEN_PATH = "/var/run/secrets/kubernetes.io/serviceaccount/token"

QE_NAMESPACE = os.environ.get("QE_K8S_NAMESPACE", "quay-enterprise")
QE_CONFIG_SECRET = os.environ.get("QE_K8S_CONFIG_SECRET", "quay-enterprise-config-secret")
EXTRA_CA_DIRECTORY_PREFIX = "extra_ca_certs_"


def _lookup_secret(service_token):
    secret_url = "namespaces/%s/secrets/%s" % (QE_NAMESPACE, QE_CONFIG_SECRET)
    response = _execute_k8s_api(service_token, "GET", secret_url)
    if response.status_code != 200:
        raise Exception("Cannot get the config secret")
    return json.loads(response.text)


def _execute_k8s_api(
    service_account_token,
    method,
    relative_url,
    data=None,
    api_prefix="api/v1",
    content_type="application/json",
):
    headers = {"Authorization": "Bearer " + service_account_token}

    if data:
        headers["Content-Type"] = content_type

    data = json.dumps(data) if data else None
    session = Session()
    url = "https://%s/%s/%s" % (KUBERNETES_API_HOST, api_prefix, relative_url)

    request = Request(method, url, data=data, headers=headers)
    return session.send(request.prepare(), verify=False, timeout=2)


def is_extra_cert(key):
    return key.find(EXTRA_CA_DIRECTORY_PREFIX) == 0


def main():
    # Load the service account token from the local store.
    if not os.path.exists(SERVICE_ACCOUNT_TOKEN_PATH):
        raise Exception("Cannot load Kubernetes service account token")

    with open(SERVICE_ACCOUNT_TOKEN_PATH, "r") as f:
        service_token = f.read()

    secret_data = _lookup_secret(service_token).get("data", {})
    cert_keys = list(filter(is_extra_cert, list(secret_data.keys())))

    for cert_key in cert_keys:
        if not os.path.exists(KUBE_EXTRA_CA_CERTDIR):
            os.mkdir(KUBE_EXTRA_CA_CERTDIR)

        cert_value = base64.b64decode(secret_data[cert_key])
        cert_filename = cert_key.replace(EXTRA_CA_DIRECTORY_PREFIX, "")
        print("Found an extra cert %s in config-secret, copying to kube ca dir")

        with open(os.path.join(KUBE_EXTRA_CA_CERTDIR, cert_filename), "w") as f:
            f.write(cert_value)


if __name__ == "__main__":
    main()
