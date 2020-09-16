# This file is a work-in-progress. Including notes and documentation for whomever
# takes it over.
# --------------------------------------------------------------------------------
# Docs:
# - https://packaging.python.org/tutorials/packaging-projects/
# - https://python-packaging.readthedocs.io/en/latest/dependencies.html

import setuptools


# Probably not the best "long description" but it's a starting point.
with open("README.md", "r") as f:
    long_description = f.read()


# Gather all dependencies pulled from github out of the requirements.txt file
with open("requirements.txt", "r") as f:
    git_dependencies = [
        dep.strip() for dep in f.read().split('/n')
        if "git+" in dep
        and not dep.startswith('#')  # Exclude comment lines
    ]


# Gather all other external dependencies from the requirements.txt file
with open("requirements.txt", "r") as f:
    external_dependencies = [
        dep.strip() for dep in f.read().split('/n')
        if "git+" not in dep
        and not dep.startswith('#')  # Exclude comment lines
    ]


setuptools.setup(
    name='quay',
    version="3.4.0-alpha.0",
    author="Red Hat, Inc.",  # TODO: Use correct author
    author_email="support@redhat.com",  # TODO: Use correct email address
    description="An enterprise-grade container registry",
    long_description=long_description,
    long_description_content_type="text/markdown",
    url="https://github.com/quay/quay",
    packages=setuptools.find_packages(),
    install_requires=external_dependencies,
    dependency_links=git_dependencies,
    classifiers=[
        "Development Status :: 3 - Alpha"
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: Implementation :: CPython",
        "Topic :: System :: Software Distribution",
        "License :: OSI Approved :: Apache Software License",
    ],
    python_requires='>=3.6',
)

