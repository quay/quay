## Red Hat Quay Release Notes
(Red Hat Customer Portal)[https://access.redhat.com/documentation/en-us/red_hat_quay/3.5/html/red_hat_quay_release_notes/index]


<a name="v3.6.4"></a>
## [v3.6.4] - 2022-03-02
### Auth
- [0033f9b8](https://github.com/quay/quay/commit/0033f9b851502bd474d8ddd3faf4e5d78f43f9ca): Fix oauth code flow (PROJQUAY-781) ([#1044](https://github.com/quay/quay/issues/1044))
 -  [#1044](https://github.com/quay/quay/issues/1044)### Billing
- [259da89c](https://github.com/quay/quay/commit/259da89cb64c85166f7bcd4b13ef007934e4c032): Remove type hints for FakeStripe (PROJQUAY-2777) ([#974](https://github.com/quay/quay/issues/974))
 -  [#974](https://github.com/quay/quay/issues/974)- [8d0aa9ff](https://github.com/quay/quay/commit/8d0aa9ffedb7d8148e890badf5c0bd86f4ef6e40): Remove annotations for type hints in billing (PROJQUAY-2777) ([#973](https://github.com/quay/quay/issues/973))
 -  [#973](https://github.com/quay/quay/issues/973)### Blobuploadcleanupworker
- [f35f3f13](https://github.com/quay/quay/commit/f35f3f137cd5d1e4594438e0db5c498651f1a396): Add BLOBUPLOAD_DELETION_DATE_THRESHOLD (PROJQUAY-2915) ([#1022](https://github.com/quay/quay/issues/1022))
 -  [#1022](https://github.com/quay/quay/issues/1022)- [22282dae](https://github.com/quay/quay/commit/22282dae093fc8f8bee543b1fa33e7f3c9c6b618): Add cleanup for orphaned blobs (PROJQUAY-2313) ([#967](https://github.com/quay/quay/issues/967))
 -  [#967](https://github.com/quay/quay/issues/967)### Build
- [443b8d50](https://github.com/quay/quay/commit/443b8d50a9300a850473457deedc45c942116ebd): Update pyrsistent to fix Dockerfile.deploy (PROJQUAY-3125) ([#1079](https://github.com/quay/quay/issues/1079))
 -  [#1079](https://github.com/quay/quay/issues/1079)- [fba69d93](https://github.com/quay/quay/commit/fba69d939ec336c5fc46a9e5f5cfd9ee3b2ee38e): Add required setup.cfg for downstream build (PROJQUAY-2713) ([#946](https://github.com/quay/quay/issues/946)) ([#993](https://github.com/quay/quay/issues/993))
 -  [#946](https://github.com/quay/quay/issues/946) -  [#993](https://github.com/quay/quay/issues/993)- [eb668cad](https://github.com/quay/quay/commit/eb668cad6622cc902bf1b88506dc0a8fc6d9f921): Use a configtool tag in the Dockerfile instead of master (PROJQUAY-2777) ([#972](https://github.com/quay/quay/issues/972))
 -  [#972](https://github.com/quay/quay/issues/972)- [78f8081a](https://github.com/quay/quay/commit/78f8081a0a53dd07096adc2545c9254112df3921): Use a configtool tag in the Dockerfile instead of master (PROJQUAY-2777) ([#971](https://github.com/quay/quay/issues/971))
 -  [#971](https://github.com/quay/quay/issues/971)- [a347d316](https://github.com/quay/quay/commit/a347d3167dece3078a119203137bf4230f8c01e5): Update backup base image name (PROJQUAY-2372) ([#965](https://github.com/quay/quay/issues/965))
 -  [#965](https://github.com/quay/quay/issues/965)- [d2f4efd8](https://github.com/quay/quay/commit/d2f4efd8428c6d7da6fd3038eaff6c15d57b05a1): Remove the image archive in post-deploy  (PROJQUAY-2372) ([#963](https://github.com/quay/quay/issues/963))
 -  [#963](https://github.com/quay/quay/issues/963)- [af2eeaa6](https://github.com/quay/quay/commit/af2eeaa61770adf69011369bb2efc86d3878165b): Use docker-archive for post-deploy script  (PROJQUAY-2372) ([#962](https://github.com/quay/quay/issues/962))
 -  [#962](https://github.com/quay/quay/issues/962)- [e8cf6339](https://github.com/quay/quay/commit/e8cf6339c31e76df608cab074f5acc3ee5f12095): Add docker-save to push images via skopeo on rhel-8 (PROJQUAY-2372) ([#960](https://github.com/quay/quay/issues/960))
 -  [#960](https://github.com/quay/quay/issues/960)- [d8b0e949](https://github.com/quay/quay/commit/d8b0e949005e6f78dd1368a55c578ac1fecc6091): Add docker-save to push images via skopeo on rhel-8 (PROJQUAY-2372) ([#959](https://github.com/quay/quay/issues/959))
 -  [#959](https://github.com/quay/quay/issues/959)- [759a83fa](https://github.com/quay/quay/commit/759a83fabfd64ec18554120fe74718599727fcd3): use Dockerfile for building quay app-sre (PROJQUAY-2373) ([#926](https://github.com/quay/quay/issues/926))
 -  [#926](https://github.com/quay/quay/issues/926)### Build(Deps)
- [4b4f16e1](https://github.com/quay/quay/commit/4b4f16e1b4bb24bea0a9e0d848baaab481de2e44): bump url-parse from 1.5.6 to 1.5.8 ([#1151](https://github.com/quay/quay/issues/1151))
 -  [#1151](https://github.com/quay/quay/issues/1151)- [49c56aa1](https://github.com/quay/quay/commit/49c56aa1c5c7e009df842d5f2825d7d9b357d58c): bump url-parse from 1.5.2 to 1.5.6 ([#1125](https://github.com/quay/quay/issues/1125))
 -  [#1125](https://github.com/quay/quay/issues/1125)- [c96d1fbc](https://github.com/quay/quay/commit/c96d1fbc1903aef8e28eae90afa9216e57ccebee): bump protobuf from 3.12.2 to 3.15.0 ([#1110](https://github.com/quay/quay/issues/1110))
 -  [#1110](https://github.com/quay/quay/issues/1110)- [102705c9](https://github.com/quay/quay/commit/102705c9469a6c5624308a31b78d10cb17a00ddd): bump pillow from 8.3.2 to 9.0.0 ([#1059](https://github.com/quay/quay/issues/1059))
 -  [#1059](https://github.com/quay/quay/issues/1059)- [e7e093b0](https://github.com/quay/quay/commit/e7e093b0a6c863930594eb4aad1db48289860bc9): bump qs from 6.3.1 to 6.3.3 ([#1086](https://github.com/quay/quay/issues/1086))
 -  [#1086](https://github.com/quay/quay/issues/1086)- [88956630](https://github.com/quay/quay/commit/889566305bc613d521c0e1d773f9773db32a5d30): bump y18n from 3.2.1 to 3.2.2 ([#1080](https://github.com/quay/quay/issues/1080))
 -  [#1080](https://github.com/quay/quay/issues/1080)- [21f3538f](https://github.com/quay/quay/commit/21f3538f4eb939c39c217726670288b6b745669e): bump python-ldap from 3.2.0 to 3.4.0 ([#1002](https://github.com/quay/quay/issues/1002))
 -  [#1002](https://github.com/quay/quay/issues/1002)- [ae516d84](https://github.com/quay/quay/commit/ae516d8481a601a58cc86bf323a607991b7b36c2): bump reportlab from 3.5.34 to 3.5.55 ([#978](https://github.com/quay/quay/issues/978))
 -  [#978](https://github.com/quay/quay/issues/978)- [288f31bb](https://github.com/quay/quay/commit/288f31bbfbced3850836ba155b602ab54d872c7d): bump pip from 20.2.3 to 21.1 ([#977](https://github.com/quay/quay/issues/977))
 -  [#977](https://github.com/quay/quay/issues/977)- [8eab6366](https://github.com/quay/quay/commit/8eab6366cdcfa273da88ab6fcd0c94681b24fb74): bump babel from 2.8.0 to 2.9.1 ([#944](https://github.com/quay/quay/issues/944))
 -  [#944](https://github.com/quay/quay/issues/944)- [66373020](https://github.com/quay/quay/commit/663730203b6f7d00076051d6e83e99b9b71f04a8): bump url-parse from 1.4.0 to 1.5.2 ([#873](https://github.com/quay/quay/issues/873))
 -  [#873](https://github.com/quay/quay/issues/873)- [299fa6d9](https://github.com/quay/quay/commit/299fa6d958ef79f33d590268368425339467905a): bump pillow from 8.3.1 to 8.3.2 ([#882](https://github.com/quay/quay/issues/882))
 -  [#882](https://github.com/quay/quay/issues/882)- [b6495343](https://github.com/quay/quay/commit/b6495343942ccd32a3227a2dd0d6646d80772d8b): bump path-parse from 1.0.5 to 1.0.7 ([#870](https://github.com/quay/quay/issues/870))
 -  [#870](https://github.com/quay/quay/issues/870)### Builders
- [30ab139e](https://github.com/quay/quay/commit/30ab139ea9957655a6b9e24a1a26f41b19d09748): Remove ServerSideEncryption param from presigned URL (PROJQUAY-3180) ([#1105](https://github.com/quay/quay/issues/1105))
 -  [#1105](https://github.com/quay/quay/issues/1105)- [7082f867](https://github.com/quay/quay/commit/7082f867a652c8d43a9be64283d71866b160ef6c): Update boto to fix signature error (PROJQUAY-2542) ([#1087](https://github.com/quay/quay/issues/1087))
 -  [#1087](https://github.com/quay/quay/issues/1087)- [dce0b934](https://github.com/quay/quay/commit/dce0b934337b5f401f0107492e99e72fcb465c99): Remove socket_timeout from the redis client (PROJQUAY-2542) ([#1084](https://github.com/quay/quay/issues/1084))
 -  [#1084](https://github.com/quay/quay/issues/1084)- [b7d325ed](https://github.com/quay/quay/commit/b7d325ed42827db9eda2d9f341cb5a6cdfd155a6): Make single_connection_client conifgurable (PROJQUAY-3025) ([#1055](https://github.com/quay/quay/issues/1055))
 -  [#1055](https://github.com/quay/quay/issues/1055)### Buildman
- [ceb9262b](https://github.com/quay/quay/commit/ceb9262b7e5484fe7cd0e050e24c014c7e78c68c): Add EXECUTOR parameter (PROJQUAY-3278) ([#1134](https://github.com/quay/quay/issues/1134))
 -  [#1134](https://github.com/quay/quay/issues/1134)- [3ca44073](https://github.com/quay/quay/commit/3ca44073b17a0c42f98d44811224652a05e306cd): prevent systemd oneshot service from timing (PROJQUAY-3304) ([#1149](https://github.com/quay/quay/issues/1149))
 -  [#1149](https://github.com/quay/quay/issues/1149)- [32691dd8](https://github.com/quay/quay/commit/32691dd8127fc23910a80edfc84cf70ba25fb806): Set build token expiration to builder's lifetime (PROJQUAY-3281) ([#1142](https://github.com/quay/quay/issues/1142))
 -  [#1142](https://github.com/quay/quay/issues/1142)- [a0443340](https://github.com/quay/quay/commit/a0443340cb57d9dba4a3dea9d335cf0e3ad29679): fix multiple build retries phase (PROJQUAY-3281) ([#1139](https://github.com/quay/quay/issues/1139))
 -  [#1139](https://github.com/quay/quay/issues/1139)- [9b892626](https://github.com/quay/quay/commit/9b89262640022250d9c3be7b4611bc2bf1758419): configurable build job registration timeout (PROJQUAY-3280) ([#1135](https://github.com/quay/quay/issues/1135))
 -  [#1135](https://github.com/quay/quay/issues/1135)- [a29e64be](https://github.com/quay/quay/commit/a29e64be187a057850fea8f34b809e6699809b43): Add kubernetesPodman build option (PROJQUAY-3052) ([#1066](https://github.com/quay/quay/issues/1066))
 -  [#1066](https://github.com/quay/quay/issues/1066)- [eaaa3adb](https://github.com/quay/quay/commit/eaaa3adbf05422a2625946e7cc5d7999d4325430): allow use of public builder image (PROJQUAY-3179) ([#1103](https://github.com/quay/quay/issues/1103))
 -  [#1103](https://github.com/quay/quay/issues/1103)- [b07b44a7](https://github.com/quay/quay/commit/b07b44a7eb2b70282e0cfb07362d33fc3666c358): fix kubernetes not returning correct running count (PROJQUAY-3169) ([#1099](https://github.com/quay/quay/issues/1099))
 -  [#1099](https://github.com/quay/quay/issues/1099)### CONTRIBUTING
- [f0edbceb](https://github.com/quay/quay/commit/f0edbceb5b24c1a5298eeece77e53de9ef643372): document backporting process ([#1043](https://github.com/quay/quay/issues/1043))
 -  [#1043](https://github.com/quay/quay/issues/1043)### Cache
- [ccf6ada1](https://github.com/quay/quay/commit/ccf6ada16a1feac137a8aa7ea828a99df66586ac): handle uncaught redis exception (PROJQUAY-2614) ([#907](https://github.com/quay/quay/issues/907))
 -  [#907](https://github.com/quay/quay/issues/907)### Chore
- [a3ad25c4](https://github.com/quay/quay/commit/a3ad25c48a04bd3319f1b393e0b1f2886a6269b9): Remove unneeded flags fromt he config schema ([#1152](https://github.com/quay/quay/issues/1152))
 -  [#1152](https://github.com/quay/quay/issues/1152)- [2344adb8](https://github.com/quay/quay/commit/2344adb8194bd026572903f8784003ebd8e81b7c): remove unused tools (PROJQUAY-0) ([#1113](https://github.com/quay/quay/issues/1113))
 -  [#1113](https://github.com/quay/quay/issues/1113)- [9bdbba6f](https://github.com/quay/quay/commit/9bdbba6ff946042709aa91bb9d80193120aba785): Remove unused files ([#1067](https://github.com/quay/quay/issues/1067))
 -  [#1067](https://github.com/quay/quay/issues/1067)- [65100439](https://github.com/quay/quay/commit/65100439f6dd70b12db2276ec61cff99704bfa4e): download aws ip ranges via github workflow ([#1041](https://github.com/quay/quay/issues/1041))
 -  [#1041](https://github.com/quay/quay/issues/1041)- [b7037d9c](https://github.com/quay/quay/commit/b7037d9c50bf7a282c7983577b380cfc401b7825): Bump up config-tool version v0.1.9 ([#992](https://github.com/quay/quay/issues/992))
 -  [#992](https://github.com/quay/quay/issues/992)- [2ffc12b3](https://github.com/quay/quay/commit/2ffc12b3eb5e36c070df80fcd5ffffa9593fd22a): cleanup remaining artifacts remaining related to aci signing (PROJQUAY-2792) ([#968](https://github.com/quay/quay/issues/968))
 -  [#968](https://github.com/quay/quay/issues/968)- [ae129b45](https://github.com/quay/quay/commit/ae129b45e9db29f4e787e0190afc6af4c29ec277): Bump up config-tool version v0.1.8 ([#984](https://github.com/quay/quay/issues/984))
 -  [#984](https://github.com/quay/quay/issues/984)- [c8092069](https://github.com/quay/quay/commit/c8092069a296726fe888f6c3b8f4e15d8f7958e8): Bump up config-tool version ([#983](https://github.com/quay/quay/issues/983))
 -  [#983](https://github.com/quay/quay/issues/983)- [ba08ddd7](https://github.com/quay/quay/commit/ba08ddd707e7ac4b6e29460deef533eb23c6036f): Bump up config-tool version ([#982](https://github.com/quay/quay/issues/982))
 -  [#982](https://github.com/quay/quay/issues/982)- [bbacf232](https://github.com/quay/quay/commit/bbacf2321facf0fbb7fdc407799623943fa14fea): bump gevent related packages' version (PROJQUAY-2821) ([#979](https://github.com/quay/quay/issues/979))
 -  [#979](https://github.com/quay/quay/issues/979)- [8ef0aff8](https://github.com/quay/quay/commit/8ef0aff83dffac3ae32938dc9105a5926a94c10d): improve check for JIRA ticket (PROJQUAY-2623) ([#919](https://github.com/quay/quay/issues/919))
 -  [#919](https://github.com/quay/quay/issues/919)- [c90b444f](https://github.com/quay/quay/commit/c90b444f8322a425ebd718809eac25c3c7cae265): Provide timestamps on container startup including registry, mirror and config container ([#921](https://github.com/quay/quay/issues/921))
 -  [#921](https://github.com/quay/quay/issues/921)- [16dcebf1](https://github.com/quay/quay/commit/16dcebf101f807738868711246614a9dd10f5566): build and publish workflow (PROJQUAY-2556)
- [79703a91](https://github.com/quay/quay/commit/79703a91760a7e7fbbadf9ebec6a85fe72a35b78): Move qemu outside of quay repo to its github repo (PROJQUAY-2342) ([#866](https://github.com/quay/quay/issues/866))
 -  [#866](https://github.com/quay/quay/issues/866)### Chore(Dockerfile)
- [0f7fdb7e](https://github.com/quay/quay/commit/0f7fdb7e847df7ac68154c7627486c5ca048736c): add local-dev-env build stage (PROJQUAY-2501) ([#883](https://github.com/quay/quay/issues/883))
 -  [#883](https://github.com/quay/quay/issues/883)### Chore: V3.6.3 Changelog Bump (Https
- [62e2eac1](https://github.com/quay/quay/commit/62e2eac1b083dc6a6c0cdc882f8494ef9dfcf999): //issues.redhat.com/browse/PROJQUAY-3028) ([#1118](https://github.com/quay/quay/issues/1118))
 -  [#1118](https://github.com/quay/quay/issues/1118)### Ci
- [e2921d7a](https://github.com/quay/quay/commit/e2921d7af8d3d2ed3bc8f44c939bfcc6b340c52b): Enable workflow dispatch for build and publish (PROJQUAY-3310) ([#1155](https://github.com/quay/quay/issues/1155))
 -  [#1155](https://github.com/quay/quay/issues/1155)- [c7c4c0dc](https://github.com/quay/quay/commit/c7c4c0dc4ca9681482a100a831950355634c3b61): Update funcparserlib version (PROJQUAY-2520) ([#893](https://github.com/quay/quay/issues/893))
 -  [#893](https://github.com/quay/quay/issues/893)### Clean.Sh
- [6b5e7f50](https://github.com/quay/quay/commit/6b5e7f506fe6cbb124ede711d9480e5f39eb70f1): don't remove webfonts dir since its now versioned ([#1025](https://github.com/quay/quay/issues/1025))
 -  [#1025](https://github.com/quay/quay/issues/1025)### Cleanup
- [687abaa2](https://github.com/quay/quay/commit/687abaa2d73eaf99dea5c0ddf078ec6fc656ce30): Removing requirements-nover.txt (PROJQUAY-2985) ([#1038](https://github.com/quay/quay/issues/1038))
 -  [#1038](https://github.com/quay/quay/issues/1038)### Config
- [c02f912f](https://github.com/quay/quay/commit/c02f912f4364ab1a4299a9e576f99825cadaefbb): Update config-tool version to v0.1.10 (PROJQUAY-3125) ([#1078](https://github.com/quay/quay/issues/1078))
 -  [#1078](https://github.com/quay/quay/issues/1078)- [c507eeff](https://github.com/quay/quay/commit/c507eeff2eae61efe1a18a4b0e6addce4d37bc5a): define default oci artifact types (PROJQUAY-2334) ([#877](https://github.com/quay/quay/issues/877))
 -  [#877](https://github.com/quay/quay/issues/877)### Config.Py
- [d14da17a](https://github.com/quay/quay/commit/d14da17a401caed79e87a3685b554a0007e5de51): Add support for source containers (PROJQUAY-2271) ([#954](https://github.com/quay/quay/issues/954))
 -  [#954](https://github.com/quay/quay/issues/954)### Data/Buildlogs
- [e1ae52ee](https://github.com/quay/quay/commit/e1ae52ee23deec4ccaf76e2f3ef04f7e79a6fa4c): format file with black ([#1061](https://github.com/quay/quay/issues/1061))
 -  [#1061](https://github.com/quay/quay/issues/1061)### Database
- [24b3c153](https://github.com/quay/quay/commit/24b3c15334dd354f16ed79a766dcaba43561cf5a): handle nested transaaction when trying to close before transaction (PROJQUAY-3303) ([#1157](https://github.com/quay/quay/issues/1157))
 -  [#1157](https://github.com/quay/quay/issues/1157) -  [#1153](https://github.com/quay/quay/issues/1153)- [7cdb88b5](https://github.com/quay/quay/commit/7cdb88b5789987c492666de381a666c5afce8ef3): force close existing non-pooled connections before transaction (PROJQUAY-3303) ([#1153](https://github.com/quay/quay/issues/1153))
 -  [#1153](https://github.com/quay/quay/issues/1153)- [c5608d97](https://github.com/quay/quay/commit/c5608d976511e5645b3c879908d7f839323a83cd): retry connections on stale MySQL connections (PROJQUAY-3303) ([#1148](https://github.com/quay/quay/issues/1148))
 -  [#1148](https://github.com/quay/quay/issues/1148)### Db
- [eb62f4e9](https://github.com/quay/quay/commit/eb62f4e999768a3a5acc68957e7198435ef432ad): remove url unqoute from migration logic (PROJQUAY-3266) ([#1126](https://github.com/quay/quay/issues/1126))
 -  [#1126](https://github.com/quay/quay/issues/1126)### Debug
- [9c327425](https://github.com/quay/quay/commit/9c32742514129207b95838979a708db9e1b3f48a): Log X-Forwaded-For for requests (PROJQUAY-2883) ([#1027](https://github.com/quay/quay/issues/1027))
 -  [#1027](https://github.com/quay/quay/issues/1027)- [4a02e1bd](https://github.com/quay/quay/commit/4a02e1bd0955b2cffd1805830274607c9b8c932d): Log X-Forwaded-For for requests (PROJQUAY-2883) ([#1026](https://github.com/quay/quay/issues/1026))
 -  [#1026](https://github.com/quay/quay/issues/1026)### Defaults
- [a29f3e0e](https://github.com/quay/quay/commit/a29f3e0eea6d475d6f621da19b083876737d5262): Update defaults in config and schema (PROJQUAY-2425) ([#923](https://github.com/quay/quay/issues/923))
 -  [#923](https://github.com/quay/quay/issues/923)### Deploy
- [6356fbb1](https://github.com/quay/quay/commit/6356fbb1b9cdddbe1e231d01b196ce7cf926bbb7): Add ignore validation for py3 deployment (PROJQUAY-2542) ([#1121](https://github.com/quay/quay/issues/1121))
 -  [#1121](https://github.com/quay/quay/issues/1121)- [d43b41c5](https://github.com/quay/quay/commit/d43b41c58a8c53dfc49458e2743fe915725fe269): Add GRPC service for builds (PROJQUAY-3189) ([#1109](https://github.com/quay/quay/issues/1109))
 -  [#1109](https://github.com/quay/quay/issues/1109)- [293e0619](https://github.com/quay/quay/commit/293e0619de040994331f4437a0b35dac5d10f323): Add LB service with no proxy-protocol (PROJQUAY-2883) ([#1006](https://github.com/quay/quay/issues/1006))
 -  [#1006](https://github.com/quay/quay/issues/1006)- [1589351b](https://github.com/quay/quay/commit/1589351b7433941411ec4e12d1a3fe9cfdcc5c31): Add clair back fill worker deployment manifests ([#991](https://github.com/quay/quay/issues/991))
 -  [#991](https://github.com/quay/quay/issues/991)- [01d41364](https://github.com/quay/quay/commit/01d4136406e237b32c80d35f6123b2c0b53f5b93): Update syslog image tag(PROJQUAY-2374) ([#966](https://github.com/quay/quay/issues/966))
 -  [#966](https://github.com/quay/quay/issues/966)- [7458578d](https://github.com/quay/quay/commit/7458578d1a5fe669e2d2b4f943360a7acaacac54): Seperate py3 deployment manifests (PROJQUAY-2374) ([#931](https://github.com/quay/quay/issues/931))
 -  [#931](https://github.com/quay/quay/issues/931)- [5a56145b](https://github.com/quay/quay/commit/5a56145ba5d49702430b030b84df8a66426b77c8): Update app-sre build script (PROJQUAY-2374) ([#934](https://github.com/quay/quay/issues/934))
 -  [#934](https://github.com/quay/quay/issues/934)- [6b01bd12](https://github.com/quay/quay/commit/6b01bd124531e428b2ebd99f9f4f59c5907a024c): Push py3 images to a different quay repo (PROJQUAY-2374) ([#930](https://github.com/quay/quay/issues/930))
 -  [#930](https://github.com/quay/quay/issues/930)- [173dfbfc](https://github.com/quay/quay/commit/173dfbfc8adf67286e22e1f5daadf984d5fcbf3d): Update quay deployment manifests for py3 canary (PROJQUAY-2373) ([#902](https://github.com/quay/quay/issues/902))
 -  [#902](https://github.com/quay/quay/issues/902)### Deps
- [bb53127d](https://github.com/quay/quay/commit/bb53127d015c6e9c2fee0643281667c539905f4b): upgrade upstream requirements.txt package versions ([#1072](https://github.com/quay/quay/issues/1072))
 -  [#1072](https://github.com/quay/quay/issues/1072)### Dockerfile
- [50d2a827](https://github.com/quay/quay/commit/50d2a82783da906a3a68064fe0b9ab10e956f550): ubi8 requires python38, otherwise installs 3.6 by default (PROJQUAY-3148) ([#1092](https://github.com/quay/quay/issues/1092))
 -  [#1092](https://github.com/quay/quay/issues/1092)- [5267cfe7](https://github.com/quay/quay/commit/5267cfe75189de7df7e61a4daa9ea4570de81cfe): update upstream image to use ubi8 as base (PROJQUAY-3148) ([#1082](https://github.com/quay/quay/issues/1082))
 -  [#1082](https://github.com/quay/quay/issues/1082) -  [#1059](https://github.com/quay/quay/issues/1059)- [085e33be](https://github.com/quay/quay/commit/085e33bed74957fc083a03868bb7bfb1b892dc48): set QUAYRUN in non-standard dockerfiles ([#1013](https://github.com/quay/quay/issues/1013))
 -  [#1013](https://github.com/quay/quay/issues/1013)- [cdc7b61f](https://github.com/quay/quay/commit/cdc7b61f9e1be90d4dbd621810ea7c30a45bb75a): make sure the production dockerfile doesn't pull from dockerhub ([#929](https://github.com/quay/quay/issues/929))
 -  [#929](https://github.com/quay/quay/issues/929)- [da558b0f](https://github.com/quay/quay/commit/da558b0f68228fad28a7cf3b6019f76dc5355e6d): replace golang base image in production dockerfile ([#928](https://github.com/quay/quay/issues/928))
 -  [#928](https://github.com/quay/quay/issues/928)- [139c9abc](https://github.com/quay/quay/commit/139c9abc66c5f60ec9eaf910057afdb28734413b): use separate dockerfile for production deployment ([#927](https://github.com/quay/quay/issues/927))
 -  [#927](https://github.com/quay/quay/issues/927)- [495dd908](https://github.com/quay/quay/commit/495dd9086ea5ac8bb19b0ac175414df1be85aad3): Update symlink in upstream dockerfile (PROJQUAY-2550) ([#889](https://github.com/quay/quay/issues/889))
 -  [#889](https://github.com/quay/quay/issues/889)### Docs
- [8f64efd6](https://github.com/quay/quay/commit/8f64efd6815a76cd27139da5df16983213c71048): consolidate getting started guides (PROJQUAY-2500) ([#884](https://github.com/quay/quay/issues/884))
 -  [#884](https://github.com/quay/quay/issues/884)### Documentation
- [ae0bd06d](https://github.com/quay/quay/commit/ae0bd06d1dc1124a6b64460884d369d0af997f4a): Added instructions to setup dev environment (PROJQUAY-2277) ([#844](https://github.com/quay/quay/issues/844)) ([#844](https://github.com/quay/quay/issues/844))
 -  [#844](https://github.com/quay/quay/issues/844)### Email
- [d81efe2f](https://github.com/quay/quay/commit/d81efe2f3ce545a398a2fba0b4fdc4ac7559376b): fix org recovery link in email (PROJQUAY-2589) ([#903](https://github.com/quay/quay/issues/903))
 -  [#903](https://github.com/quay/quay/issues/903)### Feat
- [fca67e77](https://github.com/quay/quay/commit/fca67e7729d95e8cafee5029ca08f503c803a51e): mypy type annotations (PROJQUAY-740) ([#455](https://github.com/quay/quay/issues/455))
 -  [#455](https://github.com/quay/quay/issues/455)### Fix
- [d3809b2e](https://github.com/quay/quay/commit/d3809b2e36a926721119726070d465c875110085): pin setuptools to version 57 ([#885](https://github.com/quay/quay/issues/885))
 -  [#885](https://github.com/quay/quay/issues/885)### Formatting
- [e4390472](https://github.com/quay/quay/commit/e4390472a47368a42f2fec8c6cef8c428d0ef980): Update code to obey the linter (PROJQUAY-0) ([#1057](https://github.com/quay/quay/issues/1057))
 -  [#1057](https://github.com/quay/quay/issues/1057)### Gc
- [563d04aa](https://github.com/quay/quay/commit/563d04aa00dce607af8671c2a7fa9599b279478c): remove orphaned storage on repository purge (PROJQUAY-2313) ([#961](https://github.com/quay/quay/issues/961))
 -  [#961](https://github.com/quay/quay/issues/961)### Imagemirror
- [0d3ecb13](https://github.com/quay/quay/commit/0d3ecb132e8afe6eb4184948e05a9717759b70c3): Add unsigned registries mirror option (PROJQUAY-3106) ([#1085](https://github.com/quay/quay/issues/1085))
 -  [#1085](https://github.com/quay/quay/issues/1085)### Ipresolver
- [b9557d14](https://github.com/quay/quay/commit/b9557d1486e9a70c0659d8d6d94bae4d053c4eb6): update country mmdb (PROJQUAY-3031) ([#1049](https://github.com/quay/quay/issues/1049))
 -  [#1049](https://github.com/quay/quay/issues/1049)### Ldap
- [c8a7e641](https://github.com/quay/quay/commit/c8a7e6412aecd3a732aaf9681398c2fe1aa1b382): add test for user filter (PROJQUAY-2766) ([#980](https://github.com/quay/quay/issues/980))
 -  [#980](https://github.com/quay/quay/issues/980)### Makefile
- [10e88d29](https://github.com/quay/quay/commit/10e88d29aa518c53da33da800309cdd3310925a4): Add local-dev-build-frontend step (PROJQUAY-2693) ([#933](https://github.com/quay/quay/issues/933))
 -  [#933](https://github.com/quay/quay/issues/933)### Migration
- [08201dea](https://github.com/quay/quay/commit/08201deaec55fc358e3a395b58ab00c9ee408f4c): skip existing mediatype inserts (PROJQUAY-2811) ([#976](https://github.com/quay/quay/issues/976))
 -  [#976](https://github.com/quay/quay/issues/976)- [712b8d74](https://github.com/quay/quay/commit/712b8d749333e9879d15ecf724d335662ddb7af1): configure logging in alembic's env.py (PROJQUAY-2412) ([#875](https://github.com/quay/quay/issues/875))
 -  [#875](https://github.com/quay/quay/issues/875)### Nginx
- [ec7b7610](https://github.com/quay/quay/commit/ec7b7610acff9d585053491eb902032dfc835389): add missing semicolon in template (PROJQUAY-2883) ([#1020](https://github.com/quay/quay/issues/1020))
 -  [#1020](https://github.com/quay/quay/issues/1020)- [03a36256](https://github.com/quay/quay/commit/03a3625650d4e5aa92aafc5325eefc9712443972): rename base http template file ((PROJQUAY-2883) ([#1007](https://github.com/quay/quay/issues/1007))
 -  [#1007](https://github.com/quay/quay/issues/1007)- [1ba53f4f](https://github.com/quay/quay/commit/1ba53f4f09a46586f970735250f8d9570732c736): support client ip through x-forwarded-for header (PROJQUAY-2883) ([#1003](https://github.com/quay/quay/issues/1003))
 -  [#1003](https://github.com/quay/quay/issues/1003)- [630d6f46](https://github.com/quay/quay/commit/630d6f4605124de2a799f17447bab097fff67398): use bigger http/2 chunks for blobs ([#630](https://github.com/quay/quay/issues/630))
 -  [#630](https://github.com/quay/quay/issues/630)### Notification
- [a126ad06](https://github.com/quay/quay/commit/a126ad06d5a48f54188f32d0aa17ad8172aba8fc): check certs exists for webhooks (PROJQUAY-2424) ([#886](https://github.com/quay/quay/issues/886))
 -  [#886](https://github.com/quay/quay/issues/886)### Oci
- [f50f37a3](https://github.com/quay/quay/commit/f50f37a393fa2273234f8ac0aa9f34a03a77a731): Accept the stricter oci layer type used by default in Helm 3.7 (PROJQUAY-2653) ([#922](https://github.com/quay/quay/issues/922))
 -  [#922](https://github.com/quay/quay/issues/922)### Quay
- [162b79ec](https://github.com/quay/quay/commit/162b79ec53b1a38ac4dbbb7e00224a308f7ba3c7): Fixing reclassified CVE ratings source (PROJQUAY-2691) ([#937](https://github.com/quay/quay/issues/937))
 -  [#937](https://github.com/quay/quay/issues/937)### Quay.Io
- [5debec58](https://github.com/quay/quay/commit/5debec58f97ea435ff0826c56202f31bef8c318f): Catching requests from impersonated principals ([#869](https://github.com/quay/quay/issues/869))
 -  [#869](https://github.com/quay/quay/issues/869)### Quay.Io UI
- [20aef6a5](https://github.com/quay/quay/commit/20aef6a589c06d980f24eb866f2328f99b3b2623): Fetching severity from cvss score and removing visibility… ([#887](https://github.com/quay/quay/issues/887))
 -  [#887](https://github.com/quay/quay/issues/887)### Quayio
- [34cf5b92](https://github.com/quay/quay/commit/34cf5b922692ce1d122e9a9f920950e7782a37cd): allow migration to skip adding manifest columns if exists (PROJQUAY-2579) ([#901](https://github.com/quay/quay/issues/901))
 -  [#901](https://github.com/quay/quay/issues/901)### Realtime
- [a058235b](https://github.com/quay/quay/commit/a058235b520ea4c1ec7cb9b9c64d6f41a05fc7d9): decode byte to string before using split (PROJQUAY-3180) ([#1107](https://github.com/quay/quay/issues/1107))
 -  [#1107](https://github.com/quay/quay/issues/1107)### Refactor(Dockerfile)
- [5ad6e0ff](https://github.com/quay/quay/commit/5ad6e0ffa70cd064b8fe47457f8ec805ab7becb9): use pre-built centos 8 stream ([#936](https://github.com/quay/quay/issues/936))
 -  [#936](https://github.com/quay/quay/issues/936)### Registry
- [32322bc1](https://github.com/quay/quay/commit/32322bc1f6bfc919c4366d6063bffb96be491d5a): update blob mount behaviour when from parameter is missing (PROJQUAY-2570) ([#899](https://github.com/quay/quay/issues/899))
 -  [#899](https://github.com/quay/quay/issues/899)### Requirements
- [5c11e7a6](https://github.com/quay/quay/commit/5c11e7a6a64927e46d9c1d7eea68e5c5ab5db2ae): bump cryptography package version ([#939](https://github.com/quay/quay/issues/939))
 -  [#939](https://github.com/quay/quay/issues/939)### Requirements-Osbs
- [12705e49](https://github.com/quay/quay/commit/12705e49c81dd2b932539c1231b47cd80739c689): upgrade cryptography package ([#943](https://github.com/quay/quay/issues/943))
 -  [#943](https://github.com/quay/quay/issues/943)### Requirements-Osbs.Txt
- [f3e016f4](https://github.com/quay/quay/commit/f3e016f4f984286edb3cc0d8a50a5b80dc92e897): remove ipython and related deps ([#1069](https://github.com/quay/quay/issues/1069))
 -  [#1069](https://github.com/quay/quay/issues/1069)### Requirements.Txt
- [897e7e39](https://github.com/quay/quay/commit/897e7e3913c0c18436a41b71f582817e8a273187): remove unused dependencies ([#948](https://github.com/quay/quay/issues/948))
 -  [#948](https://github.com/quay/quay/issues/948)### Revert "Schema1
- [58b06572](https://github.com/quay/quay/commit/58b065725527ee84fdae3fdf9a7206a860101c68): Permit signed schema1 manifests during conversion (PROJQUAY-PROJQUAY-3285) ([#1146](https://github.com/quay/quay/issues/1146))" ([#1150](https://github.com/quay/quay/issues/1150))
 -  [#1146](https://github.com/quay/quay/issues/1146) -  [#1150](https://github.com/quay/quay/issues/1150)### Schema1
- [b5bd74bf](https://github.com/quay/quay/commit/b5bd74bf051e5de81fede6b386b3fbd178d7b8a8): Permit signed schema1 manifests during conversion (PROJQUAY-PROJQUAY-3285) ([#1146](https://github.com/quay/quay/issues/1146))
 -  [#1146](https://github.com/quay/quay/issues/1146)### Secscan
- [7162be37](https://github.com/quay/quay/commit/7162be3791db1ef122a579e5546857dbb55314f3): make batch_size configurable (PROJQUAY-3287) ([#1156](https://github.com/quay/quay/issues/1156))
 -  [#1156](https://github.com/quay/quay/issues/1156)- [369ee78a](https://github.com/quay/quay/commit/369ee78a2cec2024c0ee31f2b92190d3d69c9286): clairv2 - fix datatype bug (PROJQUAY-3279) ([#1138](https://github.com/quay/quay/issues/1138))
 -  [#1138](https://github.com/quay/quay/issues/1138)- [b32ca314](https://github.com/quay/quay/commit/b32ca3142a7255d91d70b267fcaee078ed54bc56): ClairV2 datatype compatibility (PROJQUAY-3279) ([#1133](https://github.com/quay/quay/issues/1133))
 -  [#1133](https://github.com/quay/quay/issues/1133)- [26eb7ff9](https://github.com/quay/quay/commit/26eb7ff9827fda97f775104a3b0d6a04c63ea860): Don't save secscan result if returned state is unknown (PROJQUAY-2939) ([#1047](https://github.com/quay/quay/issues/1047))
 -  [#1047](https://github.com/quay/quay/issues/1047)- [9f16b324](https://github.com/quay/quay/commit/9f16b3247e1fdd2a97f773657f722067388a8761): fix secscan api ApiRequestFailure test (PROJQUAY-2563) ([#896](https://github.com/quay/quay/issues/896))
 -  [#896](https://github.com/quay/quay/issues/896)- [694fa2ac](https://github.com/quay/quay/commit/694fa2acafbf50d09b1cccb54dcdd3c4aec3c113): continue iterating after failure (PROJQUAY-2563) ([#892](https://github.com/quay/quay/issues/892))
 -  [#892](https://github.com/quay/quay/issues/892)### Sescan
- [4db59990](https://github.com/quay/quay/commit/4db59990372e59c1de436d3fa7f3715e90887e0c): prioritize scanning new pushes (PROJQUAY-3287) ([#1147](https://github.com/quay/quay/issues/1147))
 -  [#1147](https://github.com/quay/quay/issues/1147)### Setup
- [fd190ad9](https://github.com/quay/quay/commit/fd190ad98468bbeb911bc2327faec14e84764265): Export Quay modules (PROJQUAY-3181) ([#1108](https://github.com/quay/quay/issues/1108))
 -  [#1108](https://github.com/quay/quay/issues/1108)### Static
- [a13baef9](https://github.com/quay/quay/commit/a13baef9cc15c68f41fd24e0f21a05979f5b4fbd): vendor webfonts dir ([#1016](https://github.com/quay/quay/issues/1016))
 -  [#1016](https://github.com/quay/quay/issues/1016)- [ab499e8f](https://github.com/quay/quay/commit/ab499e8f2cc72b90d07890bd8b1a5513594ef280): vendor external libraries ([#1014](https://github.com/quay/quay/issues/1014))
 -  [#1014](https://github.com/quay/quay/issues/1014)### Storage
- [13a9f8f4](https://github.com/quay/quay/commit/13a9f8f44e59d512c4f01e5cc94a03bd8fca3d10): Add cn-northwest-1 to s3_region northwest (PROJQUAY-3082) ([#1137](https://github.com/quay/quay/issues/1137))
 -  [#1137](https://github.com/quay/quay/issues/1137)- [ca17eb43](https://github.com/quay/quay/commit/ca17eb43121e4d8ce85bc470e8f90c8feb2551e5): handle cn-north-1 region (PROJQUAY-3082) ([#1129](https://github.com/quay/quay/issues/1129))
 -  [#1129](https://github.com/quay/quay/issues/1129)- [f6f7b05a](https://github.com/quay/quay/commit/f6f7b05a060edd216354e632854c6ee0f545a768): allow configuration of storage region for cloud storage (PROJQUAY-3082) ([#1081](https://github.com/quay/quay/issues/1081))
 -  [#1081](https://github.com/quay/quay/issues/1081)### Teams
- [639833cc](https://github.com/quay/quay/commit/639833cc15304ec184f51843e18e2337dc29059f): admin team deletion (PROJQUAY-2080) ([#1077](https://github.com/quay/quay/issues/1077))
 -  [#1077](https://github.com/quay/quay/issues/1077)### Trigger_analyzer
- [861c247f](https://github.com/quay/quay/commit/861c247faf75e60a8ffde0ee58e0148abbb5efb2): fix confusing print (PROJQUAY-1995) ([#1073](https://github.com/quay/quay/issues/1073))
 -  [#1073](https://github.com/quay/quay/issues/1073)### Ui
- [033c1aaf](https://github.com/quay/quay/commit/033c1aafa1d1364a41a0861f16fa1769315672d6): display manifest list manifest sizes (PROJQUAY-3196) ([#1115](https://github.com/quay/quay/issues/1115))
 -  [#1115](https://github.com/quay/quay/issues/1115)- [e91ec644](https://github.com/quay/quay/commit/e91ec644fa9581f55a583c7d03a68a9f957c9f03): Depricate getImageCommand in security UI (PROJQUAY-3284) ([#1144](https://github.com/quay/quay/issues/1144))
 -  [#1144](https://github.com/quay/quay/issues/1144)- [374e957b](https://github.com/quay/quay/commit/374e957bd93d5b6bbb6ddd2080aaa4d67fcdfa74): fix csrf issue when login in with SSO on mobile (PROJQUAY-2340) ([#906](https://github.com/quay/quay/issues/906))
 -  [#906](https://github.com/quay/quay/issues/906)- [bf81bd9b](https://github.com/quay/quay/commit/bf81bd9bae44f6ff870d207026f44010e1b2d229): change angular routing order for repo paths (PROJQUAY-2325) ([#872](https://github.com/quay/quay/issues/872))
 -  [#872](https://github.com/quay/quay/issues/872)### Util
- [42d1cdb4](https://github.com/quay/quay/commit/42d1cdb4a16e961a23b4af9126c96798ecabb7fa): update aws-ip-ranges.json ([#1143](https://github.com/quay/quay/issues/1143))
 -  [#1143](https://github.com/quay/quay/issues/1143)### Util/Ipresolver
- [9ee1c580](https://github.com/quay/quay/commit/9ee1c580599eb74b83e16fc34f1fea369e2d0d66): manually add aws-ip-ranges.json ([#1065](https://github.com/quay/quay/issues/1065))
 -  [#1065](https://github.com/quay/quay/issues/1065)
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

[Unreleased]: https://github.com/quay/quay/compare/v3.6.4...HEAD
[v3.6.4]: https://github.com/quay/quay/compare/v3.6.2...v3.6.4
[v3.6.2]: https://github.com/quay/quay/compare/v3.6.0-alpha.9...v3.6.2
[v3.6.0-alpha.9]: https://github.com/quay/quay/compare/v3.6.0-alpha.8...v3.6.0-alpha.9
[v3.6.0-alpha.8]: https://github.com/quay/quay/compare/v3.6.0-alpha.7...v3.6.0-alpha.8
[v3.6.0-alpha.7]: https://github.com/quay/quay/compare/v3.6.0-alpha.6...v3.6.0-alpha.7
[v3.6.0-alpha.6]: https://github.com/quay/quay/compare/v3.6.0-alpha.5...v3.6.0-alpha.6
[v3.6.0-alpha.5]: https://github.com/quay/quay/compare/v3.6.0-alpha.4...v3.6.0-alpha.5
[v3.6.0-alpha.4]: https://github.com/quay/quay/compare/v3.6.0-alpha.3...v3.6.0-alpha.4
## Historical Changelog
[CHANGELOG.md](https://github.com/quay/quay/blob/96b17b8338fb10ca2ed12e9bc920dcbba148289c/CHANGELOG.md)