# Project Quay Governance

Project Quay is run according to the guidelines specified below.  This is a living document and is expected to evolve along with Project Quay itself.

## Principles

Project Quay strives to follow these principles at all times:
* Openness - Quay evolves and improves out in the open, with transparent work and decision making that is clear and well understood.
* Respectfulness - Quay is a project for a diverse community where different points of view are welcomed. Healthy and respectful discussions help us meet our goals and deliver a better end product.
* Meritocracy - In the Quay community all ideas are heard but only the best ideas help drive the project forward.  As an open, respectful community we will judge all ideas on their technical merit and alignment with Quay's design principles.
* Accountability - The Quay community is accountable
  * to our users to deliver the best software possible
  * to the project to ensure each Contributor and Maintainer carries out their duties to the best of their abilities
  * to itself to ensure the Quay remains a project where indviduals can be passionate about contributing their time and energy

## Maintainers

Maintainers play a special role to ensure that contributions align with the expected quality, consistency and long term vision for Project Quay.   Each Maintainer is vital to the success of Project Quay and has decided to make the commitment to that cause.  Being a Maintainer is difficult work and not for everyone.  Therefore Project Quay will have a small group of Maintainers- as many as deemed necessary to handle the pipeline of contributions being made to the project.

### Becoming a Maintainer

Each Maintainer must also be a Contributor.  Candidates for the Maintainer role are individuals who have made recent, substantial and recurring contributions to the project.  The existing Maintainers will periodically identify Contributors and make recommendations to the community that those individuals become Maintainers.  The Maintainers will then vote on the candidate and if so agreed the candidate will be invited to raise a PR to add their name into the MAINTAINERS.md file.  Approval of that PR signals the Contributor is now a Maintainer.

### Responsibilities of a Maintainer

Project Quay's success depends on how well Maintainers perform their duties.  Maintainers are responsible to monitor Slack and e-mail lists, help triage issues on the Project Quay JIRA board, review PRs and ensure responses are being provided to Contributors, assist with regular Project Quay releases.  If Contributors are the lifeblood of an open source community, the Maintainers act as the heart, hands, eyes and ears, helping to keep the project moving and viable.

### Stepping Down as a Maintainer

A Maintainer may decide they are no longer interested in or able to carry out the role.  In such a situation the Maintainer should notify the other Maintainers of their intentions to step down and help identify a replacement from existing Contributors.  Ideally the outgoing Maintainer will ensure that any outstanding work has been transitioned to another Maintainer.  To carry out the actual removal the outgoing Maintainer raises a PR against MAINTAINERS.md file to remove their name.

## Contributors

Anyone can be a Contributor to Project Quay.  No special approval is required- simply go through our Getting Started guide, fork one of our repositories and submit a PR.  All types of conributions will be welcome, whether it is through bug reports via JIRA, code, or documentation. 

## Sub-Projects

Project Quay will be primarily focused on the delivery of Quay itself but also contains various sub-projects such as Clair and Quay-Builders. Each sub-project must have their own dedicated repositories containing a MAINTAINERS.md file.  Each sub-project will abide by this Governance model.

Requests for new sub-projects under Project Quay should be raised to the Maintainers.

## Code of Conduct

Project Quay abides by the [CNCF Code of Conduct](https://github.com/cncf/foundation/blob/master/code-of-conduct.md).

## How Decisons Are Made

Most of the decison making for Project Quay will happen through the regular PR approval process.  We stand by the notion that what exists in the Project Quay repositories are the end result of countless community-driven decisions.

When a more complex decision is required, for example a technical issue related to a PR, it is expected that involved parties will resolve the dispute in a respectful and efficent manner.  If the dispute cannot be resolved between the involved parties then the Maintainers will review the dispute and come to an agreement via majority vote amongst themselves.  All decision making should be tracked via a JIRA issue and performed transparently via the Project Quay communications channels.

## Project Quay Releases

On a regular basis, Project Quay will issue a release.  The release cadence will not be strictly defined but should happen approximately every 3 months.  Maintainers will be part of a rotating "Release Nanny" role whereby each Maintainer shares the responsibility of creating a Quay release.

Release duties include:
* Creating the Release Notes
* Verifying the automated tests have passed
* Building the necessary Quay, Clair-JWT, and Quay-Builder container images
* Publishing the container images to quay.io
* Updating the github release pages
* Notifying the community of the new release

## DCO and Licenses

Project Quay uses the [Apache 2.0](https://opensource.org/licenses/Apache-2.0) license.