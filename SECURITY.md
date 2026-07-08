# Reporting a Security Vulnerability or Incident

Please do not report security vulnerabilities or security incidents via public
channels such as GitHub Issues or Pull Requests. To ensure coordinated
disclosure, direct all security questions and vulnerability reports to:

- **Email**: secalert@redhat.com

Further details at https://access.redhat.com/security/team/contact

## Submission Guidelines

To help us triage and resolve the issue efficiently, please include the
following in your report:

- **Title**: A concise, descriptive summary of the issue.
- **Reporter Details**: Your name or handle and affiliation.
- **Technical Description**: Detailed information regarding the vulnerability.
- **Affected Versions**: The specific version(s) or range(s) of software tested.
- **Reproduction Steps**: A minimal, functional example to reproduce the issue.
- **Impact Assessment**: Potential exploit scenarios and perceived severity (optional).
- **Suggested Fix**: Any proposed patches or mitigations (optional).
- **Disclosure Status**: Whether this has been shared with other parties or published, and your plan for future sharing (e.g., at a conference).

## Response Timeline

We aim to provide an initial acknowledgement of your report within 10 business
days. All confirmed security vulnerabilities and incidents will be addressed
according to severity level and impact on the project.

## Remediation Process

### Fix Development

1. Embargoed fixes are developed in **private branches** or forks to prevent premature disclosure.
2. All security patches undergo **peer review** by at least one other maintainer with relevant domain knowledge.
3. Patches are tested against the **reproduction steps** from the original report and validated against **regression test suites**.

### Release and Distribution

1. Security fixes are distributed through the project's **normal release channels** (container images, operator).
2. Release notes must reference the associated CVE ID(s) and advisory.

## Coordinated Vulnerability Disclosure

### Disclosure Model

The Project Quay project follows a **Coordinated Vulnerability Disclosure (CVD)** model aligned with OpenSSF guidance:

1. **Embargo Period:** Vulnerability details remain confidential until a fix is available and released.
2. **Disclosure Timing:** Public disclosure occurs simultaneously with or immediately after the availability of a patched release.
3. **Pre-notification:** For Critical severity issues affecting widely-deployed components, the Security Team may provide advance notice to major downstream users under embargo, up to 7 days before public disclosure.

## Supported Versions

We regularly perform patch releases for at least two most recent minor versions,
which contain fixes for relevant security vulnerabilities and important bugs.
Prior releases might receive critical security fixes on a best-effort basis.
However, we cannot guarantee that security fixes will be back-ported to older
unsupported versions.

As the open source steward for this project, Red Hat aligns upstream maintenance
with its downstream
[Red Hat Quay Life Cycle Policy](https://access.redhat.com/support/policy/updates/rhquay).

# Secure Development Practices

We follow established industry best practices for secure development incl. but not limited to

- Secured version control of source code
- Mandatory peer reviews
- Build-time vulnerability scanning (e.g., CodeQL, Clair)
- Automatic update of 3rd-party dependencies (e.g., Dependabot, Renovate)
- Automatic end-to-end testing of security-relevant features (e.g., authentication, authorization)

# EU Cyber Resilience Act — Open Source Steward Statement

This project is stewarded by **Red Hat, Inc.**, an open source software steward
as defined in Article 3(14) of the
[EU Cyber Resilience Act (Regulation 2024/2847)](https://eur-lex.europa.eu/eli/reg/2024/2847/oj/eng).
Contact: cra-steward@redhat.com

Refer to [Red Hat's security practices and vulnerability management policy](https://access.redhat.com/security/)
for detailed information.
