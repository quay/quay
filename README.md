# Project Quay

![CI](https://github.com/quay/quay/workflows/CI/badge.svg?branch=master)
[![Container Repository on Quay](https://quay.io/repository/projectquay/quay/status "Container Repository on Quay")](https://quay.io/repository/projectquay/quay)

:warning: The `master` branch may be in an *unstable or even broken state* during development.
Please use [releases] instead of the `master` branch in order to get stable software.

[releases]: https://github.com/quay/quay/releases

![Project Quay Logo](project_quay_logo.png)

Project Quay builds, stores, and distributes your container images.

High-level features include:

- Docker Registry Protocol [v2]
- Docker Manifest Schema [v2.1], [v2.2]
- OCI spec v1.1 support [oci]
- Authentication provided by [LDAP], [Keystone], [OIDC], [Google], and [GitHub]
- ACLs, team management, and auditability logs
- Geo-replicated storage provided by local filesystems, [S3], [GCS], [Swift], [Ceph] and [ODF]
- Continuous Integration integrated with [GitHub], [Bitbucket], [GitLab], and [git]
- Security Vulnerability Analysis via [Clair]
- [Swagger]-compliant HTTP API

[v2]: https://docs.docker.com/registry/spec/api/
[v2.1]: https://github.com/docker/distribution/blob/master/docs/spec/manifest-v2-1.md
[v2.2]: https://github.com/docker/distribution/blob/master/docs/spec/manifest-v2-2.md
[oci]: https://github.com/opencontainers/distribution-spec/tree/v1.1.0-rc1?tab=readme-ov-file#oci-distribution-specification
[LDAP]: https://en.wikipedia.org/wiki/Lightweight_Directory_Access_Protocol
[Keystone]: http://docs.openstack.org/developer/keystone
[OIDC]: https://en.wikipedia.org/wiki/OpenID_Connect
[Google]: https://developers.google.com/identity/sign-in/web/sign-in
[GitHub]: https://developer.github.com/v3/oauth
[S3]: https://aws.amazon.com/s3
[GCS]: https://cloud.google.com/storage
[Swift]: http://swift.openstack.org
[Ceph]: http://docs.ceph.com/docs/master/radosgw/config
[ODF]: https://www.redhat.com/en/technologies/cloud-computing/openshift-data-foundation
[GitHub]: https://github.com
[Bitbucket]: https://bitbucket.com
[GitLab]: https://gitlab.com
[git]: https://git-scm.com
[Clair]: https://github.com/quay/clair
[Swagger]: http://swagger.io

## Getting Started

* Explore a live instance of Project Quay hosted at [Quay.io]
* Watch [talks] given about Project Quay
* Review the [documentation] for Red Hat Quay
* Get up and running with our [getting started] guide for developing or deploying Quay
* Deploy on Kubernetes using the [Quay Operator]

[Quay.io]: https://quay.io
[talks]: /docs/talks.md
[documentation]: https://access.redhat.com/documentation/en-us/red_hat_quay
[getting started]: /docs/getting-started.md
[Quay Operator]: https://github.com/quay/quay-operator

## Community

* Mailing List: [quay-sig@googlegroups.com]
* IRC: #quay on [libera.chat]
* Bug tracking: [Red Hat JIRA]
* Security Issues: [security@redhat.com]
* Community meetings held the first Wednesday of every month 11:00 AM EST: [meeting link](https://meet.google.com/rsj-atvk-zth)

[quay-sig@googlegroups.com]: https://groups.google.com/forum/#!forum/quay-sig
[libera.chat]: https://web.libera.chat/?channel=#quay
[Red Hat JIRA]: https://issues.redhat.com/projects/PROJQUAY
[security@redhat.com]: mailto:security@redhat.com

## License

Project Quay is under the Apache 2.0 license.
See the LICENSE file for details.
