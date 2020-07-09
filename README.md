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
- [AppC Image Discovery] via on-demand transcoding
- Image Squashing via on-demand transcoding
- Authentication provided by [LDAP], [Keystone], [OIDC], [Google], and [GitHub]
- ACLs, team management, and auditability logs
- Geo-replicated storage provided by local filesystems, [S3], [GCS], [Swift], and [Ceph]
- Continuous Integration integrated with [GitHub], [Bitbucket], [GitLab], and [git]
- Security Vulnerability Analysis via [Clair]
- [Swagger]-compliant HTTP API

[v2]: https://docs.docker.com/registry/spec/api/
[v2.1]: https://github.com/docker/distribution/blob/master/docs/spec/manifest-v2-1.md
[v2.2]: https://github.com/docker/distribution/blob/master/docs/spec/manifest-v2-2.md
[AppC Image Discovery]: https://github.com/appc/spec/blob/master/spec/discovery.md
[LDAP]: https://en.wikipedia.org/wiki/Lightweight_Directory_Access_Protocol
[Keystone]: http://docs.openstack.org/developer/keystone
[OIDC]: https://en.wikipedia.org/wiki/OpenID_Connect
[Google]: https://developers.google.com/identity/sign-in/web/sign-in
[GitHub]: https://developer.github.com/v3/oauth
[S3]: https://aws.amazon.com/s3
[GCS]: https://cloud.google.com/storage
[Swift]: http://swift.openstack.org
[Ceph]: http://docs.ceph.com/docs/master/radosgw/config
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
* Get up and running with a containerized [development environment]

[Quay.io]: https://quay.io
[talks]: /docs/talks.md
[documentation]: https://access.redhat.com/documentation/en-us/red_hat_quay
[development environment]: /docs/development-container.md

## Community

* Mailing List: [quay-sig@googlegroups.com]
* IRC: #quay on [freenode.net]
* Bug tracking: [JBoss JIRA]
* Security Issues: [security@redhat.com]

[quay-sig@googlegroups.com]: https://groups.google.com/forum/#!forum/quay-sig
[freenode.net]: https://webchat.freenode.net
[JBoss JIRA]: https://issues.jboss.org/projects/PROJQUAY
[security@redhat.com]: mailto:security@redhat.com

## Quay Bug Bash!

From July 13, 2020 through August 14, 2020, Project Quay is having a Bug Bash.  We have migrated Quay from python 2 to python 3 in our master branch.  This means nearly every line of code in Quay has been touched so our risk of regression bugs is high.  We need *your* help to help find them!

### How Do I Participate?

Just grab the Quay registry codebase (quay, quay-builder), checkout master branch, build a local copy and start testing!  If you find an issue, please raise a [JIRA] or (even better) raise [a pull request].  We are considering all community contributions against master during this time period as counting towards the Bug Bash.

[JIRA]: https://issues.redhat.com/projects/PROJQUAY/summary
[a pull request]: https://github.com/quay/quay/pulls

### What's in it for me?

Aside from the peace of mind that you've helped to make Quay a better code base, we're prepared to offer you some Project Quay swag- an official Project Quay t-shirt!

* Submit a pull request?  We'll send you a t-shirt.
* Find three (3) new bugs and submit JIRA tickets for each?  We'll send you a t-shirt.

In addition, we will be tracking community involvement on our [Bug Bash Leaderboard] so you can get the credit for your work.

[Bug Bash Leaderboard]: https://docs.google.com/spreadsheets/d/1NhMcaS49jUk0IElTnXYkvfLckjv3GKr9pQWf3ejYcf4/edit#gid=0

### Have a Question?

Check out our [Bug Bash FAQ].

[Bug Bash FAQ]: https://docs.google.com/document/d/1dGvTGDA3KGxOTUkql3w0NC7j_Cf_VeSUTXPxg6lxH5U/edit?ts=5f03355b

## License

Project Quay is under the Apache 2.0 license.
See the LICENSE file for details.
