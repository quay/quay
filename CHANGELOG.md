### v3.6.0

**Release Notes**
(Red Hat Customer Portal)[https://access.redhat.com/documentation/en-us/red_hat_quay/3.6/html/red_hat_quay_release_notes/index]


## Red Hat Quay Release Notes
(Red Hat Customer Portal)[https://access.redhat.com/documentation/en-us/red_hat_quay/3.5/html/red_hat_quay_release_notes/index]


<a name="v3.6.0-alpha.9"></a>
## [v3.6.0-alpha.9] - 2021-04-21
### Cache
- [1180ea99](https://github.com/quay/quay/commit/1180ea99fae3787eccfa53801af6199d3af3bcac): remove GlobalLock from redis model cache (PROJQUAY-1902) ([#755](https://github.com/quay/quay/issues/755))
 -  [#755](https://github.com/quay/quay/issues/755)- [780685c4](https://github.com/quay/quay/commit/780685c490097ce7cf9515e0642505a45817df6a): add Redis model cache implementation (PROJQUAY-788) ([#444](https://github.com/quay/quay/issues/444))
 -  [#444](https://github.com/quay/quay/issues/444)### Chore
- [0ffe9cee](https://github.com/quay/quay/commit/0ffe9ceecac456ab2b722459aa5aebe70c902fe9): correct chnglog params (PROJQUAY-1486) ([#762](https://github.com/quay/quay/issues/762))
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

[Unreleased]: https://github.com/quay/quay/compare/v3.6.0-alpha.9...HEAD
[v3.6.0-alpha.9]: https://github.com/quay/quay/compare/v3.6.0-alpha.8...v3.6.0-alpha.9
[v3.6.0-alpha.8]: https://github.com/quay/quay/compare/v3.6.0-alpha.7...v3.6.0-alpha.8
[v3.6.0-alpha.7]: https://github.com/quay/quay/compare/v3.6.0-alpha.6...v3.6.0-alpha.7
[v3.6.0-alpha.6]: https://github.com/quay/quay/compare/v3.6.0-alpha.5...v3.6.0-alpha.6
[v3.6.0-alpha.5]: https://github.com/quay/quay/compare/v3.6.0-alpha.4...v3.6.0-alpha.5
[v3.6.0-alpha.4]: https://github.com/quay/quay/compare/v3.6.0-alpha.3...v3.6.0-alpha.4
## Historical Changelog
[CHANGELOG.md](https://github.com/quay/quay/blob/96b17b8338fb10ca2ed12e9bc920dcbba148289c/CHANGELOG.md)