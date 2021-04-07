<a name="unreleased"></a>
## [Unreleased]

### Release
- [294d18a3](https://github.com/quay/quay/commit/294d18a393d2892386b040021a5d4db82be80125): ci/cd release update (PROJQUAY-1486)

<a name="v3.6.0-alpha.1"></a>
## [v3.6.0-alpha.1] - 2021-04-06
### Chore
- [635dd6a7](https://github.com/quay/quay/commit/635dd6a73a1d52e9de8690bc1e59277167f7da25): import missing logging.config module ([#706](https://github.com/quay/quay/issues/706))
 -  [#706](https://github.com/quay/quay/issues/706)### Deps
- [8d9fa22c](https://github.com/quay/quay/commit/8d9fa22c26e5202c1036cf1137de135f2255e7b9): Update boto2 to boto3 ([#479](https://github.com/quay/quay/issues/479))
 -  [#479](https://github.com/quay/quay/issues/479)### Fix
- [23b8a239](https://github.com/quay/quay/commit/23b8a23993fcc29d7c1d9440c4b4045366b80c99): Use Python 3.8 for CI tests ([#580](https://github.com/quay/quay/issues/580))
 -  [#580](https://github.com/quay/quay/issues/580)### Format
- [0722e6ee](https://github.com/quay/quay/commit/0722e6ee5e3ace5f88adbc69899b9fba6d9550e2): remove extra comma from s3 connect_kwargs ([#709](https://github.com/quay/quay/issues/709))
 -  [#709](https://github.com/quay/quay/issues/709)### Gc
- [3b94cda7](https://github.com/quay/quay/commit/3b94cda75180d1355046ed656490aa45f63ee479): fix GlobalLock ttl unit and increase gc workers lock timeout ([#712](https://github.com/quay/quay/issues/712))
 -  [#712](https://github.com/quay/quay/issues/712)### Local-Dev
- [113ccebb](https://github.com/quay/quay/commit/113ccebbbfea827e959630be312ef8347e7a7c48): implement local development environment ([#610](https://github.com/quay/quay/issues/610))
 -  [#610](https://github.com/quay/quay/issues/610)### Notifications
- [0a9487f8](https://github.com/quay/quay/commit/0a9487f8ac358b26aa12bb9851cb61c5786ac4dc): add incoming jwt verification ([#568](https://github.com/quay/quay/issues/568))
 -  [#568](https://github.com/quay/quay/issues/568)### PROJQUAY-963
- [d575f391](https://github.com/quay/quay/commit/d575f39136c89c154de8db01be1216dafadb4b20): Add package and vulnerability related metadata into secscan response ([#515](https://github.com/quay/quay/issues/515))
 -  [#515](https://github.com/quay/quay/issues/515)### Sec
- [b389f885](https://github.com/quay/quay/commit/b389f885cfe4e0cd5da18272da50d9b9fc8934fe): implement jwt signing to ClairV4 ([#554](https://github.com/quay/quay/issues/554))
 -  [#554](https://github.com/quay/quay/issues/554)### Secscan
- [311241af](https://github.com/quay/quay/commit/311241af09be60d0f5a1e844d5722d96aaf61395): allow basic auth on the secscan api endpoint when anonymous api resource is set. ([#608](https://github.com/quay/quay/issues/608))
 -  [#608](https://github.com/quay/quay/issues/608)### Storage
- [fd274682](https://github.com/quay/quay/commit/fd2746827a48100d5aba7316b20724d25104817e): fix us-east-2 S3 direct pull ([#714](https://github.com/quay/quay/issues/714))
 -  [#714](https://github.com/quay/quay/issues/714)- [e0d39fe9](https://github.com/quay/quay/commit/e0d39fe9f24c01c4a893066fb9c71477ea9d90e5): abort unfinished mpu when no bytes were written ([#705](https://github.com/quay/quay/issues/705))
 -  [#705](https://github.com/quay/quay/issues/705)### Tags
- [79faf5f3](https://github.com/quay/quay/commit/79faf5f3679b3ac416c13b70f9fd101d496a6eef): apply tag expiry to created tags pointing to existing manifest ([#690](https://github.com/quay/quay/issues/690))
 -  [#690](https://github.com/quay/quay/issues/690)### [PROJQUAY-1021] Task
- [bd7252c5](https://github.com/quay/quay/commit/bd7252c536bcf8c49cca167d7c4b433489d36044): Update "Black" to version 20.8b1
### [PROJQUAY-1190] Fix
- [9ccb3ea9](https://github.com/quay/quay/commit/9ccb3ea9b2f8e1aa0510e632c7897d2589314cda): Use Python3 strings for user-facing tokens ([#589](https://github.com/quay/quay/issues/589))
 -  [#589](https://github.com/quay/quay/issues/589)### [PROJQUAY-1191] Add
- [b3d4d8cc](https://github.com/quay/quay/commit/b3d4d8cc7669b7c42f9d4b31ac7094ca4cf566d2): log sent emails (debug) ([#594](https://github.com/quay/quay/issues/594))
 -  [#594](https://github.com/quay/quay/issues/594)### [PROJQUAY-822] Security
- [52b86ac9](https://github.com/quay/quay/commit/52b86ac9fdaed00bd30d95af685233a0c4b77c0a): Hide sensitive LDAP log data ([#562](https://github.com/quay/quay/issues/562))
 -  [#562](https://github.com/quay/quay/issues/562)### [PROJQUAY-879] Fix
- [4d0581e2](https://github.com/quay/quay/commit/4d0581e2d9b12b8c0a096d8243eba380d7c88e88): Schema migrations with MySQL and SSL ([#596](https://github.com/quay/quay/issues/596))
 -  [#596](https://github.com/quay/quay/issues/596)### NOTE

The correct solution would have GlobalLock should either renew
the lock until the caller is done, or signal that it is no longer
valid to the caller.


<a name="vader"></a>
## [vader] - 2020-09-10
### Chore
- [5845afd4](https://github.com/quay/quay/commit/5845afd4e032304319b1764e0589e93ae34e9364): use `--no-cache-dir` flag to `pip` in dockerfiles, to save space ([#529](https://github.com/quay/quay/issues/529))
 -  [#529](https://github.com/quay/quay/issues/529)### Fix
- [4672db1d](https://github.com/quay/quay/commit/4672db1df76874238baf134d04e74112ac9f630d): Missing storage argument and type error when calling file.write ([#514](https://github.com/quay/quay/issues/514))
 -  [#514](https://github.com/quay/quay/issues/514)### Json Loads Fix
- [0c65f88a](https://github.com/quay/quay/commit/0c65f88a0ec5e3b847f45c1fdc0e53365126c22a): given arg should be a str ([#527](https://github.com/quay/quay/issues/527))
 -  [#527](https://github.com/quay/quay/issues/527)### PROJQUAY-1020 Chore
- [f9249d8b](https://github.com/quay/quay/commit/f9249d8baaf4ead12a897443f72f9c8a455de4e7): Fix cdnjs download failure(403) by setting custom User-Agent req header ([#535](https://github.com/quay/quay/issues/535))
 -  [#535](https://github.com/quay/quay/issues/535)### [PROJQUAY-1035] Fix
- [fbf5efb1](https://github.com/quay/quay/commit/fbf5efb1ec9751655d70f7e30125459a65432cff): Convert gunicorn worker counts to int for comparisons. ([#542](https://github.com/quay/quay/issues/542))
 -  [#542](https://github.com/quay/quay/issues/542)### [PROJQUAY-833] Chore
- [3a0b5d3c](https://github.com/quay/quay/commit/3a0b5d3c48f724eb35d5630a7accc7daad7a2d66): Update Pillow to 7.2.0 ([#538](https://github.com/quay/quay/issues/538))
 -  [#538](https://github.com/quay/quay/issues/538)### NOTE

This change includes a database migration which will *lock* the
manifest table

* Change tag API to return the layers size from the manifest

* Remove unused code

* Add new config_media_type field to OCI types

* Fix secscan V2 test for us no longer writing temp images

* Remove unused uploading field

* Switch registry model to use synthetic legacy images

Legacy images are now (with exception of the V2 security model) read from the *manifest* and sythensized in memory. The legacy image IDs are generated realtime based on the hashids library. This change also further deprecates a bunch of our Image APIs, reducing them to only returning the image IDs, and emptying out the remaining metadata (to avoid the requirement of us loading the information for the manifest from storage).

This has been tested with our full clients test suite with success.

* Add a backfill worker for manifest layers compressed sizes

* Change image tracks into manifest tracks now that we no longer have
manifest-less tags

* Add back in the missing method

* Add missing joins to reduce extra queries

* Remove unnecessary join when looking up legacy images

* Remove extra hidden filter on tag queries

* Further DB improvements

* Delete all Verbs, as they were deprecated

* Add back missing parameter in manifest data type

* Fix join to return None for the robot if not defined on mirror config

* switch to using secscan_v4_model for all indexing and remove most of secscan_v2_model code

* Add a missing join

* Remove files accidentally re-added due to rebase

* Add back hashids lib

* Rebase fixes

* Fix broken test

* Remove unused GPG signer now that ACI conversion is removed

* Remove duplicated repomirrorworker

* Remove unused notification code for secscan. We'll re-add it once Clair
V4 security notifications are ready to go

* Fix formatting

* Stop writing Image rows when creating manifests

* Stop writing empty layer blobs for manifests

As these blobs are shared, we don't need to write ManifestBlob rows
for them

* Remove further unused code

* Add doc comment to _build_blob_map

* Add unit test for synthetic V1 IDs

* Remove unused import

* Add an invalid value test to synthetic ID decode tests

* Add manifest backfill worker back in

Seems to have been removed at some point

* Add a test for cached active tags

* Rename test_shared to not conflict with another same-named test file

Pytest doesn't like having two test modules with the same name

* Have manifestbackfillworker also copy over the config_media_type if present


<a name="solo"></a>
## [solo] - 2020-07-13
### Keystonev2
- [4c429687](https://github.com/quay/quay/commit/4c429687fe4a6c813e0d8092794037d0322bb8d3): populate user.name into UserInformation ([#440](https://github.com/quay/quay/issues/440))
 -  [#440](https://github.com/quay/quay/issues/440)
<a name="padme"></a>
## [padme] - 2020-05-01
### .Github/Actions
- [1cad9081](https://github.com/quay/quay/commit/1cad9081189a591bea209c7929af750dc64de49d): only run dependabot changes on PR ([#360](https://github.com/quay/quay/issues/360))
 -  [#360](https://github.com/quay/quay/issues/360)### Data.Secscan_model
- [26dcf458](https://github.com/quay/quay/commit/26dcf45802183bbf696d44b15b6ab5ff44768fcb): canonicalize before comparing
### Docker
- [95432674](https://github.com/quay/quay/commit/9543267442c716e862e65d5e68682b349e87d889): s/requirements-test/requirements-dev
### Init
- [c06ca373](https://github.com/quay/quay/commit/c06ca373229a7743570a917595c7912c6f23769a): github workflows
### Makefile
- [e529ef93](https://github.com/quay/quay/commit/e529ef934d53cb4aae35a3281cd812002acc6606): remove extraneous requirements-dev
### Pylint
- [2c239622](https://github.com/quay/quay/commit/2c239622308bc8f92be1a3d06051b6b9587b7e01): drop 2 space ident configuration
### Readme
- [40c68fd8](https://github.com/quay/quay/commit/40c68fd86ba0a4e9873dc5962e431d79a478f534): replace travis badge with github actions ([#359](https://github.com/quay/quay/issues/359))
 -  [#359](https://github.com/quay/quay/issues/359)### Requirements
- [b0d2efb8](https://github.com/quay/quay/commit/b0d2efb8753cd4f4f97f5a2224f01ff7c224e892): use tox-docker upstream
### Requirements-Dev
- [f425f81d](https://github.com/quay/quay/commit/f425f81d1fb64af21284e0741a44c55403f08020): temporarily drop pylint
### Tests
- [300309db](https://github.com/quay/quay/commit/300309dbc4c38d70d92702ce859583d5fe28c443): fix tox
### Tox
- [8bb05771](https://github.com/quay/quay/commit/8bb05771717ab7e5f8786b6c1c8fdff4660bbb17): out python version for sanity
- [b2eb7530](https://github.com/quay/quay/commit/b2eb7530730cab9e53deb6e4e28af6990551a37f): remove legacy test suite
- [73595761](https://github.com/quay/quay/commit/73595761e3b81a31a4f5b54f2e4ec697ab9aa30f): use tox-docker fork for manual ports
- [4f0209b3](https://github.com/quay/quay/commit/4f0209b318a65c8d0c77931305d449c0b507d9d9): use /bin/sh instead of python to export env
- [a496ba5e](https://github.com/quay/quay/commit/a496ba5e132502ed3d9e07e0aa8cef68cd2cb50a): container healthchecks
- [987f20a3](https://github.com/quay/quay/commit/987f20a31c0de65054b4896f819313551a5efe28): init tox-docker
### Util.Canonicaljson
- [5bf41f9a](https://github.com/quay/quay/commit/5bf41f9a8d1b2c4e2e3bb1598649b7644daf7d68): add a kwarg for list ordering
### Workflows
- [9ce9a671](https://github.com/quay/quay/commit/9ce9a6710598853f21945a56cab089b288938ad1): use tox from requirements
### Pull Requests
- Merge pull request [#304](https://github.com/quay/quay/issues/304) from jzelinskie/workflows


<a name="naboo"></a>
## [naboo] - 2020-04-16
### Quay-Entrypoint.Sh
- [2735d348](https://github.com/quay/quay/commit/2735d348acff0f7dc849f85f03b675725cd8cfd5): fix openssl commandline ([#264](https://github.com/quay/quay/issues/264))
 -  [#264](https://github.com/quay/quay/issues/264)
<a name="mustafar"></a>
## [mustafar] - 2020-03-09
### Quay-Entrypoint.Sh
- [091bbe3e](https://github.com/quay/quay/commit/091bbe3e89f4ed1267d0e91412042170b563201c): don't use scl shells ([#233](https://github.com/quay/quay/issues/233))
 -  [#233](https://github.com/quay/quay/issues/233)### Quay-Entypoint.Sh
- [f89b946c](https://github.com/quay/quay/commit/f89b946ceab7e0636be93927f78b736bd05aa930): fix config argument handling ([#231](https://github.com/quay/quay/issues/231))
 -  [#231](https://github.com/quay/quay/issues/231)### Verbs
- [351535fa](https://github.com/quay/quay/commit/351535fa1adabb687d802522dd89f3c6f03ad92e): time blueprint
### Pull Requests
- Merge pull request [#236](https://github.com/quay/quay/issues/236) from alecmerdler/fix-local-config-app
- Merge pull request [#232](https://github.com/quay/quay/issues/232) from josephschorr/joseph.schorr/PROJQUAY-268/github-params
- Merge pull request [#227](https://github.com/quay/quay/issues/227) from josephschorr/joseph.schorr/PROJQUAY-220/tag-history-future
- Merge pull request [#230](https://github.com/quay/quay/issues/230) from josephschorr/joseph.schorr/PROJQUAY-268/upgrade-github-lib
- Merge pull request [#28](https://github.com/quay/quay/issues/28) from sghosh151/master
- Merge pull request [#224](https://github.com/quay/quay/issues/224) from jzelinskie/route-buckets
- Merge pull request [#229](https://github.com/quay/quay/issues/229) from jzelinskie/verb-blueprint-metrics
- Merge pull request [#221](https://github.com/quay/quay/issues/221) from josephschorr/fix-v2-labels


<a name="lando"></a>
## lando - 2020-02-17
### Buildman
- [945e038f](https://github.com/quay/quay/commit/945e038f1476de857b1b7992e1ce60dc5ff76458): cast job_status to string for metric
### Conf
- [7687e16f](https://github.com/quay/quay/commit/7687e16fc1d9d38192d8903ac38c136e2b12d3e2): replace prometheus aggregator w/ pushgateway
### Conf/Init
- [2b3d4f7b](https://github.com/quay/quay/commit/2b3d4f7bf9e255195cbfbab4d57232ac2477a342): add validate supervisord config test
- [51bdb627](https://github.com/quay/quay/commit/51bdb627f9656bddf80bc1b3cf968d633676ee24): remove service directory
### Deploy
- [2d7c0e09](https://github.com/quay/quay/commit/2d7c0e09556fec063a27ebda7a9188a3d06dc58c): add prom service for OpenShift
### Deploy/Openshift
- [af868c46](https://github.com/quay/quay/commit/af868c46d0ed0a6d60181be87d056af72b18c0d8): template monitoring resources
### Dockerfile
- [6267085d](https://github.com/quay/quay/commit/6267085d10dd382c90fe46bea8bad2f1766d5ad5): add pushgateway to OSBS images
 -  [#22](https://github.com/quay/quay/issues/22)### Docs
- [f59ebb1e](https://github.com/quay/quay/commit/f59ebb1e488d49f76b385d28bf9feed740886caa): add basic prometheus doc
### Metrics
- [6137546f](https://github.com/quay/quay/commit/6137546f3c5743d872aed709f33e7f6018697ac9): s/endpoint/route
- [2e3424d6](https://github.com/quay/quay/commit/2e3424d62320243e9137dc8243009032bbed1b39): push/pull bytes metrics named consistent
- [e8a1f74e](https://github.com/quay/quay/commit/e8a1f74ed33b56f879bfb1a1c6d68ab54bf1bd4c): add debug logging for pushgateway
### Openshift
- [ba3d0bd6](https://github.com/quay/quay/commit/ba3d0bd636f1525387c8ed619196a0224b25aff9): use one template for all of quay
### PROJQUAY-138
- [c90cd5d0](https://github.com/quay/quay/commit/c90cd5d09e731746afcc2ef4f0bccbbcb3bf38a1): Enable proxy protocol for Quay application ELB
### PROJQUAY-181
- [56a3bc44](https://github.com/quay/quay/commit/56a3bc443f76a5228ee7296f0a60e99555d097e2): updated nginx to redirect http to https for quay.io
- [72dff0ef](https://github.com/quay/quay/commit/72dff0ef21e8317bd60f8ef5838f38c232fe91fa): redirect http to https for quay.io
### README
- [8058bc06](https://github.com/quay/quay/commit/8058bc06427339b342fc64eed55e93e5f957110f): pointing to the correct community list
- [1d1092e4](https://github.com/quay/quay/commit/1d1092e4b4d55c64000951fd9b5a30acd71bc612): link to JBoss JIRA for issue tracking
### README/Docs
- [bef15009](https://github.com/quay/quay/commit/bef1500978ab6c31e2f7f9eec9d134a48e4b12de): s/projectquay/quay in git URIs
### Scripts/Ci
- [43e2d2e5](https://github.com/quay/quay/commit/43e2d2e547915217ae2759e66b53b70183f73bfc): fix incorrect logs command usage
### Travis
- [27bc7bad](https://github.com/quay/quay/commit/27bc7bad254e65b5ec20e75db226c0efa63716c2): s/state/stage
### Travis CI: Sudo
- [dede6d30](https://github.com/quay/quay/commit/dede6d30de85f70408cdda670193560a8b77fe42): is fully deprecated in Travis
### Util/Metrics
- [1e8b15ef](https://github.com/quay/quay/commit/1e8b15ef0cae4fae65f81ce337ddf18ce1861ef0): use basename for processname
- [9755eb27](https://github.com/quay/quay/commit/9755eb27155f44d7c161087126883cfeabd91d2c): fix unqualified identifier
- [6a83a52c](https://github.com/quay/quay/commit/6a83a52cad496e57a8059ebbe70abf1bcd6de117): log groupkey and add more host data
- [2241d669](https://github.com/quay/quay/commit/2241d6693b6e0c8d2efa7acd62a5fb086819c028): add process based grouping key
- [5b3db536](https://github.com/quay/quay/commit/5b3db536ef37d4383beba0a572b7d22abe70e0f7): remove metricqueue abstraction
### Reverts
- Revert "Remove the active migration for encrypted tokens now that it is complete"
- Remove the active migration for encrypted tokens now that it is complete

### Pull Requests
- Merge pull request [#220](https://github.com/quay/quay/issues/220) from josephschorr/joseph.schorr/PROJQUAY-227/manifest-conversion
- Merge pull request [#228](https://github.com/quay/quay/issues/228) from josephschorr/fix-repo-gc-timeout
- Merge pull request [#226](https://github.com/quay/quay/issues/226) from josephschorr/joseph.schorr/PROJQUAY-289/repo-create-error
- Merge pull request [#180](https://github.com/quay/quay/issues/180) from alecmerdler/fix-docstrings
- Merge pull request [#215](https://github.com/quay/quay/issues/215) from josephschorr/joseph.schorr/PROJQUAY-239/repo-gc-timeout-fix
- Merge pull request [#134](https://github.com/quay/quay/issues/134) from josephschorr/joseph.schorr/QUAY-1747/better-tagging
- Merge pull request [#214](https://github.com/quay/quay/issues/214) from josephschorr/add-v22-namespace-blacklist
- Merge pull request [#212](https://github.com/quay/quay/issues/212) from josephschorr/extra-storage-verification
- Merge pull request [#213](https://github.com/quay/quay/issues/213) from josephschorr/secscan-v2-tests
- Merge pull request [#211](https://github.com/quay/quay/issues/211) from josephschorr/manifest-config-blob-fixes
- Merge pull request [#209](https://github.com/quay/quay/issues/209) from josephschorr/fix-secscan-model
- Merge pull request [#208](https://github.com/quay/quay/issues/208) from josephschorr/joseph.schorr/PROJQUAY-219/better-manifest-errors
- Merge pull request [#175](https://github.com/quay/quay/issues/175) from josephschorr/joseph.schorr/PROJQUAY-177/abstract-sec-api
- Merge pull request [#205](https://github.com/quay/quay/issues/205) from josephschorr/add-build-badge
- Merge pull request [#119](https://github.com/quay/quay/issues/119) from josephschorr/joseph.schorr/PROJQUAY-124/async-repo-delete
- Merge pull request [#202](https://github.com/quay/quay/issues/202) from josephschorr/fix-robot-backfill
- Merge pull request [#200](https://github.com/quay/quay/issues/200) from thomasmckay/66-cherry-pick-changelog
- Merge pull request [#199](https://github.com/quay/quay/issues/199) from quay/revert-187-revert-181-joseph.schorr/PROJQUAY-185/remove-enc-token
- Merge pull request [#168](https://github.com/quay/quay/issues/168) from josephschorr/joseph.schorr/PROJQUAY-178/label-fixes
- Merge pull request [#194](https://github.com/quay/quay/issues/194) from tparikh/fix-debug-param
- Merge pull request [#187](https://github.com/quay/quay/issues/187) from quay/revert-181-joseph.schorr/PROJQUAY-185/remove-enc-token
- Merge pull request [#189](https://github.com/quay/quay/issues/189) from tparikh/PROJQUAY-181-fix-formatting
- Merge pull request [#184](https://github.com/quay/quay/issues/184) from tparikh/PROJQUAY-181
- Merge pull request [#170](https://github.com/quay/quay/issues/170) from alecmerdler/duplicate-secscan-code
- Merge pull request [#181](https://github.com/quay/quay/issues/181) from josephschorr/joseph.schorr/PROJQUAY-185/remove-enc-token
- Merge pull request [#182](https://github.com/quay/quay/issues/182) from josephschorr/joseph.schorr/PROJQUAY-186/fix-bitbucket-trigger-creation
- Merge pull request [#174](https://github.com/quay/quay/issues/174) from tparikh/http-redirect
- Merge pull request [#172](https://github.com/quay/quay/issues/172) from kurtismullins/fix-broken-ci
- Merge pull request [#169](https://github.com/quay/quay/issues/169) from jzelinskie/prom-route
- Merge pull request [#165](https://github.com/quay/quay/issues/165) from cclauss/patch-3
- Merge pull request [#162](https://github.com/quay/quay/issues/162) from cclauss/patch-2
- Merge pull request [#161](https://github.com/quay/quay/issues/161) from jzelinskie/prom-docs
- Merge pull request [#163](https://github.com/quay/quay/issues/163) from josephschorr/joseph.schorr/PROJQUAY-170/appr-limits
- Merge pull request [#158](https://github.com/quay/quay/issues/158) from josephschorr/joseph.schjorr/PROJQUAY-168/fix-migration
- Merge pull request [#164](https://github.com/quay/quay/issues/164) from alecmerdler/PROJQUAY-171
- Merge pull request [#49](https://github.com/quay/quay/issues/49) from quay/dependabot/pip/ecdsa-0.13.3
- Merge pull request [#135](https://github.com/quay/quay/issues/135) from quay/dependabot/pip/waitress-1.4.2
- Merge pull request [#151](https://github.com/quay/quay/issues/151) from josephschorr/fix-notification-view
- Merge pull request [#150](https://github.com/quay/quay/issues/150) from thomasmckay/146-fix-osbs
- Merge pull request [#149](https://github.com/quay/quay/issues/149) from kurtismullins/fix-setuptools-in-dockerfile
- Merge pull request [#145](https://github.com/quay/quay/issues/145) from kurtismullins/QUAY-1748
- Merge pull request [#110](https://github.com/quay/quay/issues/110) from jzelinskie/consistent-metrics
- Merge pull request [#132](https://github.com/quay/quay/issues/132) from josephschorr/joseph.schorr/QUAY-2239/fix-log-lookup
- Merge pull request [#142](https://github.com/quay/quay/issues/142) from josephschorr/joseph.schorr/PROJQUAY-132/queuefile-timeout
- Merge pull request [#144](https://github.com/quay/quay/issues/144) from MrDevJay/master
- Merge pull request [#121](https://github.com/quay/quay/issues/121) from josephschorr/joseph.schorr/QUAY-2100/gitlab-500
- Merge pull request [#120](https://github.com/quay/quay/issues/120) from josephschorr/joseph.schorr/PROJQUAY-125/fix-migration-template
- Merge pull request [#133](https://github.com/quay/quay/issues/133) from josephschorr/joseph.schorr/PROJQUAY-129/label-links
- Merge pull request [#140](https://github.com/quay/quay/issues/140) from tparikh/elb-proxy-protocol
- Merge pull request [#109](https://github.com/quay/quay/issues/109) from josephschorr/joseph.schorr/QUAY-1322/custom-webhook-body
- Merge pull request [#127](https://github.com/quay/quay/issues/127) from josephschorr/joseph.schorr/QUAY-2111/created-datetime
- Merge pull request [#122](https://github.com/quay/quay/issues/122) from josephschorr/joseph.schorr/PROJQUAY-126/digest-500
- Merge pull request [#114](https://github.com/quay/quay/issues/114) from tparikh/projquay117
- Merge pull request [#108](https://github.com/quay/quay/issues/108) from josephschorr/joseph.schorr/QUAY-1312/fresh-login-fix
- Merge pull request [#96](https://github.com/quay/quay/issues/96) from alecmerdler/QUAY-2213
- Merge pull request [#107](https://github.com/quay/quay/issues/107) from jzelinskie/job-status-str
- Merge pull request [#105](https://github.com/quay/quay/issues/105) from tparikh/drop-extra-ca-certs-dir
- Merge pull request [#106](https://github.com/quay/quay/issues/106) from tparikh/find-symlinks-ca-certs
- Merge pull request [#104](https://github.com/quay/quay/issues/104) from tparikh/update-quay-extra-certs-path
- Merge pull request [#100](https://github.com/quay/quay/issues/100) from thomasmckay/92-black
- Merge pull request [#98](https://github.com/quay/quay/issues/98) from tparikh/projquay67-fix-port
- Merge pull request [#92](https://github.com/quay/quay/issues/92) from tparikh/projquay67
- Merge pull request [#95](https://github.com/quay/quay/issues/95) from jzelinskie/consolidate-openshift
- Merge pull request [#94](https://github.com/quay/quay/issues/94) from jzelinskie/monitoring-template
- Merge pull request [#89](https://github.com/quay/quay/issues/89) from jzelinskie/prom-port
- Merge pull request [#79](https://github.com/quay/quay/issues/79) from josephschorr/joseph.schorr/QUAY-2225/reencrypt-fields
- Merge pull request [#88](https://github.com/quay/quay/issues/88) from josephschorr/joseph.schorr/PROJQUAY-62/deprecation
- Merge pull request [#87](https://github.com/quay/quay/issues/87) from quay/logforward
- Merge pull request [#80](https://github.com/quay/quay/issues/80) from josephschorr/joseph.schorr/QUAY-2204/fix-et-phase-2
- Merge pull request [#84](https://github.com/quay/quay/issues/84) from josephschorr/joseph.schorr/PROJQUAY-63/fix-count-repo-actions
- Merge pull request [#76](https://github.com/quay/quay/issues/76) from thomasmckay/58-tech-preview
- Merge pull request [#77](https://github.com/quay/quay/issues/77) from thomasmckay/59-rhocs
- Merge pull request [#78](https://github.com/quay/quay/issues/78) from tparikh/mount-quay-extra-ca-certs
- Merge pull request [#71](https://github.com/quay/quay/issues/71) from alecmerdler/QUAY-2201
- Merge pull request [#68](https://github.com/quay/quay/issues/68) from alecmerdler/PROJQUAY-6-redux
- Merge pull request [#69](https://github.com/quay/quay/issues/69) from tparikh/add-metrics-port-clusterip-svc
- Merge pull request [#70](https://github.com/quay/quay/issues/70) from jzelinskie/basename-prom
- Merge pull request [#67](https://github.com/quay/quay/issues/67) from alecmerdler/QUAY-2213
- Merge pull request [#63](https://github.com/quay/quay/issues/63) from thomasmckay/53-mirror-token
- Merge pull request [#66](https://github.com/quay/quay/issues/66) from jzelinskie/qualified
- Merge pull request [#65](https://github.com/quay/quay/issues/65) from tparikh/projquay-39
- Merge pull request [#64](https://github.com/quay/quay/issues/64) from jzelinskie/prom-log-groupkey
- Merge pull request [#62](https://github.com/quay/quay/issues/62) from jzelinskie/prom-grouping
- Merge pull request [#58](https://github.com/quay/quay/issues/58) from alecmerdler/PROJQUAY-6
- Merge pull request [#60](https://github.com/quay/quay/issues/60) from jzelinskie/debug-pushgateway
- Merge pull request [#59](https://github.com/quay/quay/issues/59) from jzelinskie/prom-osbs
- Merge pull request [#22](https://github.com/quay/quay/issues/22) from jzelinskie/prometheus-redo
- Merge pull request [#54](https://github.com/quay/quay/issues/54) from alecmerdler/PROJQUAY-42
- Merge pull request [#51](https://github.com/quay/quay/issues/51) from josephschorr/break-et-phases
- Merge pull request [#50](https://github.com/quay/quay/issues/50) from thomasmckay/40-azure-versions
- Merge pull request [#34](https://github.com/quay/quay/issues/34) from alecmerdler/PROJQUAY-6
- Merge pull request [#48](https://github.com/quay/quay/issues/48) from josephschorr/joseph.schorr/PROJQUAY-37/out-of-bounds
- Merge pull request [#46](https://github.com/quay/quay/issues/46) from quay/joseph.schorr/PROJQUAY-35/fix-gitlab-deactivate
- Merge pull request [#47](https://github.com/quay/quay/issues/47) from thomasmckay/34-root-certs
- Merge pull request [#41](https://github.com/quay/quay/issues/41) from thomasmckay/black
- Merge pull request [#45](https://github.com/quay/quay/issues/45) from maorfr/post-deploy
- Merge pull request [#44](https://github.com/quay/quay/issues/44) from josephschorr/noop-fix
- Merge pull request [#42](https://github.com/quay/quay/issues/42) from josephschorr/fix-access-token-clear
- Merge pull request [#43](https://github.com/quay/quay/issues/43) from jzelinskie/ci-logs
- Merge pull request [#40](https://github.com/quay/quay/issues/40) from tparikh/rhel7-base-img-src
- Merge pull request [#33](https://github.com/quay/quay/issues/33) from thomasmckay/18-travis-branches
- Merge pull request [#35](https://github.com/quay/quay/issues/35) from vbatts/mailing-list
- Merge pull request [#39](https://github.com/quay/quay/issues/39) from tparikh/refactor-app-sre-scripts-2
- Merge pull request [#37](https://github.com/quay/quay/issues/37) from tparikh/quay-openshift-template-updates
- Merge pull request [#36](https://github.com/quay/quay/issues/36) from tparikh/quay-openshift-deployment-updates
- Merge pull request [#32](https://github.com/quay/quay/issues/32) from thomasmckay/20-non-root
- Merge pull request [#21](https://github.com/quay/quay/issues/21) from alecmerdler/opensearch
- Merge pull request [#25](https://github.com/quay/quay/issues/25) from thomasmckay/12-mirror-api
- Merge pull request [#26](https://github.com/quay/quay/issues/26) from tparikh/fix-openshift-deployment
- Merge pull request [#24](https://github.com/quay/quay/issues/24) from tparikh/quayio-osd-deployment
- Merge pull request [#20](https://github.com/quay/quay/issues/20) from josephschorr/fix-alembic-no-migration
- Merge pull request [#17](https://github.com/quay/quay/issues/17) from josephschorr/fix-encrypted-token-migration
- Merge pull request [#18](https://github.com/quay/quay/issues/18) from josephschorr/remove-email-viewer-tool
- Merge pull request [#16](https://github.com/quay/quay/issues/16) from tparikh/app-sre-pipeline-integration
- Merge pull request [#13](https://github.com/quay/quay/issues/13) from kbrwn/nginx-storage-proxy-header-fix
- Merge pull request [#14](https://github.com/quay/quay/issues/14) from danielhelfand/dtr_broken_link
- Merge pull request [#12](https://github.com/quay/quay/issues/12) from jzelinskie/jboss-jira
- Merge pull request [#11](https://github.com/quay/quay/issues/11) from alecmerdler/PROJQUAY-3
- Merge pull request [#1](https://github.com/quay/quay/issues/1) from quay/init


[Unreleased]: https://github.com/quay/quay/compare/v3.6.0-alpha.1...HEAD
[v3.6.0-alpha.1]: https://github.com/quay/quay/compare/vader...v3.6.0-alpha.1
[vader]: https://github.com/quay/quay/compare/solo...vader
[solo]: https://github.com/quay/quay/compare/padme...solo
[padme]: https://github.com/quay/quay/compare/naboo...padme
[naboo]: https://github.com/quay/quay/compare/mustafar...naboo
[mustafar]: https://github.com/quay/quay/compare/lando...mustafar
