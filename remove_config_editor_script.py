
import subprocess
import sys
def check_oc_command():
    try:
        subprocess.run(["oc", "version"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=True)
    except subprocess.CalledProcessError:
        print("oc command not found. Please make sure OpenShift CLI is installed and in your PATH.", file=sys.stderr)
        sys.exit(1)
def remove_object(object_type, object_name):
    print(f"Removing {object_type}: {object_name}")
    subprocess.run(["oc", "delete", object_type, object_name])
def main():
    check_oc_command()
    # Remove route
    route_name = subprocess.run(["oc", "get", "route"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True).stdout
    route_name = next((line.split()[0] for line in route_name.splitlines() if "quay-config-editor" in line), None)
    if route_name:
        remove_object("route", route_name)
    # Remove deployment
    deployment_name = subprocess.run(["oc", "get", "deployment"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True).stdout
    deployment_name = next((line.split()[0] for line in deployment_name.splitlines() if "quay-config-editor" in line), None)
    if deployment_name:
        remove_object("deployment", deployment_name)
    # Remove service
    service_name = subprocess.run(["oc", "get", "svc"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True).stdout
    service_name = next((line.split()[0] for line in service_name.splitlines() if "config-editor" in line), None)
    if service_name:
        remove_object("service", service_name)
    # Remove secret
    secret_name = subprocess.run(["oc", "get", "secret"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True).stdout
    secret_name = next((line.split()[0] for line in secret_name.splitlines() if "config-editor" in line), None)
    if secret_name:
        remove_object("secret", secret_name)
    # Remove pod
    pod_name = subprocess.run(["oc", "get", "pod"], stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True).stdout
    pod_name = next((line.split()[0] for line in pod_name.splitlines() if "quay-config-editor" in line), None)
    if pod_name:
        remove_object("pod", pod_name)
    print("Red Hat Quay config editor objects removal completed.")
if __name__ == "__main__":
    main()
