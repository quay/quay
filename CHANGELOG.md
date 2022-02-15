## Red Hat Quay Release Notes
(Red Hat Customer Portal)[https://access.redhat.com/documentation/en-us/red_hat_quay/3.5/html/red_hat_quay_release_notes/index]


<a name="3.6.3"></a>
## [3.6.3] - 2022-02-14
### Blobuploadcleanupworker
- [9adf8fb6](https://github.com/quay/quay/commit/9adf8fb6e21af5578f06612fff3b014b135fc5ad): Add cleanup for orphaned blobs (PROJQUAY-2313) ([#967](https://github.com/quay/quay/issues/967)) ([#1028](https://github.com/quay/quay/issues/1028))
 -  [#967](https://github.com/quay/quay/issues/967) -  [#1028](https://github.com/quay/quay/issues/1028)- [7a0cf329](https://github.com/quay/quay/commit/7a0cf32936ea6149f46951cbdc2d5a462d6ccdf8): Add BLOBUPLOAD_DELETION_DATE_THRESHOLD (PROJQUAY-2915) ([#1022](https://github.com/quay/quay/issues/1022)) ([#1023](https://github.com/quay/quay/issues/1023))
 -  [#1022](https://github.com/quay/quay/issues/1022) -  [#1023](https://github.com/quay/quay/issues/1023)### Build(Deps)
- [95395118](https://github.com/quay/quay/commit/953951183b3c1427376224f593a0c0a06feb47af): bump python-ldap from 3.2.0 to 3.4.0 ([#1042](https://github.com/quay/quay/issues/1042))
 -  [#1042](https://github.com/quay/quay/issues/1042)### Buildman
- [7ed876e6](https://github.com/quay/quay/commit/7ed876e660854636a0c8128d68a6b731c4bb99f5): allow use of public builder image (PROJQUAY-3179) ([#1104](https://github.com/quay/quay/issues/1104))
 -  [#1104](https://github.com/quay/quay/issues/1104)- [95af8585](https://github.com/quay/quay/commit/95af8585f365e7ade8c14ae52befc7a4c8806a09): fix kubernetes not returning correct running count (PROJQUAY-3169) ([#1102](https://github.com/quay/quay/issues/1102))
 -  [#1102](https://github.com/quay/quay/issues/1102)### Chore
- [bb127b5f](https://github.com/quay/quay/commit/bb127b5ffb471a44d73b64efa561654a5ed1d788): download aws ip ranges via github workflow ([#1064](https://github.com/quay/quay/issues/1064))
 -  [#1064](https://github.com/quay/quay/issues/1064)- [99269962](https://github.com/quay/quay/commit/99269962fade1cb854441848bbf642494c8ac91e): 3.6.2 changelog bump (PROJQUAY-2853)
### Fix
- [f0643064](https://github.com/quay/quay/commit/f0643064f44d406c4992cd379d2009d1b935a478): Resolves issue with local docker builds not starting ([#1114](https://github.com/quay/quay/issues/1114))
 -  [#1114](https://github.com/quay/quay/issues/1114) -  [#953](https://github.com/quay/quay/issues/953)### Gc
- [62b2550e](https://github.com/quay/quay/commit/62b2550ec1e3b804d57e7a65e1b3b60c8aa83874): remove orphaned storage on repository purge (PROJQUAY-2313) ([#1075](https://github.com/quay/quay/issues/1075))
 -  [#1075](https://github.com/quay/quay/issues/1075)### Imagemirror
- [4e782c01](https://github.com/quay/quay/commit/4e782c01fc4b9c63e7e1d1b5f1a6647b8ef90331): Add unsigned registries mirror option (PROJQUAY-3106) ([#1098](https://github.com/quay/quay/issues/1098))
 -  [#1098](https://github.com/quay/quay/issues/1098)### Requirements-Osbs.Txt
- [165a60b2](https://github.com/quay/quay/commit/165a60b28c3bcc140106e6cef7435c4e6a220b4a): remove ipython and related deps ([#1069](https://github.com/quay/quay/issues/1069)) ([#1100](https://github.com/quay/quay/issues/1100))
 -  [#1069](https://github.com/quay/quay/issues/1069) -  [#1100](https://github.com/quay/quay/issues/1100)### Storage
- [49386766](https://github.com/quay/quay/commit/4938676644e1fb5cd63329a51d8bb681c31b68d3): allow configuration of storage region for cloud storage (PROJQUAY-3082) ([#1096](https://github.com/quay/quay/issues/1096))
 -  [#1096](https://github.com/quay/quay/issues/1096)### Util/Ipresolver
- [832f6573](https://github.com/quay/quay/commit/832f6573f7bcb1f704c3463a7576cb6550114761): manually add aws-ip-ranges.json ([#1088](https://github.com/quay/quay/issues/1088))
 -  [#1088](https://github.com/quay/quay/issues/1088)### [Redhat-3.6] Teams
- [92c1400b](https://github.com/quay/quay/commit/92c1400b4a9b70cbca7cff775037a4e3d312e03a): admin team deletion (PROJQUAY-2080) ([#1097](https://github.com/quay/quay/issues/1097))
 -  [#1097](https://github.com/quay/quay/issues/1097) -  [#1095](https://github.com/quay/quay/issues/1095)
<a name="v3.6.2"></a>
## [v3.6.2] - 2021-12-02
### Api
- [6470248b](https://github.com/quay/quay/commit/6470248be1ca55ab3ea6f2a364bc02547976186d): /v1/user/initialize to create first user (PROJQUAY-1926) ([#771](https://github.com/quay/quay/issues/771))
 -  [#771](https://github.com/quay/quay/issues/771)### Backport
- [0520aa7c](https://github.com/quay/quay/commit/0520aa7c49032b37e99077932566aea0e3cc75ca): Quayio nvd data UI improvements  ([#957](https://github.com/quay/quay/issues/957))
 -  [#957](https://github.com/quay/quay/issues/957) -  [#937](https://github.com/quay/quay/issues/937)### Build
- [1ae91bcc](https://github.com/quay/quay/commit/1ae91bcc8ba95ae38cadf401ce55044da9aaec36): Add required setup.cfg for downstream build (PROJQUAY-2713) ([#946](https://github.com/quay/quay/issues/946)) ([#994](https://github.com/quay/quay/issues/994))
 -  [#946](https://github.com/quay/quay/issues/946) -  [#994](https://github.com/quay/quay/issues/994)- [4c09559c](https://github.com/quay/quay/commit/4c09559cee9b68493483c6c7b8486afde64c6702): add full python build dependencies (PROJQUAY-2216) ([#822](https://github.com/quay/quay/issues/822))
 -  [#822](https://github.com/quay/quay/issues/822)- [1d63cfa2](https://github.com/quay/quay/commit/1d63cfa255d32c9eece8041452f13d78daab6e1a): update package-lock.json (PROJQUAY-1749) ([#821](https://github.com/quay/quay/issues/821))
 -  [#821](https://github.com/quay/quay/issues/821)- [9c8e3f1f](https://github.com/quay/quay/commit/9c8e3f1f486840513a65197dccdb77585f42c815): remove unused node modules (PROJQUAY-1667) ([#805](https://github.com/quay/quay/issues/805))
 -  [#805](https://github.com/quay/quay/issues/805)- [62e3bd9c](https://github.com/quay/quay/commit/62e3bd9cc7ca743ac472e6ae7f8099ba28a91fd5): update python pillow version (PROJQUAY-1520) ([#809](https://github.com/quay/quay/issues/809))
 -  [#809](https://github.com/quay/quay/issues/809)- [653dc021](https://github.com/quay/quay/commit/653dc021fea6358f8a56c344ade4e775605df15d): update node url-parse to 1.4.3 (PROJQUAY-1749) ([#797](https://github.com/quay/quay/issues/797))
 -  [#797](https://github.com/quay/quay/issues/797)### Build(Deps)
- [98c008e6](https://github.com/quay/quay/commit/98c008e63fbb59f5c58da4f4c7bb96a74a4ff66e): bump pillow from 8.3.1 to 8.3.2 ([#882](https://github.com/quay/quay/issues/882)) ([#958](https://github.com/quay/quay/issues/958))
 -  [#882](https://github.com/quay/quay/issues/882) -  [#958](https://github.com/quay/quay/issues/958)- [c5488aa3](https://github.com/quay/quay/commit/c5488aa3b52cab1c9e1391e50e0e9732f464d780): bump ssri from 6.0.1 to 6.0.2 ([#818](https://github.com/quay/quay/issues/818))
 -  [#818](https://github.com/quay/quay/issues/818)- [3c355223](https://github.com/quay/quay/commit/3c355223f17833dc5c0a8d95c1db6556b3ef9b44): bump flask-cors from 3.0.8 to 3.0.9 ([#783](https://github.com/quay/quay/issues/783))
 -  [#783](https://github.com/quay/quay/issues/783)### Buildman
- [f5b9492a](https://github.com/quay/quay/commit/f5b9492ac62df7a9b3ee741fc7ef8aba36028b72): Add proxy variables to builds if they exist (PROJQUAY-2120) ([#834](https://github.com/quay/quay/issues/834))
 -  [#834](https://github.com/quay/quay/issues/834)- [bfb8602d](https://github.com/quay/quay/commit/bfb8602d5ae1b3eb56fe57a381a6939fb60f98be): fix vm image name in startup script (PROJQUAY-2120) ([#811](https://github.com/quay/quay/issues/811))
 -  [#811](https://github.com/quay/quay/issues/811)### Cache
- [3dde3646](https://github.com/quay/quay/commit/3dde364615ae3f2b839fb38b7e791805e4243c3c): py2 compatibility, kwargs after named args (PROJQUAY-2101) ([#859](https://github.com/quay/quay/issues/859))
 -  [#859](https://github.com/quay/quay/issues/859)- [cd6871c1](https://github.com/quay/quay/commit/cd6871c14f5e017d70d99664ccde89ccac9e4366): add support for redis cluster mode (PROJQUAY-2101) ([#810](https://github.com/quay/quay/issues/810))
 -  [#810](https://github.com/quay/quay/issues/810)### Chore
- [35e8109c](https://github.com/quay/quay/commit/35e8109c332fed45ace09615c56e27629e415561): v3.6.1 changelog bump (PROJQUAY-2728) ([#955](https://github.com/quay/quay/issues/955))
 -  [#955](https://github.com/quay/quay/issues/955)- [b016844a](https://github.com/quay/quay/commit/b016844a0ff4b78bc03722b52fcd93efef57e7ce): build and publish workflow (PROJQUAY-2556)
- [47a1fdd3](https://github.com/quay/quay/commit/47a1fdd38ecbaffb460ebb4c6d43da4c14986221): remove ui elements for account recovery mode (PROJQUAY-970) ([#853](https://github.com/quay/quay/issues/853))
 -  [#853](https://github.com/quay/quay/issues/853)- [7d7eb755](https://github.com/quay/quay/commit/7d7eb75557fdc58a6c40536ccc807522659bd0d9): return zope.interface to requirements-osbs.txt (PROJQUAY-1535) ([#854](https://github.com/quay/quay/issues/854))
 -  [#854](https://github.com/quay/quay/issues/854)- [0999baa2](https://github.com/quay/quay/commit/0999baa29e76ee7c3118af75bb06b7bd681b66de): fix rediscluster cache config key name (PROJQUAY-2101) ([#849](https://github.com/quay/quay/issues/849))
 -  [#849](https://github.com/quay/quay/issues/849)- [a839a78e](https://github.com/quay/quay/commit/a839a78eb52e612a3f99c573ce1a552c5bb5e7a0): allows Quay to run for account recoveries (PROJQUAY-970) ([#793](https://github.com/quay/quay/issues/793))
 -  [#793](https://github.com/quay/quay/issues/793)- [4880c776](https://github.com/quay/quay/commit/4880c776e264e3fbf553418eff6656c68e5f60f2): remove node modules from final container (PROJQUAY-1822) ([#788](https://github.com/quay/quay/issues/788))
 -  [#788](https://github.com/quay/quay/issues/788)- [4ad5a458](https://github.com/quay/quay/commit/4ad5a458c2927be557f876a5e66928a02c67f87d): remove uploading filtering from imagestorage queries (PROJQUAY-1914) ([#764](https://github.com/quay/quay/issues/764))
 -  [#764](https://github.com/quay/quay/issues/764)### Config
- [c4ad61b5](https://github.com/quay/quay/commit/c4ad61b5831b40e95dab4aeda07f32e802b5cb2b): define default oci artifact types (PROJQUAY-2334) ([#877](https://github.com/quay/quay/issues/877)) ([#881](https://github.com/quay/quay/issues/881))
 -  [#877](https://github.com/quay/quay/issues/877) -  [#881](https://github.com/quay/quay/issues/881)### Db
- [8591caf0](https://github.com/quay/quay/commit/8591caf0372dc0f68eb146a5e28a06eedd3fea87): remove transaction from empty layer upload (PROJQUAY-1946) ([#775](https://github.com/quay/quay/issues/775))
 -  [#775](https://github.com/quay/quay/issues/775)### Defaults
- [26a06763](https://github.com/quay/quay/commit/26a06763882e6a6df35dd36668df9dc5b95b6976): Update defaults in config and schema (PROJQUAY-2425) ([#923](https://github.com/quay/quay/issues/923)) ([#925](https://github.com/quay/quay/issues/925))
 -  [#923](https://github.com/quay/quay/issues/923) -  [#925](https://github.com/quay/quay/issues/925)### Deploy
- [ce3cb357](https://github.com/quay/quay/commit/ce3cb357bd2abb7f1f7ddf6bc21f6b0294d9803e): update component label value for recovery (PROJQUAY-970) ([#832](https://github.com/quay/quay/issues/832))
 -  [#832](https://github.com/quay/quay/issues/832)- [d6616e9e](https://github.com/quay/quay/commit/d6616e9e1f4bcfc28ab80339448787cc19eca8d3): Add recovery endpoint deployment manifests (PROJQUAY-970) ([#831](https://github.com/quay/quay/issues/831))
 -  [#831](https://github.com/quay/quay/issues/831)### Deployment
- [242d4def](https://github.com/quay/quay/commit/242d4defc7d0a47f932f5338283f088c92cc8dc7): Change canary to blue deployment (PROJQUAY-1896) ([#781](https://github.com/quay/quay/issues/781))
 -  [#781](https://github.com/quay/quay/issues/781)### Doc
- [7a70a98b](https://github.com/quay/quay/commit/7a70a98b1ea616f79cdd3f691e4d2c55c4be6a7c): Fix broken links in the CHANGELOG (PROJQUAY-2298) ([#858](https://github.com/quay/quay/issues/858))
 -  [#858](https://github.com/quay/quay/issues/858)### Dockerfile
- [61d256fd](https://github.com/quay/quay/commit/61d256fdb25d11a83ad9ac4ec1a874ead1a7be4e): Update symlink in upstream dockerfile (PROJQUAY-2550) ([#889](https://github.com/quay/quay/issues/889)) ([#981](https://github.com/quay/quay/issues/981))
 -  [#889](https://github.com/quay/quay/issues/889) -  [#981](https://github.com/quay/quay/issues/981)- [1f7d128c](https://github.com/quay/quay/commit/1f7d128c8d38db7de7b909a8229102ae982198b1): Fix downstream python site-packages location (PROJQUAY-2258) ([#842](https://github.com/quay/quay/issues/842))
 -  [#842](https://github.com/quay/quay/issues/842)- [6e809033](https://github.com/quay/quay/commit/6e809033736d5d0d5855457675b91eec794fcdaa): Fix QUAYCONF symlink and config-tool build in refactored Dockerfile (PROJQUAY-2254) ([#837](https://github.com/quay/quay/issues/837))
 -  [#837](https://github.com/quay/quay/issues/837)- [86d150a2](https://github.com/quay/quay/commit/86d150a2044a1eb24140b0940ba6f830b05c842b): refactor dockerfile (PROJQUAY-1997) ([#787](https://github.com/quay/quay/issues/787))
 -  [#787](https://github.com/quay/quay/issues/787)### Email
- [a2ba0a46](https://github.com/quay/quay/commit/a2ba0a4611fdae3fd7cefe368765b1204230df6d): fix org recovery link in email (PROJQUAY-2589) ([#904](https://github.com/quay/quay/issues/904))
 -  [#904](https://github.com/quay/quay/issues/904) -  [#903](https://github.com/quay/quay/issues/903) -  [#873](https://github.com/quay/quay/issues/873)### Fips
- [65363057](https://github.com/quay/quay/commit/653630579f63498670215779ab5cf80d61857253): enforce smtp tls (PROJQUAY-1804) ([#782](https://github.com/quay/quay/issues/782)) ([#782](https://github.com/quay/quay/issues/782))
 -  [#782](https://github.com/quay/quay/issues/782)### Local-Dev
- [eea5cfcb](https://github.com/quay/quay/commit/eea5cfcb2bc7099f40d5758e360d16f49492d841): Increase timeout for gunicorn tasks to come up (PROJQUAY-2114) ([#808](https://github.com/quay/quay/issues/808))
 -  [#808](https://github.com/quay/quay/issues/808)### Migration
- [94ed4716](https://github.com/quay/quay/commit/94ed47164bad3ec3b94fa17546bb6d605ec9f188): Add composite index in manifestblob (PROJQUAY-1922) ([#769](https://github.com/quay/quay/issues/769))
 -  [#769](https://github.com/quay/quay/issues/769)### Mirror
- [95ec9478](https://github.com/quay/quay/commit/95ec9478fc6b66f8b87ddcb699c6496f1661c15c): Do not store signatures on repo mirroring (PROJQUAY-2167) ([#816](https://github.com/quay/quay/issues/816))
 -  [#816](https://github.com/quay/quay/issues/816)### Modelcache
- [b33f125c](https://github.com/quay/quay/commit/b33f125c58cadfa0342ad1767517077b1c62a664): Add read and write endpoints to Redis (PROJQUAY-1939) ([#795](https://github.com/quay/quay/issues/795))
 -  [#795](https://github.com/quay/quay/issues/795)- [df4ad945](https://github.com/quay/quay/commit/df4ad9452757dd01fb651e2836abcb4620df9db7): Make ModelCache TTL configurable (PROJQUAY-1878) ([#765](https://github.com/quay/quay/issues/765))
 -  [#765](https://github.com/quay/quay/issues/765)### Notification
- [5996cbec](https://github.com/quay/quay/commit/5996cbecf16680262bbf70d7bd9e5c8d2a14f035): check certs exists for webhooks (PROJQUAY-2424) ([#886](https://github.com/quay/quay/issues/886)) ([#900](https://github.com/quay/quay/issues/900))
 -  [#886](https://github.com/quay/quay/issues/886) -  [#900](https://github.com/quay/quay/issues/900) -  [#893](https://github.com/quay/quay/issues/893)### Oauth
- [7f23e584](https://github.com/quay/quay/commit/7f23e584d12f095e4a67e4d7fcd4fbb36693d1cc): add timeout to OAuth token exchange (PROJQUAY-1335) ([#735](https://github.com/quay/quay/issues/735))
 -  [#735](https://github.com/quay/quay/issues/735)### Oci
- [3b13ccd4](https://github.com/quay/quay/commit/3b13ccd4f190f1fce40d27c15a4146f47dfcc4d1): Accept the stricter oci layer type used by default in Helm 3.7 (PROJQUAY-2653) ([#922](https://github.com/quay/quay/issues/922)) ([#949](https://github.com/quay/quay/issues/949))
 -  [#922](https://github.com/quay/quay/issues/922) -  [#949](https://github.com/quay/quay/issues/949) -  [#907](https://github.com/quay/quay/issues/907)- [1994f2d1](https://github.com/quay/quay/commit/1994f2d108a30b6d64a1f491f2f6342604758dc9): add support for zstd compression (PROJQUAY-1417) ([#801](https://github.com/quay/quay/issues/801))
 -  [#801](https://github.com/quay/quay/issues/801)- [64bc11fe](https://github.com/quay/quay/commit/64bc11fe46acdc20795f9a51ba2c8c6926579f77): allow oci artifact registration (PROJQUAY-1032) ([#803](https://github.com/quay/quay/issues/803))
 -  [#803](https://github.com/quay/quay/issues/803)### Organization
- [6ba0e881](https://github.com/quay/quay/commit/6ba0e88128b75bc79ca4763d931d2c2be472f8cb): config to allow organization creation on push (PROJQUAY-928) ([#799](https://github.com/quay/quay/issues/799))
 -  [#799](https://github.com/quay/quay/issues/799)### Python
- [2d0adf0c](https://github.com/quay/quay/commit/2d0adf0c189dc446c79ffcb2cdae493307f0d4b2): bump pillow to 8.3.1 (PROJQUAY-2250) ([#852](https://github.com/quay/quay/issues/852))
 -  [#852](https://github.com/quay/quay/issues/852)### Registry
- [b0adc966](https://github.com/quay/quay/commit/b0adc9667c906fcf8f7be7b9818768bf4f9311c7): add support for extended repository names (PROJQUAY-1535) ([#814](https://github.com/quay/quay/issues/814))
 -  [#814](https://github.com/quay/quay/issues/814)### Release
- [28b36abb](https://github.com/quay/quay/commit/28b36abb27954459f41e01cfe8ecda677aeb0ea3): update downstream Dockerfile (PROJQUAY-1861) ([#851](https://github.com/quay/quay/issues/851))
 -  [#851](https://github.com/quay/quay/issues/851)### Repository
- [a1b7e4b5](https://github.com/quay/quay/commit/a1b7e4b51974edfe86f66788621011eef2667e6a): config to allow public repo create (PROJQUAY-1929) ([#772](https://github.com/quay/quay/issues/772))
 -  [#772](https://github.com/quay/quay/issues/772)### Requirements
- [1f9a9aee](https://github.com/quay/quay/commit/1f9a9aeecd987539bc20017f762590ce20dc7bd5): bump cryptography package version ([#939](https://github.com/quay/quay/issues/939)) ([#940](https://github.com/quay/quay/issues/940))
 -  [#939](https://github.com/quay/quay/issues/939) -  [#940](https://github.com/quay/quay/issues/940) -  [#943](https://github.com/quay/quay/issues/943)### Secscan
- [1b061534](https://github.com/quay/quay/commit/1b0615341348aafc6ba2776ea90e84e4a6d175e4): continue iterating after failure (PROJQUAY-2563) ([#894](https://github.com/quay/quay/issues/894))
 -  [#894](https://github.com/quay/quay/issues/894) -  [#896](https://github.com/quay/quay/issues/896) -  [#893](https://github.com/quay/quay/issues/893)- [79e97785](https://github.com/quay/quay/commit/79e9778576e715da04a5eafc8dbde2e78955a095): handle proxy model fallback to noop v2 (PROJQUAY-2289) ([#847](https://github.com/quay/quay/issues/847))
 -  [#847](https://github.com/quay/quay/issues/847)- [65ec47ab](https://github.com/quay/quay/commit/65ec47ab4b67fcd84fb9a7aa0b4f9f31c5b4d902): handle remote layer url when sending request to Clair (PROJQUAY-2269) ([#841](https://github.com/quay/quay/issues/841))
 -  [#841](https://github.com/quay/quay/issues/841)### Secscan
- [fa0e8618](https://github.com/quay/quay/commit/fa0e8618494138dc78c8496c0d9d6d83b66335ca): clair v4 enrichment (PROJQUAY-2102) ([#840](https://github.com/quay/quay/issues/840))
 -  [#840](https://github.com/quay/quay/issues/840)### Static
- [3488e785](https://github.com/quay/quay/commit/3488e7855a391ec4b446982810c8eed9f28935c3): vendor webfonts dir ([#1017](https://github.com/quay/quay/issues/1017))
 -  [#1017](https://github.com/quay/quay/issues/1017)- [d93d85fa](https://github.com/quay/quay/commit/d93d85fa6647b7ed57c654e33c5c20bb48a11e39): vendor external libraries ([#1015](https://github.com/quay/quay/issues/1015))
 -  [#1015](https://github.com/quay/quay/issues/1015)### Templates
- [1c157e2a](https://github.com/quay/quay/commit/1c157e2a5b3ad4d091bc9480761b850d8856a15a): escape templated script value (PROJQUAY-970) ([#828](https://github.com/quay/quay/issues/828))
 -  [#828](https://github.com/quay/quay/issues/828)### Ui
- [a180c52a](https://github.com/quay/quay/commit/a180c52aaab7f7cd7ecc72c5a41b85c75970300e): force uses to sign-in page to fix SSO CSRF cookie issue (PROJQUAY-2340) ([#865](https://github.com/quay/quay/issues/865))
 -  [#865](https://github.com/quay/quay/issues/865)- [97fc1b5c](https://github.com/quay/quay/commit/97fc1b5cc774dbc6d085490548dc4695b440d55e): Require user to enter repository when deleting (PROJQUAY-763) ([#432](https://github.com/quay/quay/issues/432))
 -  [#432](https://github.com/quay/quay/issues/432)- [de12ed74](https://github.com/quay/quay/commit/de12ed7482859e3d6d4ce89d5ece2e701996d6ee): Add repo state column when mirroring enabled (PROJQUAY-591) ([#419](https://github.com/quay/quay/issues/419))
 -  [#419](https://github.com/quay/quay/issues/419)### Util
- [cfd4e8c4](https://github.com/quay/quay/commit/cfd4e8c46b7f174c3bc028a843293e58a5d37eab): fix matching multiples in jsontemplate.py (PROJQUAY-0000) ([#800](https://github.com/quay/quay/issues/800))
 -  [#800](https://github.com/quay/quay/issues/800)### Utility
- [69777301](https://github.com/quay/quay/commit/6977730185710cec71ef39edc55b5d774bc278b4): Fixes backfillreplication script to use manifest blobs (PROJQUAY-2218) ([#826](https://github.com/quay/quay/issues/826))
 -  [#826](https://github.com/quay/quay/issues/826)### NOTE

This change simply allows the use of "/" in repository
names needed for certain Openshift use cases. This does not implement
any new permission model for nested paths. i.e A repository with a
nested path is treated as a single repository under a _single_
namespace.


<a name="v3.6.0-alpha.9"></a>
## [v3.6.0-alpha.9] - 2021-04-21
### Cache
- [1180ea99](https://github.com/quay/quay/commit/1180ea99fae3787eccfa53801af6199d3af3bcac): remove GlobalLock from redis model cache (PROJQUAY-1902) ([#755](https://github.com/quay/quay/issues/755))
 -  [#755](https://github.com/quay/quay/issues/755)- [780685c4](https://github.com/quay/quay/commit/780685c490097ce7cf9515e0642505a45817df6a): add Redis model cache implementation (PROJQUAY-788) ([#444](https://github.com/quay/quay/issues/444))
 -  [#444](https://github.com/quay/quay/issues/444)### Chore
- [8921114d](https://github.com/quay/quay/commit/8921114d41faa184a787a93802394f5ab783d488): v3.6.0-alpha.9 changelog bump (PROJQUAY-1486) ([#763](https://github.com/quay/quay/issues/763))
 -  [#763](https://github.com/quay/quay/issues/763)- [0ffe9cee](https://github.com/quay/quay/commit/0ffe9ceecac456ab2b722459aa5aebe70c902fe9): correct chnglog params (PROJQUAY-1486) ([#762](https://github.com/quay/quay/issues/762))
 -  [#762](https://github.com/quay/quay/issues/762)- [addaeac0](https://github.com/quay/quay/commit/addaeac04aaab3d887258f53fdbb2fc85240bd62): fix release image tag to retain leading 'v' (PROJQUAY-1486) ([#739](https://github.com/quay/quay/issues/739))
 -  [#739](https://github.com/quay/quay/issues/739)- [ce7aa978](https://github.com/quay/quay/commit/ce7aa97802aac4118894cc5e97a81e431fe79f35): bump version to 3.6.0 (PROJQUAY-1861) ([#738](https://github.com/quay/quay/issues/738))
 -  [#738](https://github.com/quay/quay/issues/738)### Ci
- [e6011cff](https://github.com/quay/quay/commit/e6011cff5ba539a51a25ec2f0298068f63819c6e): include optional merge commit number in commit check job (PROJQUAY-1486) ([#742](https://github.com/quay/quay/issues/742))
 -  [#742](https://github.com/quay/quay/issues/742)### Deployment
- [080010e8](https://github.com/quay/quay/commit/080010e8cd7f2646c01fe29f17fae502c3114b31): Add image tag param to the deploy file (PROJQUAY-1896) ([#759](https://github.com/quay/quay/issues/759))
 -  [#759](https://github.com/quay/quay/issues/759)- [03c610d5](https://github.com/quay/quay/commit/03c610d51011061dd33499b5c38aacfcadf0f0c6): Add canary deployment to quay-app (PROJQUAY-1896) ([#754](https://github.com/quay/quay/issues/754))
 -  [#754](https://github.com/quay/quay/issues/754)### Gc
- [efa0692e](https://github.com/quay/quay/commit/efa0692e5ac3c47719dc8940d65feaa5f26a568b): increment quay_gc_repos_purged for NamespaceGCWorker (PROJQUAY-1802) ([#749](https://github.com/quay/quay/issues/749))
 -  [#749](https://github.com/quay/quay/issues/749)- [f774e4c6](https://github.com/quay/quay/commit/f774e4c6b6c674c822057a1d3dd49a3d5c36e6ca): add metrics for deleted resources ([#711](https://github.com/quay/quay/issues/711))
 -  [#711](https://github.com/quay/quay/issues/711)### Lock
- [c12654bf](https://github.com/quay/quay/commit/c12654bf46da701cd30dd9995091444bc046cf69): allows global lock to be used from main app (PROJQUAY-788) ([#745](https://github.com/quay/quay/issues/745))
 -  [#745](https://github.com/quay/quay/issues/745)- [778afaf3](https://github.com/quay/quay/commit/778afaf36be17d54958d5fa5bd8f365bea3ee965): reuse redis client when creating locks (PROJQUAY-1872) ([#741](https://github.com/quay/quay/issues/741))
 -  [#741](https://github.com/quay/quay/issues/741)### Queueworker
- [90f9ef95](https://github.com/quay/quay/commit/90f9ef95af98c7177566abf41213b22839e7206b): prevent stop event on WorkerSleepException (PROJQUAY-1857) ([#737](https://github.com/quay/quay/issues/737))
 -  [#737](https://github.com/quay/quay/issues/737)
<a name="v3.6.0-alpha.8"></a>
## [v3.6.0-alpha.8] - 2021-04-09
### Chore
- [ecc125ff](https://github.com/quay/quay/commit/ecc125ff93c5a8328290195ab7dc2156a8ce32df): v3.6.0-alpha.8 changelog bump (PROJQUAY-1486) ([#732](https://github.com/quay/quay/issues/732))
 -  [#732](https://github.com/quay/quay/issues/732)- [166d17ab](https://github.com/quay/quay/commit/166d17ab4fb9ab65ffb0f59c35246e406ffbdf52): correct cut-release.yml (PROJQUAY-1486) ([#731](https://github.com/quay/quay/issues/731))
 -  [#731](https://github.com/quay/quay/issues/731)
<a name="v3.6.0-alpha.7"></a>
## [v3.6.0-alpha.7] - 2021-04-09
### Chore
- [b54c8999](https://github.com/quay/quay/commit/b54c89997f64b66431accacc348e8fcefb02a42c): v3.6.0-alpha.7 changelog bump (PROJQUAY-1486) ([#730](https://github.com/quay/quay/issues/730))
 -  [#730](https://github.com/quay/quay/issues/730)- [bfc9d75c](https://github.com/quay/quay/commit/bfc9d75cab49df0bfd901a355a9bcb53bfeb5407): fix cut-release.yml (PROJQUAY-1468) ([#729](https://github.com/quay/quay/issues/729))
 -  [#729](https://github.com/quay/quay/issues/729)
<a name="v3.6.0-alpha.6"></a>
## [v3.6.0-alpha.6] - 2021-04-09
### Chore
- [6c7dcb84](https://github.com/quay/quay/commit/6c7dcb8425debd7f9fcfed466a93ec40ad62fb1d): correct git-chglog config (PROJQUAY-1468) ([#728](https://github.com/quay/quay/issues/728))
 -  [#728](https://github.com/quay/quay/issues/728)- [43891120](https://github.com/quay/quay/commit/438911205aed1f543a97f0226319449eac3b927c): v3.6.0-alpha.6 changelog bump (PROJQUAY-1486) ([#727](https://github.com/quay/quay/issues/727))
 -  [#727](https://github.com/quay/quay/issues/727)- [043dbffc](https://github.com/quay/quay/commit/043dbffc59ce92fb125e678db579e7db45590efd): fix changelog template (PROJQUAY-1486) ([#726](https://github.com/quay/quay/issues/726))
 -  [#726](https://github.com/quay/quay/issues/726)- [03347285](https://github.com/quay/quay/commit/033472855fea2226925932486f4a98d8b960a7f7): parse new CHANGELOG.md format (PROJQUAY-1486) ([#725](https://github.com/quay/quay/issues/725))
 -  [#725](https://github.com/quay/quay/issues/725)
<a name="v3.6.0-alpha.5"></a>
## [v3.6.0-alpha.5] - 2021-04-08
### Release
- [fba629b2](https://github.com/quay/quay/commit/fba629b2dbd2679071ecdfe13d6463a9b96a2fec): fixing Release action (PROJQUAY-1486) ([#723](https://github.com/quay/quay/issues/723))
 -  [#723](https://github.com/quay/quay/issues/723)
<a name="v3.6.0-alpha.4"></a>
## [v3.6.0-alpha.4] - 2021-04-08
### Release
- [9dd55dee](https://github.com/quay/quay/commit/9dd55deed36c82b9499b3d230802e37e35b2cbc7): fixing Release action (PROJQUAY-1486)

[Unreleased]: https://github.com/quay/quay/compare/3.6.3...HEAD
[3.6.3]: https://github.com/quay/quay/compare/v3.6.2...3.6.3
[v3.6.2]: https://github.com/quay/quay/compare/v3.6.0-alpha.9...v3.6.2
[v3.6.0-alpha.9]: https://github.com/quay/quay/compare/v3.6.0-alpha.8...v3.6.0-alpha.9
[v3.6.0-alpha.8]: https://github.com/quay/quay/compare/v3.6.0-alpha.7...v3.6.0-alpha.8
[v3.6.0-alpha.7]: https://github.com/quay/quay/compare/v3.6.0-alpha.6...v3.6.0-alpha.7
[v3.6.0-alpha.6]: https://github.com/quay/quay/compare/v3.6.0-alpha.5...v3.6.0-alpha.6
[v3.6.0-alpha.5]: https://github.com/quay/quay/compare/v3.6.0-alpha.4...v3.6.0-alpha.5
[v3.6.0-alpha.4]: https://github.com/quay/quay/compare/v3.6.0-alpha.3...v3.6.0-alpha.4
## Historical Changelog
[CHANGELOG.md](https://github.com/quay/quay/blob/96b17b8338fb10ca2ed12e9bc920dcbba148289c/CHANGELOG.md)