import os

from setuptools import setup

# File used to export Quay modules to be used in other projects.
# Current modules exported to support reuse of database models.
# Modules and dependencies are exported via whitelist - only the
# required modules are exported for efficiency.

# The only Quay dependencies that will be exported with package
packages = [
    "alembic",
    "Authlib",
    "bitmath",
    "boto3",
    "bcrypt",
    "botocore",
    "cachetools",
    "cryptography",
    "Deprecated",
    "elasticsearch",
    "Flask",
    "hashids",
    "jsonschema",
    "keystoneauth1",
    "peewee",
    "pymemcache",
    "PyYAML",
    "redis",
    "rehash",
    "six",
    "SQLAlchemy",
    "stripe",
    "tldextract",
    "toposort",
    "tzlocal",
    "beautifulsoup4",
    "bintrees",
    "geoip2",
    "gevent",
    "greenlet",
    "gunicorn",
    "Jinja2",
    "mixpanel",
    "netaddr",
    "psutil",
    "PyJWT",
    "pyOpenSSL",
    "raven",
    "requests",
    "Werkzeug",
    "xhtml2pdf",
]

# Pull dependency versions from requirements.txt
# Exclude dependencies built directly from source, none are required
quay_root = os.path.dirname(os.path.realpath(__file__))
requirementPath = quay_root + "/requirements.txt"
install_requires = []
if os.path.isfile(requirementPath):
    with open(requirementPath) as f:
        for line in f.read().splitlines():
            if not line.startswith("git") and line.split("==")[0] in packages:
                install_requires.append(line)

setup(
    name="quay",
    version="3.13",
    description="Quay Modules",
    author="Quay Team",
    author_email="",
    url="https://github.com/quay/quay",
    packages=[
        "features",
        "auth",
        "data",
        "data.cache",
        "data.logs_model",
        "data.logs_model.logs_producer",
        "data.model",
        "data.model.oci",
        "data.queue",
        "data.registry_model",
        "data.secscan_model",
        "util",
        "util.metrics",
        "util.migrate",
        "util.secscan",
        "util.secscan.v4",
        "util.security",
        "image",
        "image.docker",
        "image.oci",
        "image.docker.schema2",
        "image.shared",
        "digest",
        "oauth",
    ],
    install_requires=install_requires,
)
