## Red Hat Quay Release Notes

[Red Hat Customer Portal](https://access.redhat.com/documentation/en-us/red_hat_quay/3.7/html/red_hat_quay_release_notes/index)


<a name="v3.8.11"></a>
## [v3.8.11] - 2023-07-13
### Chore
- [9a562abe](https://github.com/quay/quay/commit/9a562abeca116f5c38a7d343b84bc3eac44779f3): Use buildx v0.11.0-rc2 ([#1960](https://github.com/quay/quay/issues/1960)) ([#2013](https://github.com/quay/quay/issues/2013))
### [Redhat-3.8] Pagination
- [7abedb68](https://github.com/quay/quay/commit/7abedb68a4e46d773085d32938e3fac7e340f9e6): Fixing paginate for /api/v1/superuser/logs API (PROJQUAY-5360) ([#2010](https://github.com/quay/quay/issues/2010))

<a name="v3.8.10"></a>
## [v3.8.10] - 2023-06-23
### Chore
- [d1e2d0f1](https://github.com/quay/quay/commit/d1e2d0f12925464fcd4b7b249963d2372720f53f): v3.8.10 changelog bump (PROJQUAY-5677) ([#1991](https://github.com/quay/quay/issues/1991))
### Db
- [a7cfd6ee](https://github.com/quay/quay/commit/a7cfd6eeeed5f8081beb4251745b9057de8f9a2a): handle readonly mode when updating repo size cache (PROJQUAY-4854) ([#1930](https://github.com/quay/quay/issues/1930))

<a name="v3.8.9"></a>
## [v3.8.9] - 2023-06-07
### Chore
- [45487213](https://github.com/quay/quay/commit/45487213a2a55dc29eca624663dc3c1bd3ebf1c7): v3.8.9 changelog bump (PROJQUAY-5607) ([#1946](https://github.com/quay/quay/issues/1946))
- [3747f70e](https://github.com/quay/quay/commit/3747f70e52259b4b415aaff87b40767c84d4e3a0): update ppc64le builder ([#1911](https://github.com/quay/quay/issues/1911))
- [b80166b0](https://github.com/quay/quay/commit/b80166b02352e035e3b90c6fd69b586a703d2f94): Use external builders ([#1910](https://github.com/quay/quay/issues/1910))
### Proxy
- [47d50900](https://github.com/quay/quay/commit/47d50900bdfd38c76f2f9f2ce5fbfb8e45ae6755): Allow anonymous pulls from registries (PROJQUAY-5273) ([#1908](https://github.com/quay/quay/issues/1908))
### Superuser
- [540cf0f8](https://github.com/quay/quay/commit/540cf0f88997e81919b4438c426c0e64fd2c71be): paginate user's list (PROJQUAY-4297) ([#1881](https://github.com/quay/quay/issues/1881)) ([#1909](https://github.com/quay/quay/issues/1909))
### [Redhat-3.8] Superuser
- [9c198c69](https://github.com/quay/quay/commit/9c198c6981c3c67a1a9604195ebda363a8b41dd8): paginating superuser organization list (PROJQUAY-4297) ([#1896](https://github.com/quay/quay/issues/1896))

<a name="v3.8.8"></a>
## [v3.8.8] - 2023-05-17
### Chore
- [9c27dadc](https://github.com/quay/quay/commit/9c27dadc754587157a13d45823eb6a8df207ad3c): v3.8.8 changelog bump (PROJQUAY-5514) ([#1889](https://github.com/quay/quay/issues/1889))
- [517d3b35](https://github.com/quay/quay/commit/517d3b35a1e6dbfcb56b57e5d5c5ea4710216dc3): Remove cachito magic for PyPDF2 ([#1885](https://github.com/quay/quay/issues/1885))
### Storagereplication
- [1cc45a7b](https://github.com/quay/quay/commit/1cc45a7b325d65b5f9738e4e17491b236bb1a0cb): add retry logic without exhausting queue retries (PROJQUAY-4793) ([#1884](https://github.com/quay/quay/issues/1884))

<a name="v3.8.7"></a>
## [v3.8.7] - 2023-04-26
### Chore
- [d60d6e42](https://github.com/quay/quay/commit/d60d6e42ab6fab375574cbcdb6ef8d19158f6e4e): v3.8.7 changelog bump (PROJQUAY-5352) ([#1836](https://github.com/quay/quay/issues/1836))
- [3db02218](https://github.com/quay/quay/commit/3db022180a41138a7f84994830064640f2846564): Ensure use of HTTP 1.1 when proxying storage (PROJQUAY-5140) We were not enforcing the use of `HTTP 1.1` when storage proxy was concerned. This causes problems in certain complex scenarios. ([#1828](https://github.com/quay/quay/issues/1828))

<a name="v3.8.6"></a>
## [v3.8.6] - 2023-04-12
### Build(Deps)
- [f218831c](https://github.com/quay/quay/commit/f218831c5162f5159b26e7787cf65f0d617bb90d): bump certifi from 2019.11.28 to 2022.12.7 ([#1823](https://github.com/quay/quay/issues/1823))
### Chore
- [12b0bc23](https://github.com/quay/quay/commit/12b0bc236bea594024427d2aa66756bc8484fb8b): v3.8.6 changelog bump (PROJQUAY-5279) ([#1824](https://github.com/quay/quay/issues/1824))
- [7761140e](https://github.com/quay/quay/commit/7761140e24a2bc537567f48f2b8e63d88d514e30): Pin distribution-spec conformance tests ([#1816](https://github.com/quay/quay/issues/1816))
### Storagereplication
- [3809d7ff](https://github.com/quay/quay/commit/3809d7ff428d8342a4acad55a7fef46ff04d8a83): sleep on unexpected exception for retry (PROJQUAY-4792) ([#1810](https://github.com/quay/quay/issues/1810))

<a name="v3.8.5"></a>
## [v3.8.5] - 2023-03-21
### Build(Deps)
- [c38bbef9](https://github.com/quay/quay/commit/c38bbef98cb6338f784130f1ee6ffdaa701138bd): bump setuptools from 63.4.0 to 65.5.1 ([#1797](https://github.com/quay/quay/issues/1797))
- [e4a562b5](https://github.com/quay/quay/commit/e4a562b58bc111bcf4a6faca0511f97d1a96a84d): reduce CVEs in dependencies and runtime environment (PROJQUAY-4777) ([#1644](https://github.com/quay/quay/issues/1644)) ([#1795](https://github.com/quay/quay/issues/1795))
### Chore
- [9ca88389](https://github.com/quay/quay/commit/9ca883899ebdf7af66957b542b0fcf6f483cd24c): v3.8.5 changelog bump (PROJQUAY-5228) ([#1805](https://github.com/quay/quay/issues/1805))
- [5695cbf9](https://github.com/quay/quay/commit/5695cbf9dd28d5bf23a34209394e1ce54eecb697): Downgrade cryptography to 3.3.2 (PROJQUAY-5120) ([#1804](https://github.com/quay/quay/issues/1804))
- [5af451df](https://github.com/quay/quay/commit/5af451df5af503201e1c71a011a14e98cfead890): Add setuptools-rust as a build dependency ([#1798](https://github.com/quay/quay/issues/1798))
- [7e2eab2e](https://github.com/quay/quay/commit/7e2eab2e9a6c8e558c232b1aa7bad09ccfd57eeb): backport requirements.txt changes (PROJQUAY-4777) ([#1781](https://github.com/quay/quay/issues/1781))
### [Redhat-3.8] Chore
- [54799d69](https://github.com/quay/quay/commit/54799d6963e6ca4d22d62561ec9effed8b470b30): Bump pyOpenSSL and cryptography (PROJQUAY-5120) ([#1796](https://github.com/quay/quay/issues/1796))
### [Redhat-3.8] Security
- [3b38e859](https://github.com/quay/quay/commit/3b38e85935d1142e0af15bdc35f76a920d4e76cc): Change error messages in UI during LDAP login (PROJQUAY-4845) ([#1801](https://github.com/quay/quay/issues/1801))

<a name="v3.8.4"></a>
## [v3.8.4] - 2023-03-10
### Chore
- [abc58174](https://github.com/quay/quay/commit/abc58174e562709245069c12b0b6df4e8e10507d): v3.8.4 changelog bump (PROJQUAY-5148) ([#1780](https://github.com/quay/quay/issues/1780))
- [4b29cd5b](https://github.com/quay/quay/commit/4b29cd5b42dd8bcad4729bbc9b5db05399b2ff58): Bump Authlib (PROJQUAY-5120) ([#1776](https://github.com/quay/quay/issues/1776))
### Healthcheck
- [9858a0d8](https://github.com/quay/quay/commit/9858a0d86d889e6335fa75816344b2c65fc0a608): fix invalid Exception attribute (PROJQUAY-5047) ([#1783](https://github.com/quay/quay/issues/1783))
### Permissions
- [0caa7786](https://github.com/quay/quay/commit/0caa7786ec529fc01bcfa3fe9f3672a75906386e): lazy-load superuser permissions (PROJQUAY-5117) ([#1779](https://github.com/quay/quay/issues/1779))
### Storage
- [1c191a2f](https://github.com/quay/quay/commit/1c191a2f106edc06a7ed34d60b333e75097886a0): add option to validate all configured storages (PROJQUAY-5074) ([#1768](https://github.com/quay/quay/issues/1768))
### Tox
- [cd2cc5c3](https://github.com/quay/quay/commit/cd2cc5c37ae2fb42b3c7fa8bb15e8952a1e78fbd): allow /bin/sh (PROJQUAY-5092) ([#1769](https://github.com/quay/quay/issues/1769))

<a name="v3.8.3"></a>
## [v3.8.3] - 2023-02-28
### Chore
- [02caa532](https://github.com/quay/quay/commit/02caa532c7e90f49cddba218426187e1ae1faef0): v3.8.3 changelog bump (PROJQUAY-5062) ([#1766](https://github.com/quay/quay/issues/1766))

<a name="v3.8.2"></a>
## [v3.8.2] - 2023-02-07
### Build(Deps)
- [53ca62b8](https://github.com/quay/quay/commit/53ca62b867d65b0c854173a79eb0caee5f35a2a2): bump oauthlib from 3.2.1 to 3.2.2 ([#1742](https://github.com/quay/quay/issues/1742))
- [1ab53c38](https://github.com/quay/quay/commit/1ab53c38512cb1dc3ef72000ff17289d65f909ef): bump pillow from 9.0.1 to 9.3.0 ([#1739](https://github.com/quay/quay/issues/1739))
### Chore
- [7547f6f5](https://github.com/quay/quay/commit/7547f6f5b686bc582f40dd2f5428c88075fa2262): Remove appr dependencies (PROJQUAY-4992) ([#1743](https://github.com/quay/quay/issues/1743))
- [ce694e04](https://github.com/quay/quay/commit/ce694e04eacbe03db4bf54a445007b55cc70a5a8): remove deprecated appr code (PROJQUAY-4992) ([#1729](https://github.com/quay/quay/issues/1729))
### Config
- [08fae2ee](https://github.com/quay/quay/commit/08fae2eeb23b68ed7d23cc97562644845fb52b7b): clean upload folder by default (PROJQUAY-4395) ([#1741](https://github.com/quay/quay/issues/1741))
### Logs
- [8c562906](https://github.com/quay/quay/commit/8c56290617f4075d79bf8455833d76d909b4ff14): Add repository information for build audit logs (PROJQUAY-4726) ([#1720](https://github.com/quay/quay/issues/1720))

<a name="v3.8.1"></a>
## [v3.8.1] - 2023-01-24
### Chore
- [136e9734](https://github.com/quay/quay/commit/136e973499fc9d9714367dcdfec493e7b45101c2): v3.8.1 changelog bump (PROJQUAY-4716) ([#1723](https://github.com/quay/quay/issues/1723))
### Chore: V3.7.11 Changelog Bump (Https
- [8238c755](https://github.com/quay/quay/commit/8238c75504590de4a33f6ecbf8c663139d837a07): //issues.redhat.com/browse/PROJQUAY-4790) ([#1722](https://github.com/quay/quay/issues/1722))
### Cors
- [8f4cae04](https://github.com/quay/quay/commit/8f4cae0449af54699b557025fa43227f5b9012c3): Adding missing method type (PROJQUAY-4800) ([#1660](https://github.com/quay/quay/issues/1660))
### Logs
- [c722d6df](https://github.com/quay/quay/commit/c722d6df81c94c3605444f0962ec9cbee1affb67): audit logs on manual build triggers and build cancellations (PROJQUAY-4726) ([#1701](https://github.com/quay/quay/issues/1701))
### Nginx
- [006779bd](https://github.com/quay/quay/commit/006779bdb23e2a10c8e258021e33040e2db387d1): Minor update to fix toggling issue on Safari (PROJQUAY-4527) ([#1673](https://github.com/quay/quay/issues/1673))
### Oci/Index.Py
- [d7371d1e](https://github.com/quay/quay/commit/d7371d1e6919cbe932e0bd4ae5534252857516cd): support docker schema2 sub-manifest types ([#1661](https://github.com/quay/quay/issues/1661))
### Superusers
- [68ec0579](https://github.com/quay/quay/commit/68ec05790fd7b1b6521221f636a82b2e89386a8b): gives superusers access to team invite api (PROJQUAY-4765) ([#1702](https://github.com/quay/quay/issues/1702))
### UI
- [013f96fd](https://github.com/quay/quay/commit/013f96fd59dc1ebf0f6cc0ac7d538cf4e4e2379d): Fix redirection to user/org page (PROJQUAY-4667) ([#1659](https://github.com/quay/quay/issues/1659))
### Ui
- [3a3daeb5](https://github.com/quay/quay/commit/3a3daeb5d7c61502eb591c5a4f76caec5ff86227): Repository settings feature flag (PROJQUAY-4565) ([#1689](https://github.com/quay/quay/issues/1689))
- [95f3064c](https://github.com/quay/quay/commit/95f3064cd5b66b9c408f07c8297514279de41a24): Remove add_analytics script from Dockerfile (PROJQUAY-4582) ([#1672](https://github.com/quay/quay/issues/1672))

<a name="v3.8.0"></a>
## [v3.8.0] - 2022-11-26
### Api
- [2b3c3cc5](https://github.com/quay/quay/commit/2b3c3cc58482b94e83ad4b5483a5a4de7bdee6b4): feature to limit org creation to superusers (PROJQUAY-1245) ([#1516](https://github.com/quay/quay/issues/1516))
- [aefddd36](https://github.com/quay/quay/commit/aefddd36dd0540709f391a86485a8afb2a57e85a): add OPTIONS method to /config request (PROJQUAY-4276) ([#1476](https://github.com/quay/quay/issues/1476))
- [d37dd766](https://github.com/quay/quay/commit/d37dd766accdaa8c2af5c465af2fd6f2948ed990): fix CORS headers, use concat instead of extend (PROJQUAY-4163) ([#1445](https://github.com/quay/quay/issues/1445))
- [871c43ea](https://github.com/quay/quay/commit/871c43eaf37ea44da13308e06b2e2f9c543fc5dd): handle missing tag on DELETE tag api ([#1444](https://github.com/quay/quay/issues/1444))
- [bf99e718](https://github.com/quay/quay/commit/bf99e718513b41e67ee2963e220d93e59e4acac5): Update werkzeug to 1.0.0 and add valid CORS methods (PROJQUAY-4163) ([#1443](https://github.com/quay/quay/issues/1443))
### Arch
- [0f0cc408](https://github.com/quay/quay/commit/0f0cc408d0120abe93541d1554e74312d0592c49): Map aarch64 to arm64 in ARCH variable ([#1606](https://github.com/quay/quay/issues/1606))
### Auth
- [734f7f9d](https://github.com/quay/quay/commit/734f7f9da388a404d9fe45f60ee51d5a19f16b13): Adding wraps to user namespace decorator (PROJQUAY-4694) ([#1608](https://github.com/quay/quay/issues/1608))
- [3ae26f5e](https://github.com/quay/quay/commit/3ae26f5e983ed3b4e62a4d57526940ca92c33551): Speed up permissions loading (PROJQUAY-4004) ([#1582](https://github.com/quay/quay/issues/1582))
- [6ed0bcde](https://github.com/quay/quay/commit/6ed0bcdedc9a0cb4a84197006602ba39c7f965ec): allow rs384 in jwt (PROJQUAY-4148) ([#1449](https://github.com/quay/quay/issues/1449))
### Billing
- [78896aa0](https://github.com/quay/quay/commit/78896aa0ceaa244e41988f5991c677a29e4ce263): fix new private repo count (PROJQUAY-4208) ([#1463](https://github.com/quay/quay/issues/1463))
- [17778979](https://github.com/quay/quay/commit/177789798139779d6e46032f595ddc2adfcbaf0f): add new larger stripe plan (PROJQUAY-4208) ([#1462](https://github.com/quay/quay/issues/1462))
### Bug
- [ee5ff714](https://github.com/quay/quay/commit/ee5ff7141f1096a2d6c79020df23791c8cd64e8a): Increase column size in logentry3 table (PROJQUAY-4305) ([#1510](https://github.com/quay/quay/issues/1510))
- [9209cf75](https://github.com/quay/quay/commit/9209cf7596d21719d4797c0caf8677cbc2347a1f): Fix schema discovery on basic auth (PROJQUAY-4362) ([#1498](https://github.com/quay/quay/issues/1498))
### Build(Deps)
- [9a1de19f](https://github.com/quay/quay/commit/9a1de19f975800e2a4bbe384d87b8ceab416aa7e): bump angular and [@types](https://github.com/types)/angular ([#1451](https://github.com/quay/quay/issues/1451))
- [0c62c0ee](https://github.com/quay/quay/commit/0c62c0ee02920408fc8fa57b3580fef48a9d4ccf): bump terser from 4.3.4 to 4.8.1 ([#1452](https://github.com/quay/quay/issues/1452))
- [0f2ebdaf](https://github.com/quay/quay/commit/0f2ebdafc58867af6fac9168ed6348178ac63d45): bump moment from 2.29.2 to 2.29.4 ([#1442](https://github.com/quay/quay/issues/1442))
### Builders
- [b8d3e174](https://github.com/quay/quay/commit/b8d3e17406c546ca60789ce41c11f12e49dea9cb): Add cacert's to build agent (PROJQUAY-3819) ([#1398](https://github.com/quay/quay/issues/1398))
- [d11d45f2](https://github.com/quay/quay/commit/d11d45f208bc3c78f852bab0cb7686aa6f125c62): Send notifications on build completion (PROJQUAY-3614) ([#1346](https://github.com/quay/quay/issues/1346))
- [1d2e55b6](https://github.com/quay/quay/commit/1d2e55b63d906d949de792fd5b9481a6dd42568b): Set imagePullPolicy to always (PROJQUAY-3507) ([#1330](https://github.com/quay/quay/issues/1330))
- [3a63fd71](https://github.com/quay/quay/commit/3a63fd718788b4a0f733c1a29b8e0992083d0884): Add dnsPolicy option (PROJQUAY-3755) ([#1305](https://github.com/quay/quay/issues/1305))
### Buildman
- [e3b170ea](https://github.com/quay/quay/commit/e3b170ea3f35920afee9c2c2d32c8dbf40c9bd9d): fix type when getting ec2 ami ([#1328](https://github.com/quay/quay/issues/1328))
### Bump
- [b21400b9](https://github.com/quay/quay/commit/b21400b90d46ff1d6a989c2b3008769420bbd608): Bump to redeploy Quay pods to reflect new endpoint (PROJQUAY-2056) ([#1327](https://github.com/quay/quay/issues/1327))
### CI
- [e566560f](https://github.com/quay/quay/commit/e566560fee3ab584e9eccb612925d830facbb142): Commenting arm docker build (PROJQUAY-0000) ([#1522](https://github.com/quay/quay/issues/1522))
### Chore
- [f4828fde](https://github.com/quay/quay/commit/f4828fde5cecac46f898d88037b41a1e6e2bee6b): Add georeplication variable check (PROJQUAY-4363) ([#1499](https://github.com/quay/quay/issues/1499))
- [8e1fba48](https://github.com/quay/quay/commit/8e1fba48420087eadaf57ed6892780e44a767cdf): Fix startup script ([#1402](https://github.com/quay/quay/issues/1402))
- [cf52f5e3](https://github.com/quay/quay/commit/cf52f5e3716009e87d251d71a7057343b81d33e6): Use Python 3.9 ([#1382](https://github.com/quay/quay/issues/1382))
- [5eaf0584](https://github.com/quay/quay/commit/5eaf0584dbc87d7eeb135de63bbea4c7d40a1fa0): Run mypy as CI job ([#1363](https://github.com/quay/quay/issues/1363))
- [13f8e0c4](https://github.com/quay/quay/commit/13f8e0c4b3ac6b48503cadb8c191832f499e61c0): Rebuild quay image if requirements.txt is changed ([#1342](https://github.com/quay/quay/issues/1342))
### Chore: V3.6.8 Changelog Bump (Https
- [f69b1309](https://github.com/quay/quay/commit/f69b1309a01d3e4d73dddc2d829e7e188b6bb04e): //issues.redhat.com/browse/PROJQUAY-3990) ([#1419](https://github.com/quay/quay/issues/1419))
### Chore: V3.6.9 Changelog Bump (Https
- [b44df459](https://github.com/quay/quay/commit/b44df459aaa511a5e44f8b427e9b6a8feda501ee): //issues.redhat.com/browse/PROJQUAY-4192) ([#1466](https://github.com/quay/quay/issues/1466))
### Chore: V3.7.0 Changelog Bump (Https
- [e85372d0](https://github.com/quay/quay/commit/e85372d00586217dd8ec1f4b808c6d2534dea28e): //issues.redhat.com/browse/PROJQUAY-2411) ([#1337](https://github.com/quay/quay/issues/1337))
### Chore: V3.7.1 Changelog Bump (Https
- [e76db133](https://github.com/quay/quay/commit/e76db133fcd62b07f6c99c420410ef9eca12dd73): //issues.redhat.com/browse/PROJQUAY-3836) ([#1372](https://github.com/quay/quay/issues/1372))
### Chore: V3.7.10 Changelog Bump (Https
- [9f3c1699](https://github.com/quay/quay/commit/9f3c1699bef1a489c2817babd618056a792405c2): //issues.redhat.com/browse/PROJQUAY-4627) ([#1593](https://github.com/quay/quay/issues/1593))
### Chore: V3.7.3 Changelog Bump (Https
- [a55c63e7](https://github.com/quay/quay/commit/a55c63e7117438c483c78cd17c60e0491ab498cd): //issues.redhat.com/browse/PROJQUAY-3989) ([#1420](https://github.com/quay/quay/issues/1420))
### Chore: V3.7.4 Changelog Bump (Https
- [a5279983](https://github.com/quay/quay/commit/a52799830235ae67162e35e8cc6ddcca999343a2): //issues.redhat.com/browse/PROJQUAY-4050) ([#1446](https://github.com/quay/quay/issues/1446))
### Chore: V3.7.5 Changelog Bump (Https
- [cc26275d](https://github.com/quay/quay/commit/cc26275d999ebac469c1cc80211ea3f3fd3c7652): //issues.redhat.com/browse/PROJQUAY-4172) ([#1458](https://github.com/quay/quay/issues/1458))
### Chore: V3.7.6 Changelog Bump (Https
- [e1a14f5c](https://github.com/quay/quay/commit/e1a14f5c53b18f8db967131572c43b7588ad51aa): //issues.redhat.com/browse/PROJQUAY-4237) ([#1480](https://github.com/quay/quay/issues/1480))
### Chore: V3.7.7 Changelog Bump (Https
- [fcdd0e12](https://github.com/quay/quay/commit/fcdd0e12bf299bcf362799d1ffe8051ceb90ce71): //issues.redhat.com/browse/PROJQUAY-4286) ([#1508](https://github.com/quay/quay/issues/1508))
### Chore: V3.7.8 Changelog Bump (Https
- [292d33f2](https://github.com/quay/quay/commit/292d33f2922df5e3cdae72d839a537c3d7fa5df6): //issues.redhat.com/browse/PROJQUAY-4385) ([#1517](https://github.com/quay/quay/issues/1517))
### Chore: V3.7.9 Changelog Bump (Https
- [6438a8c6](https://github.com/quay/quay/commit/6438a8c64938d51212904817a296a57f5c3cd536): //issues.redhat.com/browse/PROJQUAY-4478) ([#1570](https://github.com/quay/quay/issues/1570))
### Ci
- [07c8a75f](https://github.com/quay/quay/commit/07c8a75fa18ab4da5abad2ede24347419656c793): Check arm64 builds in CI (PROJQUAY-4038) ([#1431](https://github.com/quay/quay/issues/1431))
### Cleanup
- [eb2cda16](https://github.com/quay/quay/commit/eb2cda160ed10204f1228e7f7917339710c3642f): Remove old validation code (PROJQUAY-4606) ([#1586](https://github.com/quay/quay/issues/1586))
### Conf/Nginx
- [f45c68eb](https://github.com/quay/quay/commit/f45c68ebf2635eeadbaeaf11ce5df9e215ae62d1): mark beginning of string in oauth location match ([#1550](https://github.com/quay/quay/issues/1550))
### Dev
- [d3cc640f](https://github.com/quay/quay/commit/d3cc640fef64d673ae0c8ff9aef84aad13562c45): Update Clair for dev (PROJQUAY-4461) ([#1528](https://github.com/quay/quay/issues/1528))
- [04af141a](https://github.com/quay/quay/commit/04af141a49fa231157d91f20f04ab498e307228d): Add pre-commit script to run black (PROJQUAY-4039) ([#1432](https://github.com/quay/quay/issues/1432))
### Doc 
- [34cd7d09](https://github.com/quay/quay/commit/34cd7d09188cabe90af78ed6ef7b3cb048cfe309): update Instructions for Deploying on OpenShift ([#1537](https://github.com/quay/quay/issues/1537))
### Dockerfile
- [f0f31e0b](https://github.com/quay/quay/commit/f0f31e0b7a864c5322c6d7981d9f4afa4ad8e8e3): use nodejs ubi8 image to build frontends ([#1355](https://github.com/quay/quay/issues/1355))
### Export Compliance
- [adf70956](https://github.com/quay/quay/commit/adf709568eb84a473b2924b1e5adedf457c86813): Fetching quay user data from federated login username (PROJQUAY-0000) ([#1530](https://github.com/quay/quay/issues/1530))
### Fix
- [12e7c8fc](https://github.com/quay/quay/commit/12e7c8fcb0e9c2bcb3b839a21b9dbe4e4025c683): support oci image indexes that don't specify a mediaType (PROJQUAY-4254) ([#1469](https://github.com/quay/quay/issues/1469))
- [f2c4375f](https://github.com/quay/quay/commit/f2c4375f657a39a141ae0ed540659b1c50baeb93): enable non-admins to cache images via pull-thru (PROJQUAY-3806) ([#1366](https://github.com/quay/quay/issues/1366))
### GUI
- [020b3abe](https://github.com/quay/quay/commit/020b3abea2f8be15568f2e4e7f5de125e8c23298): Show how to pull an image using podman pull ([#1332](https://github.com/quay/quay/issues/1332))
### Healthcheck
- [c36945b8](https://github.com/quay/quay/commit/c36945b8361caf65ba294bc56722b5c6296b5035): Use db_kwargs in health check (PROJQUAY-4222) ([#1507](https://github.com/quay/quay/issues/1507))
### Init
- [e1745a9b](https://github.com/quay/quay/commit/e1745a9b13dcb0648091fa61a96cb076750d6590): fix bash path before appending certs (PROJQUAY-3881) ([#1359](https://github.com/quay/quay/issues/1359))
- [8786ef2e](https://github.com/quay/quay/commit/8786ef2efd78baee88d2354279fe9499f552873a): ensure a newline is present before appending certs (PROJQUAY-3881) ([#1356](https://github.com/quay/quay/issues/1356))
- [16d9a2ce](https://github.com/quay/quay/commit/16d9a2ce41f2990911c7e18d8b41a6e1e3b41ae0): ensure a newline is present before appending certs (PROJQUAY-3881) ([#1352](https://github.com/quay/quay/issues/1352))
### Logs
- [33dde306](https://github.com/quay/quay/commit/33dde30693287cf42cf259152578ef7b81395a2c): create action logs on proxy cache config creation/deletion (PROJQUAY-4718) ([#1636](https://github.com/quay/quay/issues/1636))
### Makefile
- [692e3cee](https://github.com/quay/quay/commit/692e3cee29132af1035ba66fa32404f0f9e2e857): use non-standard port for postgres test container ([#1485](https://github.com/quay/quay/issues/1485))
- [fd4e7723](https://github.com/quay/quay/commit/fd4e7723f34f11d085cb7951c6eab084efe39d65): use variable to tell postgres test target which tests to run ([#1475](https://github.com/quay/quay/issues/1475))
### Mirror
- [679380b9](https://github.com/quay/quay/commit/679380b99f67ad852db522360df6eadf3296c38b): Rollback failed tags (PROJQUAY-4322) ([#1496](https://github.com/quay/quay/issues/1496))
- [30298699](https://github.com/quay/quay/commit/30298699fc45b8d713c5ba70a49495c0037d96b2): Default mirror rollback to false (PROJQUAY-4296) ([#1490](https://github.com/quay/quay/issues/1490))
- [14c8d139](https://github.com/quay/quay/commit/14c8d13984ff2e1c8be0357592d942740ef51090): Pass command output to a tempfile instead of pipe (PROJQUAY-3145) ([#1417](https://github.com/quay/quay/issues/1417))
### Mirroring
- [26a334f5](https://github.com/quay/quay/commit/26a334f5d8bc82ebfcae12081818979865b45409): fix mirror claims for multiple processes (PROJQUAY-3982) ([#1433](https://github.com/quay/quay/issues/1433))
### Nginx
- [30bf4050](https://github.com/quay/quay/commit/30bf40506909db74cedb52212897074ad7228589): mark beginning of string in location match ([#1546](https://github.com/quay/quay/issues/1546))
### Oauth
- [5f49ffc2](https://github.com/quay/quay/commit/5f49ffc2d0658a70d1784b7bac7cb98dfcf77166): fix oauth token generation when using dangerous scopes (PROJQUAY-4042) ([#1457](https://github.com/quay/quay/issues/1457))
- [922a82a3](https://github.com/quay/quay/commit/922a82a3d945002dd2d259d2d7950614249ef382): Add the code param to the oauthrize.html template (PROJQUAY-3648) ([#1362](https://github.com/quay/quay/issues/1362))
### PROJQUAY-3750
- [ac6a8d2f](https://github.com/quay/quay/commit/ac6a8d2f8b93bcff032d3b2dfc57e07432a96709): support registries that do not return a digest header ([#1310](https://github.com/quay/quay/issues/1310))
### Proxy Cache
- [342a50eb](https://github.com/quay/quay/commit/342a50eb1f9c7a12a2afdeff6762939069c82def): respect CREATE_PRIVATE_REPO_ON_PUSH flag (PROJQUAY-3743) ([#1426](https://github.com/quay/quay/issues/1426))
### Pull-Thru
- [d029a465](https://github.com/quay/quay/commit/d029a4652deb763105af0db9ffa05cbf2b6b2343): bump expiration of all parent manifest lists on pull ([#1336](https://github.com/quay/quay/issues/1336))
### Quay
- [7c566ad4](https://github.com/quay/quay/commit/7c566ad4f3879e08ed82955a14122cd2a2e1f269): Exporting image.oci package to Quay module (PROJQUAY-0000) ([#1548](https://github.com/quay/quay/issues/1548))
### Quayio
- [b49fd45e](https://github.com/quay/quay/commit/b49fd45ee646d53c0789d79c60c87a7fb5ae8ec8): Redirect user to billing page when starting free trial (PROJQUAY-4130) ([#1439](https://github.com/quay/quay/issues/1439))
### Quota
- [f90e5e3d](https://github.com/quay/quay/commit/f90e5e3dcef4bb312e31aaf5a4ce536e81e3e424): Configuring Quota for user panel(PROJQUAY-3767) ([#1334](https://github.com/quay/quay/issues/1334))
- [1e4871ec](https://github.com/quay/quay/commit/1e4871eca27ea1878937a49fb2974401c5963512): Add Cache To Tag Delete (PROJQUAY-3828) ([#1345](https://github.com/quay/quay/issues/1345))
### Quota
- [a0df8950](https://github.com/quay/quay/commit/a0df895005bcd3e53847046f69f6a7add87c88fd): Fix calculating org size (PROJQUAY-3889) ([#1391](https://github.com/quay/quay/issues/1391))
- [f28b35cc](https://github.com/quay/quay/commit/f28b35cc311dae94671cc6bce4b11abc9a68e917): Fix join on caching repo size (PROJQUAY-3889) ([#1378](https://github.com/quay/quay/issues/1378))
- [9d8ff6b1](https://github.com/quay/quay/commit/9d8ff6b1c109fdc285298d32ec2a83069bd90556): address possible integrity exception if computing size concurrently (PROJQUAY-3752) ([#1303](https://github.com/quay/quay/issues/1303))
### Quota Management
- [59d586c4](https://github.com/quay/quay/commit/59d586c4c6294ceceb214d2fa1a8fb7e164081c8): Adding default quota check for image push (PROJQUAY-3789) ([#1316](https://github.com/quay/quay/issues/1316))
### Quota UI
- [a0bd9aca](https://github.com/quay/quay/commit/a0bd9aca3efe42c30a45b28f6f2b79d7829250d2): Show quota consumption in whole numbers on super user organizations panel (PROJQUAY-3974) ([#1383](https://github.com/quay/quay/issues/1383))
- [587cceb3](https://github.com/quay/quay/commit/587cceb3386d4b01dbe4b84a74cbf3fde60e82b6): Adding Overall storage consumption for Super users panel page (PROJQUAY-3639) ([#1307](https://github.com/quay/quay/issues/1307))
### Registry
- [c04d0a64](https://github.com/quay/quay/commit/c04d0a644d07e9f3195ef3543df951fe75cfdd95): correctly bump tag expiration when tag changes upstream (PROJQUAY-3976) ([#1479](https://github.com/quay/quay/issues/1479))
### Requirements.Txt
- [46cd48dd](https://github.com/quay/quay/commit/46cd48dd9febb0b894b2192d10ce649ce5da9bee): bump flask-restful from 0.3.7 to 0.3.9 ([#1375](https://github.com/quay/quay/issues/1375))
### Revert "Chore
- [51ebfc22](https://github.com/quay/quay/commit/51ebfc22d24d520691d1ee52b16a1c5c7d8ff995): Add server side assembly of chunked metadata for RADOSGW driver (PROJQUAY-4592) ([#1557](https://github.com/quay/quay/issues/1557))" ([#1643](https://github.com/quay/quay/issues/1643))
### Rhsso
- [0fdf96a2](https://github.com/quay/quay/commit/0fdf96a2d178c3d499ce7f53b5ff8a50e581cd91): Add checks for e-mail blocked in export screen (PROJQUAY-2056) ([#1333](https://github.com/quay/quay/issues/1333))
### Schema1
- [b2dbdcd7](https://github.com/quay/quay/commit/b2dbdcd79813bbe2b1c205c8f6a6a5616851cba9): Generate kid in the correct format (PROJQUAY-3486) ([#1208](https://github.com/quay/quay/issues/1208))
### Secscan
- [44462faf](https://github.com/quay/quay/commit/44462faf68bf215c4316f30ca9f5164157263827): Generate key to reduce vulnerabilities (PROJQUAY-4562) ([#1577](https://github.com/quay/quay/issues/1577))
- [5291daf8](https://github.com/quay/quay/commit/5291daf8fe22218995eb37e4ef6f8b3a481bdd2b): Don't delete manifest security status on error (PROJQUAY-4060) ([#1434](https://github.com/quay/quay/issues/1434))
- [5471d3cb](https://github.com/quay/quay/commit/5471d3cbcb4d4f923d1b1007677f20118eec8f6f): deprecate support for Clair V2 (PROJQUAY-2837) ([#951](https://github.com/quay/quay/issues/951))
- [776dbd90](https://github.com/quay/quay/commit/776dbd90d5d898776dff1a9a87d933bdfbc9a7b2): update https proxy scheme ([#1340](https://github.com/quay/quay/issues/1340))
### Sso
- [ca70a501](https://github.com/quay/quay/commit/ca70a501c6095ef2953fb37c032cdfec624dddd8): Handle edge case for stage sso only users (PROJQUAY-2056) ([#1326](https://github.com/quay/quay/issues/1326))
- [42f09298](https://github.com/quay/quay/commit/42f09298c453133da73bb4b9b363fb2ffed4b928): Fix debug statement (PROJQUAY-2056) ([#1325](https://github.com/quay/quay/issues/1325))
- [f6e754b5](https://github.com/quay/quay/commit/f6e754b561a0ebf356d34d6d56ca3f9f539eb4f1): Use trusted cert from extra_ca_certs directory (PROJQUAY-2056) ([#1324](https://github.com/quay/quay/issues/1324))
- [0826ac0e](https://github.com/quay/quay/commit/0826ac0e4e6da68dab99a9746e09c5181b2e516b): Use requests client in screening call (PROJQUAY-2056) ([#1321](https://github.com/quay/quay/issues/1321))
- [4e739d30](https://github.com/quay/quay/commit/4e739d30bf6be74b5094012ab5aae91865a59ef7): Update mount path for export compliance certificate (PROJQUAY-2056) ([#1320](https://github.com/quay/quay/issues/1320))
- [2c3e26a3](https://github.com/quay/quay/commit/2c3e26a322501aef73d887fc2346ef7e1610fdff): Add test for RHSSO OAuth service (PROJQUAY-2056) ([#1317](https://github.com/quay/quay/issues/1317))
### Storage
- [47564690](https://github.com/quay/quay/commit/47564690071c02a6f7d5cf7b5ac1c9a102ab7523): handle KeyError we sometimes get from aws ([#1543](https://github.com/quay/quay/issues/1543))
- [a101553c](https://github.com/quay/quay/commit/a101553cb1bae22cdf4b16e37a3a3a2bc8645e48): return S3 url only for ip ranges in the same region (PROJQUAY-4498) ([#1539](https://github.com/quay/quay/issues/1539))
- [e6be9fc4](https://github.com/quay/quay/commit/e6be9fc43a04c2770b82927b939f9347f270b7cb): Add username field to requests on CloudFront (PROJQUAY-3511) ([#1486](https://github.com/quay/quay/issues/1486))
- [56b16b70](https://github.com/quay/quay/commit/56b16b70cca1ff0f5f51dd2fb47852027d66eef6): optimize large azure chunked upload (PROJQUAY-3753) ([#1387](https://github.com/quay/quay/issues/1387))
### Superusers
- [acb4b509](https://github.com/quay/quay/commit/acb4b509582a6abe04dc6c5feecad3aff8666e6d): grant superusers additinonal org permissions (PROJQUAY-4687) ([#1615](https://github.com/quay/quay/issues/1615))
### Task
- [eb308136](https://github.com/quay/quay/commit/eb308136836ccbe64bbaf143ef67330e72a5010e): remove obsolete logrotate.conf file (PROJQUAY-4364) ([#1500](https://github.com/quay/quay/issues/1500))
### UI
- [ba2aa54d](https://github.com/quay/quay/commit/ba2aa54d3fc081c052d65c899b49f67dd6ca3ada): Superuser user panel settings icon permissions fix (PROJQUAY-3905) ([#1364](https://github.com/quay/quay/issues/1364))
- [c93661e9](https://github.com/quay/quay/commit/c93661e9d51a645b43760db83b20f8b9c8041d3c): Show settings icon for super user under Superuser Users Panel (PROJQUAY-3905) ([#1358](https://github.com/quay/quay/issues/1358))
### Ui
- [4dd1e1e0](https://github.com/quay/quay/commit/4dd1e1e01bfffd4b0598ffb653db262413d44204): Fix font size in superuser page (PROJQUAY-4407) ([#1555](https://github.com/quay/quay/issues/1555))
- [5f1fdbc5](https://github.com/quay/quay/commit/5f1fdbc59ff491dcef1531d69fb1393df26f8ffc): Support on Old UI to switch to New UI (PROJQUAY-4124) ([#1504](https://github.com/quay/quay/issues/1504))
- [b1d13d16](https://github.com/quay/quay/commit/b1d13d1622f5df33c561a81ad317b647e6b43524): Remove trial from larger plans for quay.io (PROJQUAY-4197) ([#1459](https://github.com/quay/quay/issues/1459))
- [7cbf0ffd](https://github.com/quay/quay/commit/7cbf0ffd7d3bf3c6de1943af2f638f4eb90b038c): Remove trial from larger plans for quay.io (PROJQUAY-4197) ([#1455](https://github.com/quay/quay/issues/1455))
- [1a016efc](https://github.com/quay/quay/commit/1a016efc80220c7c62b723ce62a4044d7d8b9a24): Add CSRF and token endpoint and public config endpoint (PROJQUAY-3865) ([#1323](https://github.com/quay/quay/issues/1323))
- [d9dbbd88](https://github.com/quay/quay/commit/d9dbbd88dbb9a1da95ef46195bcfb5458db6a7b8): basic support for cosign in the UI (PROJQUAY-3965) ([#1380](https://github.com/quay/quay/issues/1380))
### User
- [1e136d6d](https://github.com/quay/quay/commit/1e136d6dd0fec70cb6e4cbd442ef1768aab1592d): Added function to fetch users public repositories count (PROJQUAY-0000) ([#1540](https://github.com/quay/quay/issues/1540))
### Users
- [80617b93](https://github.com/quay/quay/commit/80617b93ef6b9b3628352de57fd98a6e14b02637): default to true if LDAP_RESTRICTED_USER_FILTER is not set (PROJQUAY-4776) ([#1646](https://github.com/quay/quay/issues/1646))
- [52c3ab1d](https://github.com/quay/quay/commit/52c3ab1d5bf5142af20121fe3737fd366dc6682d): fix behavior when using ldap and restricted user whitelist is set (PROJQUAY-4767) ([#1641](https://github.com/quay/quay/issues/1641))
- [4390bbcc](https://github.com/quay/quay/commit/4390bbccd00868bd9f672168b7e5ff8238147128): fix create repo on push on orgs for restricted users (PROJQUAY-4732) ([#1635](https://github.com/quay/quay/issues/1635))
- [5592ae69](https://github.com/quay/quay/commit/5592ae69a59703c186519e6e9caf303d94ed5871): prevent CREATE_NAMESPACE_ON_PUSH is restricted (PROJQUAY-4702) ([#1624](https://github.com/quay/quay/issues/1624))
- [c4595fbb](https://github.com/quay/quay/commit/c4595fbbca77cdc935e6e247551d4876335fc7ec): when set, grant superusers repository permissions. ([#1622](https://github.com/quay/quay/issues/1622))
- [f6ee8ac3](https://github.com/quay/quay/commit/f6ee8ac3aa1bd0186fa9582dbbb9a9eb6abdb920): prevent creating repo on push for restricted users (PROJQUAY-4706) ([#1616](https://github.com/quay/quay/issues/1616))
- [33a322c2](https://github.com/quay/quay/commit/33a322c26ebc49978ebe61dd140c1399bdd928b8): add restricted users' filter (PROJQUAY-1245) ([#1599](https://github.com/quay/quay/issues/1599))
- [14e87bd4](https://github.com/quay/quay/commit/14e87bd41e393032576fd23daf4801ea5f7def22): fix missing references in ldap for superusers ([#1542](https://github.com/quay/quay/issues/1542))
- [070f464b](https://github.com/quay/quay/commit/070f464b149695b79d837fd781bd72aadde5753e): superuser group in federated identity provider (PROJQUAY-3924) ([#1464](https://github.com/quay/quay/issues/1464))
### V2auth
- [fd9a6b2e](https://github.com/quay/quay/commit/fd9a6b2e606db6d20bb079f4c3a942e176f83a0c): Check for user before creating org (PROJQUAY-3766) ([#1315](https://github.com/quay/quay/issues/1315))
### [Redhat-3.8] Arch
- [2e6f9b1e](https://github.com/quay/quay/commit/2e6f9b1e747db123a8237fcda9ab679ba761e5cd): add ppc64le support to quay (PROJQUAY-4595) ([#1558](https://github.com/quay/quay/issues/1558))
### [Redhat-3.8] Chore
- [48f9a952](https://github.com/quay/quay/commit/48f9a952cedf16e1a031a1fb7f2f188bc0def3d4): Add server side assembly of chunked metadata for RADOSGW driver (PROJQUAY-4592) ([#1584](https://github.com/quay/quay/issues/1584))
### [Redhat-3.8] Config
- [4a2d7b40](https://github.com/quay/quay/commit/4a2d7b40c1f61005b2ea3055a18675c5677ab753): Updating Cosign SBOM Media Types on Quay (PROJQUAY-4591) ([#1565](https://github.com/quay/quay/issues/1565))
### [Redhat-3.8] Repomirror
- [55cb0ba1](https://github.com/quay/quay/commit/55cb0ba1a3d21f1c5db4e2f05298a494e0411316): Use skopeo list-tags to get repo tags (PROJQUAY-2179) ([#1559](https://github.com/quay/quay/issues/1559))

<a name="v3.7.13"></a>
## [v3.7.13] - 2023-07-13
### Chore
- [2d151a70](https://github.com/quay/quay/commit/2d151a70e00fe96b6717c236e407123629682f66): v3.7.13 changelog bump (PROJQUAY-5815) ([#2014](https://github.com/quay/quay/issues/2014))

<a name="v3.7.12"></a>
## [v3.7.12] - 2023-06-05
### Chore
- [578e047a](https://github.com/quay/quay/commit/578e047a05800a12ea7ddbd284ea6d08e11a8ddc): v3.7.12 changelog bump ( PROJQUAY-5599) ([#1937](https://github.com/quay/quay/issues/1937))
- [b57937a5](https://github.com/quay/quay/commit/b57937a524510f340e7bb62bcea36c8791091bc4): Remove appr dependencies (PROJQUAY-4992) ([#1936](https://github.com/quay/quay/issues/1936))
- [bb0544db](https://github.com/quay/quay/commit/bb0544db4f62b0bd027dc630ee22cba641f344f2): Pin distribution-spec conformance tests ([#1919](https://github.com/quay/quay/issues/1919))
- [96bc0dec](https://github.com/quay/quay/commit/96bc0decf7aaad89f3c5661296b14e6e48b0f0ef): remove deprecated appr code (PROJQUAY-4992) ([#1746](https://github.com/quay/quay/issues/1746))
### Superuser
- [65de5d3b](https://github.com/quay/quay/commit/65de5d3b85aa4ae46f9bcfe389872a84cfacf693): paginate user's list (PROJQUAY-4297) ([#1881](https://github.com/quay/quay/issues/1881)) ([#1923](https://github.com/quay/quay/issues/1923))
### Tox
- [c3e5912c](https://github.com/quay/quay/commit/c3e5912c32b83814966b6ce0dd1abf5203e62317): allow /bin/sh (PROJQUAY-5092) ([#1918](https://github.com/quay/quay/issues/1918))
### [Redhat-3.7] Oci
- [7c22f8e3](https://github.com/quay/quay/commit/7c22f8e346a24f947d746d5d5f1b35404f1f9bc1): Create workflow for OCI Conformance (PROJQUAY-2812) ([#1744](https://github.com/quay/quay/issues/1744))
### [Redhat-3.7] Superuser
- [f5f0ea90](https://github.com/quay/quay/commit/f5f0ea905b4185a0db9106f7eddf755f707a1819): lowering page limit (PROJQUAY-5178) ([#1912](https://github.com/quay/quay/issues/1912)) ([#1925](https://github.com/quay/quay/issues/1925))
- [4cbde7e2](https://github.com/quay/quay/commit/4cbde7e25d9120d4b635aaca46fd59c78913ee3b): paginating superuser organization list (PROJQUAY-4297) ([#1895](https://github.com/quay/quay/issues/1895))

<a name="v3.7.11"></a>
## [v3.7.11] - 2022-12-01
### Chore: V3.7.11 Changelog Bump (Https
- [5b1d1f67](https://github.com/quay/quay/commit/5b1d1f6706ef860760264d5dc1c5a84dbb467951): //issues.redhat.com/browse/PROJQUAY-4790) ([#1652](https://github.com/quay/quay/issues/1652))
### Revert "Chore
- [f61ba511](https://github.com/quay/quay/commit/f61ba51171ef58c8caaffdfbfba4f27efa564c7c): Add server side assembly of chunked metadata for RADOSGW driver (PROJQUAY-4592) ([#1557](https://github.com/quay/quay/issues/1557))" ([#1647](https://github.com/quay/quay/issues/1647))

<a name="v3.7.10"></a>
## [v3.7.10] - 2022-10-25
### Auth
- [b619da30](https://github.com/quay/quay/commit/b619da308de62272eae9d85c9c9d357188c19ff0): Speed up permissions loading (PROJQUAY-4004) ([#1581](https://github.com/quay/quay/issues/1581))
### Chore: V3.7.10 Changelog Bump (Https
- [59937c6d](https://github.com/quay/quay/commit/59937c6dbf896cc6b01e5b295f8d17449284c0c1): //issues.redhat.com/browse/PROJQUAY-4627) ([#1592](https://github.com/quay/quay/issues/1592))
### Secscan
- [128f1255](https://github.com/quay/quay/commit/128f1255766fa2fb1a0c72a09fa030871383511d): Generate key to reduce vulnerabilities (PROJQUAY-4562) ([#1576](https://github.com/quay/quay/issues/1576))
### [Redhat-3.7] Chore
- [72e382c8](https://github.com/quay/quay/commit/72e382c827879dd2c794d217eab5738cd48f862a): Add server side assembly of chunked metadata for RADOSGW driver (PROJQUAY-4592) ([#1583](https://github.com/quay/quay/issues/1583))

<a name="v3.7.9"></a>
## [v3.7.9] - 2022-10-17
### Chore: V3.7.9 Changelog Bump (Https
- [f65a235e](https://github.com/quay/quay/commit/f65a235e541b44566b3e013977ae9e1bc610ff74): //issues.redhat.com/browse/PROJQUAY-4478) ([#1569](https://github.com/quay/quay/issues/1569))
### Storage
- [4d44be98](https://github.com/quay/quay/commit/4d44be98c62b5511a4e2c4f40bad5dde2baa65e1): handle KeyError we sometimes get from aws ([#1544](https://github.com/quay/quay/issues/1544))

<a name="v3.7.8"></a>
## [v3.7.8] - 2022-09-12
### Chore: V3.7.7 Changelog Bump (Https
- [40b023fd](https://github.com/quay/quay/commit/40b023fd3ac3e10b075c5a5031850770eb7617a7): //issues.redhat.com/browse/PROJQUAY-4286) ([#1509](https://github.com/quay/quay/issues/1509))
### Chore: V3.7.8 Changelog Bump (Https
- [53f866cc](https://github.com/quay/quay/commit/53f866ccbc21c04a4a93e524c72a0995e819de25): //issues.redhat.com/browse/PROJQUAY-4385) ([#1518](https://github.com/quay/quay/issues/1518))
### Healthcheck
- [7a10c7b6](https://github.com/quay/quay/commit/7a10c7b6afce623bcfba4df35d1837ced33a1d0a): Use db_kwargs in health check (PROJQUAY-4222) ([#1511](https://github.com/quay/quay/issues/1511))
### [Redhat-3.7] Bug
- [1f5f0475](https://github.com/quay/quay/commit/1f5f0475176a2c00d5b3d7b1adac281f2565f555): Increase column size in logentry3 table (PROJQUAY-4305) ([#1512](https://github.com/quay/quay/issues/1512))
- [94f1795e](https://github.com/quay/quay/commit/94f1795e6deaa1120686a4c525b5728d38412f9f): Fix schema discovery on basic auth (PROJQUAY-4362) ([#1505](https://github.com/quay/quay/issues/1505))
### [Redhat-3.7] Ci
- [117a7ebd](https://github.com/quay/quay/commit/117a7ebd49ae49b266329306fcbcbca8242418eb): Update release workflow to use new release action (PROJQUAY-4444) ([#1527](https://github.com/quay/quay/issues/1527))

<a name="v3.7.7"></a>
## [v3.7.7] - 2022-08-29
### Mirror
- [72a4d353](https://github.com/quay/quay/commit/72a4d353fb171b1747f864edc09ae6987818ad1d): Rollback failed tags (PROJQUAY-4322) ([#1501](https://github.com/quay/quay/issues/1501))
- [21931a63](https://github.com/quay/quay/commit/21931a639fb05b8a5b195af45b8dfcac808817d1): Default mirror rollback to false (PROJQUAY-4296) ([#1491](https://github.com/quay/quay/issues/1491))
### Registry
- [b7f3434a](https://github.com/quay/quay/commit/b7f3434a38f15f6e76779a7837055c63dc816dd2): correctly bump tag expiration when tag changes upstream ([#1484](https://github.com/quay/quay/issues/1484))

<a name="v3.7.6"></a>
## [v3.7.6] - 2022-08-15
### Chore: V3.7.6 Changelog Bump (Https
- [01b30c2d](https://github.com/quay/quay/commit/01b30c2d6fabd5ca5837321c0ac65de20419008a): //issues.redhat.com/browse/PROJQUAY-4237) ([#1480](https://github.com/quay/quay/issues/1480)) ([#1481](https://github.com/quay/quay/issues/1481))
### Fix
- [dc17f537](https://github.com/quay/quay/commit/dc17f537d434f19f3b4993135b65b7e7cd381d2d): support oci image indexes that don't specify a mediaType (PROJQUAY-4254) ([#1472](https://github.com/quay/quay/issues/1472))
### Proxy Cache
- [f3910e3c](https://github.com/quay/quay/commit/f3910e3c50bb88394028e9924783d36d855615b1): respect CREATE_PRIVATE_REPO_ON_PUSH flag (PROJQUAY-3743) ([#1470](https://github.com/quay/quay/issues/1470))

<a name="v3.7.5"></a>
## [v3.7.5] - 2022-07-26
### Auth
- [f435b9e6](https://github.com/quay/quay/commit/f435b9e6d4c7a84e7853aeebdbc06d5eda4a3bee): allow rs384 in jwt (PROJQUAY-4148) ([#1450](https://github.com/quay/quay/issues/1450))
### Chore: V3.7.4 Changelog Bump (Https
- [10edbe6d](https://github.com/quay/quay/commit/10edbe6df195edfb2b6cbb096ceb71501bf26c93): //issues.redhat.com/browse/PROJQUAY-4050) ([#1446](https://github.com/quay/quay/issues/1446)) ([#1447](https://github.com/quay/quay/issues/1447))
### Chore: V3.7.5 Changelog Bump (Https
- [564f3f0c](https://github.com/quay/quay/commit/564f3f0cf1d9a1c058293e27259c955a8489cd6a): //issues.redhat.com/browse/PROJQUAY-4172) ([#1460](https://github.com/quay/quay/issues/1460))
### Mirroring
- [eb20c961](https://github.com/quay/quay/commit/eb20c9610339611ddeb93f80d958521a1c761073): fix mirror claims for multiple processes (PROJQUAY-3982) ([#1453](https://github.com/quay/quay/issues/1453))

<a name="v3.7.4"></a>
## [v3.7.4] - 2022-07-07
### Builders
- [92d694aa](https://github.com/quay/quay/commit/92d694aa216317a16a81bae4fe56c29242ab1cf6): Add cacert's to build agent (PROJQUAY-3819) ([#1398](https://github.com/quay/quay/issues/1398)) ([#1436](https://github.com/quay/quay/issues/1436))
### Mirror
- [c5354154](https://github.com/quay/quay/commit/c53541544d6fd18c4c52f524eb3ed1bad3c776ce): Pass command output to a tempfile instead of pipe (PROJQUAY-3145) ([#1437](https://github.com/quay/quay/issues/1437))

<a name="v3.7.3"></a>
## [v3.7.3] - 2022-06-28
### Chore: V3.7.3 Changelog Bump (Https
- [50f24e2f](https://github.com/quay/quay/commit/50f24e2f1d423ca5622d3af07c1ef6c6f40a4887): //issues.redhat.com/browse/PROJQUAY-3989) ([#1420](https://github.com/quay/quay/issues/1420)) ([#1421](https://github.com/quay/quay/issues/1421))
### Storage
- [34765df7](https://github.com/quay/quay/commit/34765df70943253ff7d1445364466bbe5e7534d6): optimize large azure chunked upload (PROJQUAY-3753) ([#1408](https://github.com/quay/quay/issues/1408))
### [Redhat-3.7] Ui
- [992bfa1f](https://github.com/quay/quay/commit/992bfa1f3769fe984c8d16dab680f981fc7c2188): basic support for cosign in the UI (PROJQUAY-3965) ([#1414](https://github.com/quay/quay/issues/1414))

<a name="v3.7.2"></a>
## [v3.7.2] - 2022-06-22
### Builders
- [ec8da07c](https://github.com/quay/quay/commit/ec8da07c2eee80a78deef94db23e60e734b2195a): Send notifications on build completion (PROJQUAY-3614) ([#1367](https://github.com/quay/quay/issues/1367))
### Chore: V3.7.1 Changelog Bump (Https
- [ece9d54f](https://github.com/quay/quay/commit/ece9d54f41bd30d6a43d6b1ec33426ed41e02494): //issues.redhat.com/browse/PROJQUAY-3836) ([#1373](https://github.com/quay/quay/issues/1373))
### Chore: V3.7.2 Changelog Bump (Https
- [78814ef2](https://github.com/quay/quay/commit/78814ef22fd5828dc0e105c9fb3c06734557e2b4): //issues.redhat.com/browse/PROJQUAY-3932) ([#1406](https://github.com/quay/quay/issues/1406))
### Fix
- [6090bd05](https://github.com/quay/quay/commit/6090bd05a7368a7cbf8afbfd4818f78d7fab43bf): enable non-admins to cache images via pull-thru (PROJQUAY-3806) ([#1366](https://github.com/quay/quay/issues/1366)) ([#1379](https://github.com/quay/quay/issues/1379))
### GUI
- [5487b269](https://github.com/quay/quay/commit/5487b269f2d4c02f2a2e0188db9ff2e464b012f0): Show how to pull an image using podman pull ([#1377](https://github.com/quay/quay/issues/1377))
### Quota
- [af28e832](https://github.com/quay/quay/commit/af28e832d82cecc88be7482ac045c5145397d115): Fix calculating org size (PROJQUAY-3889) ([#1393](https://github.com/quay/quay/issues/1393))
- [058b9d34](https://github.com/quay/quay/commit/058b9d34ceaa1014bced26e2a18d6a3af44490e0): Fix join on caching repo size (PROJQUAY-3889) ([#1381](https://github.com/quay/quay/issues/1381))
### Requirements.Txt
- [c0cdee4e](https://github.com/quay/quay/commit/c0cdee4e6c5583fcad833372dfb06094aaa6ea81): bump flask-restful from 0.3.7 to 0.3.9 ([#1376](https://github.com/quay/quay/issues/1376))
### UI
- [abbbe4ad](https://github.com/quay/quay/commit/abbbe4addc42aec757cf2d7d52790c0ab8fab9c3): Superuser user panel settings icon permissions fix (PROJQUAY-3905) ([#1368](https://github.com/quay/quay/issues/1368))
### [Redhat-3.7] Quota UI
- [179a7dbf](https://github.com/quay/quay/commit/179a7dbfb09834ab39802f75886b2add032a352f): Show quota consumption in whole numbers on super user organizations panel (PROJQUAY-3974) ([#1386](https://github.com/quay/quay/issues/1386))

<a name="v3.7.1"></a>
## [v3.7.1] - 2022-06-06
### Init
- [e37960f2](https://github.com/quay/quay/commit/e37960f258638266c55c7c1d6659da7f818c3d1f): fix bash path before appending certs (PROJQUAY-3881) ([#1360](https://github.com/quay/quay/issues/1360))
- [cba35f91](https://github.com/quay/quay/commit/cba35f91be47eee17c4715620e239a3934b9ba82): ensure a newline is present before appending certs (PROJQUAY-3881) ([#1357](https://github.com/quay/quay/issues/1357))
- [c1227410](https://github.com/quay/quay/commit/c122741063bdf4fac9d7e1d7deecc9c076ba23b1): ensure a newline is present before appending certs (PROJQUAY-3881) ([#1354](https://github.com/quay/quay/issues/1354))
### Pull-Thru
- [a7ffd5c7](https://github.com/quay/quay/commit/a7ffd5c7ec4179cc6aba7fbf8ac3690ed43ab0a2): bump expiration of all parent manifest lists on pull (PROJQUAY-3818) ([#1343](https://github.com/quay/quay/issues/1343))
### [Redhat-3.7] Quota
- [abe1528d](https://github.com/quay/quay/commit/abe1528da8fed94fd4ecaa950f0bc567400b58b3): Configuring Quota for user panel(PROJQUAY-3767) ([#1353](https://github.com/quay/quay/issues/1353))
- [0cafea97](https://github.com/quay/quay/commit/0cafea97d869fb953ffa28df18c60b3fcb2abb3d): Add Cache To Tag Delete (PROJQUAY-3828) ([#1347](https://github.com/quay/quay/issues/1347))
### [Redhat-3.7] UI
- [5de7b6ce](https://github.com/quay/quay/commit/5de7b6ce4cfe703fc7f259dee837dc6ea22341a7): Show settings icon for super user under Superuser Users Panel (PROJQUAY-3905) ([#1361](https://github.com/quay/quay/issues/1361))

<a name="v3.7.0"></a>
## [v3.7.0] - 2022-05-23
### API
- [2dca65f9](https://github.com/quay/quay/commit/2dca65f9cef56581457535b70683ec93bcde2876): Removing internal only decorator from exposed Super user endpoints ([#1271](https://github.com/quay/quay/issues/1271))
### Api
- [896a3aab](https://github.com/quay/quay/commit/896a3aab3a8109cf2e8899aadd865d4d77927719): update the quota api so that it's more consistent with the other apis endpoints (PROJQUAY-2936) ([#1221](https://github.com/quay/quay/issues/1221))
- [02dfc63f](https://github.com/quay/quay/commit/02dfc63f42eff253571fbe6da8d48adf48660202): fully deprecate image api endpoints (PROJQUAY-3418) ([#1164](https://github.com/quay/quay/issues/1164))
### App.Py
- [b4600553](https://github.com/quay/quay/commit/b4600553b9327032149a52c5efc58a9da3e99ee7): filter proxy cache login details from debug logs ([#1268](https://github.com/quay/quay/issues/1268))
### Auth
- [6effd4cd](https://github.com/quay/quay/commit/6effd4cdec250bedb9a36b810dfec3519b61ed7b): Add state to the oauthorize redirect (PROJQUAY-3648) ([#1301](https://github.com/quay/quay/issues/1301))
- [edb4e721](https://github.com/quay/quay/commit/edb4e72166cb1c557dfcad27533226fa75827f9b): Add state to the oauthorize page (PROJQUAY-3648) ([#1292](https://github.com/quay/quay/issues/1292))
- [2219d5ae](https://github.com/quay/quay/commit/2219d5aed22f28546df28fac4a4c7d0cc783f9d6): Add state to the Oauth code response (PROJQUAY-3139) ([#1124](https://github.com/quay/quay/issues/1124))
- [0033f9b8](https://github.com/quay/quay/commit/0033f9b851502bd474d8ddd3faf4e5d78f43f9ca): Fix oauth code flow (PROJQUAY-781) ([#1044](https://github.com/quay/quay/issues/1044))
### Billing
- [8da53e97](https://github.com/quay/quay/commit/8da53e972047cec9a4339189112fe9b9272e3bb8): use BytesIO when rendering invoice (PROJQUAY-3267) ([#1174](https://github.com/quay/quay/issues/1174))
- [259da89c](https://github.com/quay/quay/commit/259da89cb64c85166f7bcd4b13ef007934e4c032): Remove type hints for FakeStripe (PROJQUAY-2777) ([#974](https://github.com/quay/quay/issues/974))
- [8d0aa9ff](https://github.com/quay/quay/commit/8d0aa9ffedb7d8148e890badf5c0bd86f4ef6e40): Remove annotations for type hints in billing (PROJQUAY-2777) ([#973](https://github.com/quay/quay/issues/973))
### Blobuploadcleanupworker
- [f35f3f13](https://github.com/quay/quay/commit/f35f3f137cd5d1e4594438e0db5c498651f1a396): Add BLOBUPLOAD_DELETION_DATE_THRESHOLD (PROJQUAY-2915) ([#1022](https://github.com/quay/quay/issues/1022))
- [22282dae](https://github.com/quay/quay/commit/22282dae093fc8f8bee543b1fa33e7f3c9c6b618): Add cleanup for orphaned blobs (PROJQUAY-2313) ([#967](https://github.com/quay/quay/issues/967))
### Build
- [443b8d50](https://github.com/quay/quay/commit/443b8d50a9300a850473457deedc45c942116ebd): Update pyrsistent to fix Dockerfile.deploy (PROJQUAY-3125) ([#1079](https://github.com/quay/quay/issues/1079))
- [fba69d93](https://github.com/quay/quay/commit/fba69d939ec336c5fc46a9e5f5cfd9ee3b2ee38e): Add required setup.cfg for downstream build (PROJQUAY-2713) ([#946](https://github.com/quay/quay/issues/946)) ([#993](https://github.com/quay/quay/issues/993))
- [eb668cad](https://github.com/quay/quay/commit/eb668cad6622cc902bf1b88506dc0a8fc6d9f921): Use a configtool tag in the Dockerfile instead of master (PROJQUAY-2777) ([#972](https://github.com/quay/quay/issues/972))
- [78f8081a](https://github.com/quay/quay/commit/78f8081a0a53dd07096adc2545c9254112df3921): Use a configtool tag in the Dockerfile instead of master (PROJQUAY-2777) ([#971](https://github.com/quay/quay/issues/971))
- [a347d316](https://github.com/quay/quay/commit/a347d3167dece3078a119203137bf4230f8c01e5): Update backup base image name (PROJQUAY-2372) ([#965](https://github.com/quay/quay/issues/965))
- [d2f4efd8](https://github.com/quay/quay/commit/d2f4efd8428c6d7da6fd3038eaff6c15d57b05a1): Remove the image archive in post-deploy  (PROJQUAY-2372) ([#963](https://github.com/quay/quay/issues/963))
- [af2eeaa6](https://github.com/quay/quay/commit/af2eeaa61770adf69011369bb2efc86d3878165b): Use docker-archive for post-deploy script  (PROJQUAY-2372) ([#962](https://github.com/quay/quay/issues/962))
- [e8cf6339](https://github.com/quay/quay/commit/e8cf6339c31e76df608cab074f5acc3ee5f12095): Add docker-save to push images via skopeo on rhel-8 (PROJQUAY-2372) ([#960](https://github.com/quay/quay/issues/960))
- [d8b0e949](https://github.com/quay/quay/commit/d8b0e949005e6f78dd1368a55c578ac1fecc6091): Add docker-save to push images via skopeo on rhel-8 (PROJQUAY-2372) ([#959](https://github.com/quay/quay/issues/959))
- [759a83fa](https://github.com/quay/quay/commit/759a83fabfd64ec18554120fe74718599727fcd3): use Dockerfile for building quay app-sre (PROJQUAY-2373) ([#926](https://github.com/quay/quay/issues/926))
### Build(Deps)
- [4ee715c9](https://github.com/quay/quay/commit/4ee715c9e8c27ea37a5229f9b64cf264a36817bd): bump is-my-json-valid from 2.16.0 to 2.20.6 ([#1058](https://github.com/quay/quay/issues/1058))
- [b009590c](https://github.com/quay/quay/commit/b009590c4f7f83e01adec3d26fb62d0149375710): bump ajv from 6.10.2 to 6.12.6 ([#1112](https://github.com/quay/quay/issues/1112))
- [4176c498](https://github.com/quay/quay/commit/4176c498f50b20f382953a649dfd67efd25a17ad): bump moment from 2.17.1 to 2.29.2 ([#1236](https://github.com/quay/quay/issues/1236))
- [723fd599](https://github.com/quay/quay/commit/723fd59918a30a073aadd3ea70f1a01964d7f8df): bump url-parse from 1.5.8 to 1.5.9 ([#1168](https://github.com/quay/quay/issues/1168))
- [4b4f16e1](https://github.com/quay/quay/commit/4b4f16e1b4bb24bea0a9e0d848baaab481de2e44): bump url-parse from 1.5.6 to 1.5.8 ([#1151](https://github.com/quay/quay/issues/1151))
- [49c56aa1](https://github.com/quay/quay/commit/49c56aa1c5c7e009df842d5f2825d7d9b357d58c): bump url-parse from 1.5.2 to 1.5.6 ([#1125](https://github.com/quay/quay/issues/1125))
- [c96d1fbc](https://github.com/quay/quay/commit/c96d1fbc1903aef8e28eae90afa9216e57ccebee): bump protobuf from 3.12.2 to 3.15.0 ([#1110](https://github.com/quay/quay/issues/1110))
- [102705c9](https://github.com/quay/quay/commit/102705c9469a6c5624308a31b78d10cb17a00ddd): bump pillow from 8.3.2 to 9.0.0 ([#1059](https://github.com/quay/quay/issues/1059))
- [e7e093b0](https://github.com/quay/quay/commit/e7e093b0a6c863930594eb4aad1db48289860bc9): bump qs from 6.3.1 to 6.3.3 ([#1086](https://github.com/quay/quay/issues/1086))
- [88956630](https://github.com/quay/quay/commit/889566305bc613d521c0e1d773f9773db32a5d30): bump y18n from 3.2.1 to 3.2.2 ([#1080](https://github.com/quay/quay/issues/1080))
- [21f3538f](https://github.com/quay/quay/commit/21f3538f4eb939c39c217726670288b6b745669e): bump python-ldap from 3.2.0 to 3.4.0 ([#1002](https://github.com/quay/quay/issues/1002))
- [ae516d84](https://github.com/quay/quay/commit/ae516d8481a601a58cc86bf323a607991b7b36c2): bump reportlab from 3.5.34 to 3.5.55 ([#978](https://github.com/quay/quay/issues/978))
- [288f31bb](https://github.com/quay/quay/commit/288f31bbfbced3850836ba155b602ab54d872c7d): bump pip from 20.2.3 to 21.1 ([#977](https://github.com/quay/quay/issues/977))
- [8eab6366](https://github.com/quay/quay/commit/8eab6366cdcfa273da88ab6fcd0c94681b24fb74): bump babel from 2.8.0 to 2.9.1 ([#944](https://github.com/quay/quay/issues/944))
- [66373020](https://github.com/quay/quay/commit/663730203b6f7d00076051d6e83e99b9b71f04a8): bump url-parse from 1.4.0 to 1.5.2 ([#873](https://github.com/quay/quay/issues/873))
- [299fa6d9](https://github.com/quay/quay/commit/299fa6d958ef79f33d590268368425339467905a): bump pillow from 8.3.1 to 8.3.2 ([#882](https://github.com/quay/quay/issues/882))
- [b6495343](https://github.com/quay/quay/commit/b6495343942ccd32a3227a2dd0d6646d80772d8b): bump path-parse from 1.0.5 to 1.0.7 ([#870](https://github.com/quay/quay/issues/870))
### Builders
- [5cf6d99c](https://github.com/quay/quay/commit/5cf6d99c3b10e6eb848458ef2c865e95631c66d9): Add dnsPolicy option (PROJQUAY-3755) ([#1306](https://github.com/quay/quay/issues/1306))
- [9557cb9a](https://github.com/quay/quay/commit/9557cb9abbabc3f16b2d39484bd65267a0119473): Set default kubernetesPodman image (PROJQUAY-3586) ([#1245](https://github.com/quay/quay/issues/1245))
- [d8ae686f](https://github.com/quay/quay/commit/d8ae686f9b0992ffe73cccf945bd7a359a8a5acc): Persist build pod when DEBUG is true (PROJQUAY-3710) ([#1297](https://github.com/quay/quay/issues/1297))
- [88e86eb1](https://github.com/quay/quay/commit/88e86eb11e5095c83ce7b50716c357034dbc0273): Set backoffLimit to 1 (PROJQUAY-3587) ([#1246](https://github.com/quay/quay/issues/1246))
- [2d053e37](https://github.com/quay/quay/commit/2d053e37fbddac020e19f4c79d4ce2fc11cc5fec): add a check for expired key (PROJQUAY-3489) ([#1214](https://github.com/quay/quay/issues/1214))
- [4ecbcded](https://github.com/quay/quay/commit/4ecbcded060699388ffd008f6687c40bad4abc9f): Add DEBUG and JOB_REGISTRATION_TIMEOUT options (PROJQUAY-3395) ([#1177](https://github.com/quay/quay/issues/1177))
- [5d55ad55](https://github.com/quay/quay/commit/5d55ad55f90db0ef38ceeb999b66a15535f07bd4): Update py-bitbucket to fix bitbucket triggers (PROJQUAY-3362) ([#1170](https://github.com/quay/quay/issues/1170))
- [30ab139e](https://github.com/quay/quay/commit/30ab139ea9957655a6b9e24a1a26f41b19d09748): Remove ServerSideEncryption param from presigned URL (PROJQUAY-3180) ([#1105](https://github.com/quay/quay/issues/1105))
- [7082f867](https://github.com/quay/quay/commit/7082f867a652c8d43a9be64283d71866b160ef6c): Update boto to fix signature error (PROJQUAY-2542) ([#1087](https://github.com/quay/quay/issues/1087))
- [dce0b934](https://github.com/quay/quay/commit/dce0b934337b5f401f0107492e99e72fcb465c99): Remove socket_timeout from the redis client (PROJQUAY-2542) ([#1084](https://github.com/quay/quay/issues/1084))
- [b7d325ed](https://github.com/quay/quay/commit/b7d325ed42827db9eda2d9f341cb5a6cdfd155a6): Make single_connection_client conifgurable (PROJQUAY-3025) ([#1055](https://github.com/quay/quay/issues/1055))
### Buildman
- [a79f7b6f](https://github.com/quay/quay/commit/a79f7b6f4063b38a8caeceb38975ac0f37ea1c57): increase allowed grpc body size for log streams ([#1234](https://github.com/quay/quay/issues/1234))
- [ceb9262b](https://github.com/quay/quay/commit/ceb9262b7e5484fe7cd0e050e24c014c7e78c68c): Add EXECUTOR parameter (PROJQUAY-3278) ([#1134](https://github.com/quay/quay/issues/1134))
- [3ca44073](https://github.com/quay/quay/commit/3ca44073b17a0c42f98d44811224652a05e306cd): prevent systemd oneshot service from timing (PROJQUAY-3304) ([#1149](https://github.com/quay/quay/issues/1149))
- [32691dd8](https://github.com/quay/quay/commit/32691dd8127fc23910a80edfc84cf70ba25fb806): Set build token expiration to builder's lifetime (PROJQUAY-3281) ([#1142](https://github.com/quay/quay/issues/1142))
- [a0443340](https://github.com/quay/quay/commit/a0443340cb57d9dba4a3dea9d335cf0e3ad29679): fix multiple build retries phase (PROJQUAY-3281) ([#1139](https://github.com/quay/quay/issues/1139))
- [9b892626](https://github.com/quay/quay/commit/9b89262640022250d9c3be7b4611bc2bf1758419): configurable build job registration timeout (PROJQUAY-3280) ([#1135](https://github.com/quay/quay/issues/1135))
- [a29e64be](https://github.com/quay/quay/commit/a29e64be187a057850fea8f34b809e6699809b43): Add kubernetesPodman build option (PROJQUAY-3052) ([#1066](https://github.com/quay/quay/issues/1066))
- [eaaa3adb](https://github.com/quay/quay/commit/eaaa3adbf05422a2625946e7cc5d7999d4325430): allow use of public builder image (PROJQUAY-3179) ([#1103](https://github.com/quay/quay/issues/1103))
- [b07b44a7](https://github.com/quay/quay/commit/b07b44a7eb2b70282e0cfb07362d33fc3666c358): fix kubernetes not returning correct running count (PROJQUAY-3169) ([#1099](https://github.com/quay/quay/issues/1099))
### CONTRIBUTING
- [f0edbceb](https://github.com/quay/quay/commit/f0edbceb5b24c1a5298eeece77e53de9ef643372): document backporting process ([#1043](https://github.com/quay/quay/issues/1043))
### Cache
- [ccf6ada1](https://github.com/quay/quay/commit/ccf6ada16a1feac137a8aa7ea828a99df66586ac): handle uncaught redis exception (PROJQUAY-2614) ([#907](https://github.com/quay/quay/issues/907))
### Chore
- [c2ceda5a](https://github.com/quay/quay/commit/c2ceda5a26d3106ef6672fa31e8212ba4cb902ab): various small changes to fix exceptions, remove unused code ([#1295](https://github.com/quay/quay/issues/1295))
- [2d56a8df](https://github.com/quay/quay/commit/2d56a8dfba0cf305a43aad82af382bc48b06911a): add logging during instance service key generation ([#1276](https://github.com/quay/quay/issues/1276))
- [5c226105](https://github.com/quay/quay/commit/5c226105e83b5884d4832ae4bcd47771e362859c): Fix cachito issue with pypdf (PROJQUAY-3184) ([#1223](https://github.com/quay/quay/issues/1223))
- [a3ad25c4](https://github.com/quay/quay/commit/a3ad25c48a04bd3319f1b393e0b1f2886a6269b9): Remove unneeded flags fromt he config schema ([#1152](https://github.com/quay/quay/issues/1152))
- [2344adb8](https://github.com/quay/quay/commit/2344adb8194bd026572903f8784003ebd8e81b7c): remove unused tools (PROJQUAY-0) ([#1113](https://github.com/quay/quay/issues/1113))
- [9bdbba6f](https://github.com/quay/quay/commit/9bdbba6ff946042709aa91bb9d80193120aba785): Remove unused files ([#1067](https://github.com/quay/quay/issues/1067))
- [65100439](https://github.com/quay/quay/commit/65100439f6dd70b12db2276ec61cff99704bfa4e): download aws ip ranges via github workflow ([#1041](https://github.com/quay/quay/issues/1041))
- [b7037d9c](https://github.com/quay/quay/commit/b7037d9c50bf7a282c7983577b380cfc401b7825): Bump up config-tool version v0.1.9 ([#992](https://github.com/quay/quay/issues/992))
- [2ffc12b3](https://github.com/quay/quay/commit/2ffc12b3eb5e36c070df80fcd5ffffa9593fd22a): cleanup remaining artifacts remaining related to aci signing (PROJQUAY-2792) ([#968](https://github.com/quay/quay/issues/968))
- [ae129b45](https://github.com/quay/quay/commit/ae129b45e9db29f4e787e0190afc6af4c29ec277): Bump up config-tool version v0.1.8 ([#984](https://github.com/quay/quay/issues/984))
- [c8092069](https://github.com/quay/quay/commit/c8092069a296726fe888f6c3b8f4e15d8f7958e8): Bump up config-tool version ([#983](https://github.com/quay/quay/issues/983))
- [ba08ddd7](https://github.com/quay/quay/commit/ba08ddd707e7ac4b6e29460deef533eb23c6036f): Bump up config-tool version ([#982](https://github.com/quay/quay/issues/982))
- [bbacf232](https://github.com/quay/quay/commit/bbacf2321facf0fbb7fdc407799623943fa14fea): bump gevent related packages' version (PROJQUAY-2821) ([#979](https://github.com/quay/quay/issues/979))
- [8ef0aff8](https://github.com/quay/quay/commit/8ef0aff83dffac3ae32938dc9105a5926a94c10d): improve check for JIRA ticket (PROJQUAY-2623) ([#919](https://github.com/quay/quay/issues/919))
- [c90b444f](https://github.com/quay/quay/commit/c90b444f8322a425ebd718809eac25c3c7cae265): Provide timestamps on container startup including registry, mirror and config container ([#921](https://github.com/quay/quay/issues/921))
- [16dcebf1](https://github.com/quay/quay/commit/16dcebf101f807738868711246614a9dd10f5566): build and publish workflow (PROJQUAY-2556)
- [79703a91](https://github.com/quay/quay/commit/79703a91760a7e7fbbadf9ebec6a85fe72a35b78): Move qemu outside of quay repo to its github repo (PROJQUAY-2342) ([#866](https://github.com/quay/quay/issues/866))
### Chore(Dockerfile)
- [0f7fdb7e](https://github.com/quay/quay/commit/0f7fdb7e847df7ac68154c7627486c5ca048736c): add local-dev-env build stage (PROJQUAY-2501) ([#883](https://github.com/quay/quay/issues/883))
### Chore: V3.6.3 Changelog Bump (Https
- [62e2eac1](https://github.com/quay/quay/commit/62e2eac1b083dc6a6c0cdc882f8494ef9dfcf999): //issues.redhat.com/browse/PROJQUAY-3028) ([#1118](https://github.com/quay/quay/issues/1118))
### Chore: V3.6.4 Changelog Bump (Https
- [992bc5c3](https://github.com/quay/quay/commit/992bc5c3ccb1474c0dc1d5a576363dc9d01ff2d7): //issues.redhat.com/browse/PROJQUAY-3335) ([#1162](https://github.com/quay/quay/issues/1162))
### Chore: V3.6.5 Changelog Bump (Https
- [81db4e84](https://github.com/quay/quay/commit/81db4e84bb415a475956dbb6c76bbd11080b09b7): //issues.redhat.com/browse/PROJQUAY-3354) ([#1211](https://github.com/quay/quay/issues/1211))
### Chore: V3.6.6 Changelog Bump (Https
- [d8a76c0d](https://github.com/quay/quay/commit/d8a76c0d3c10d4ff08f55bfddde181b9611007b5): //issues.redhat.com/browse/PROJQUAY-3635) ([#1278](https://github.com/quay/quay/issues/1278))
### Chore: V3.7.0 Changelog Bump (Https
- [8a54431d](https://github.com/quay/quay/commit/8a54431dd5931aad81ef3d9f52780686ff53eabf): //issues.redhat.com/browse/PROJQUAY-2411) ([#1338](https://github.com/quay/quay/issues/1338))
### Ci
- [e2921d7a](https://github.com/quay/quay/commit/e2921d7af8d3d2ed3bc8f44c939bfcc6b340c52b): Enable workflow dispatch for build and publish (PROJQUAY-3310) ([#1155](https://github.com/quay/quay/issues/1155))
- [c7c4c0dc](https://github.com/quay/quay/commit/c7c4c0dc4ca9681482a100a831950355634c3b61): Update funcparserlib version (PROJQUAY-2520) ([#893](https://github.com/quay/quay/issues/893))
### Clean.Sh
- [6b5e7f50](https://github.com/quay/quay/commit/6b5e7f506fe6cbb124ede711d9480e5f39eb70f1): don't remove webfonts dir since its now versioned ([#1025](https://github.com/quay/quay/issues/1025))
### Cleanup
- [687abaa2](https://github.com/quay/quay/commit/687abaa2d73eaf99dea5c0ddf078ec6fc656ce30): Removing requirements-nover.txt (PROJQUAY-2985) ([#1038](https://github.com/quay/quay/issues/1038))
### Compliance
- [ad4bb6f1](https://github.com/quay/quay/commit/ad4bb6f185d312f582ad8a174fce498b95c2a5dd): Move export screening to RHSSO class (PROJQUAY-2056) ([#1302](https://github.com/quay/quay/issues/1302))
### Conf
- [a07ba480](https://github.com/quay/quay/commit/a07ba480559ef71981e536e2243dd190c2bd79dd): fix supervisord chunk worker template ([#1259](https://github.com/quay/quay/issues/1259))
### Config
- [e659e809](https://github.com/quay/quay/commit/e659e8092a17a1d78aa1fedbd8c8c91c2bf83d21): Update config-tool to v0.1.11 (PROJQUAY-3318) ([#1195](https://github.com/quay/quay/issues/1195))
- [c1cc7c53](https://github.com/quay/quay/commit/c1cc7c531d060723ed92ea60de1119987a202c30): Allow envelope mediatype (PROJQUAY-3386) ([#1196](https://github.com/quay/quay/issues/1196))
- [c02f912f](https://github.com/quay/quay/commit/c02f912f4364ab1a4299a9e576f99825cadaefbb): Update config-tool version to v0.1.10 (PROJQUAY-3125) ([#1078](https://github.com/quay/quay/issues/1078))
- [c507eeff](https://github.com/quay/quay/commit/c507eeff2eae61efe1a18a4b0e6addce4d37bc5a): define default oci artifact types (PROJQUAY-2334) ([#877](https://github.com/quay/quay/issues/877))
### Config.Py
- [d14da17a](https://github.com/quay/quay/commit/d14da17a401caed79e87a3685b554a0007e5de51): Add support for source containers (PROJQUAY-2271) ([#954](https://github.com/quay/quay/issues/954))
### Data
- [a4ed9866](https://github.com/quay/quay/commit/a4ed9866089b43de9dbc3947fc5b340d5e71bc82): increase max len for proxy cache config credentials ([#1241](https://github.com/quay/quay/issues/1241))
### Data/Buildlogs
- [e1ae52ee](https://github.com/quay/quay/commit/e1ae52ee23deec4ccaf76e2f3ef04f7e79a6fa4c): format file with black ([#1061](https://github.com/quay/quay/issues/1061))
### Database
- [24b3c153](https://github.com/quay/quay/commit/24b3c15334dd354f16ed79a766dcaba43561cf5a): handle nested transaaction when trying to close before transaction (PROJQUAY-3303) ([#1157](https://github.com/quay/quay/issues/1157))
- [7cdb88b5](https://github.com/quay/quay/commit/7cdb88b5789987c492666de381a666c5afce8ef3): force close existing non-pooled connections before transaction (PROJQUAY-3303) ([#1153](https://github.com/quay/quay/issues/1153))
- [c5608d97](https://github.com/quay/quay/commit/c5608d976511e5645b3c879908d7f839323a83cd): retry connections on stale MySQL connections (PROJQUAY-3303) ([#1148](https://github.com/quay/quay/issues/1148))
### Db
- [eb62f4e9](https://github.com/quay/quay/commit/eb62f4e999768a3a5acc68957e7198435ef432ad): remove url unqoute from migration logic (PROJQUAY-3266) ([#1126](https://github.com/quay/quay/issues/1126))
### Debug
- [9c327425](https://github.com/quay/quay/commit/9c32742514129207b95838979a708db9e1b3f48a): Log X-Forwaded-For for requests (PROJQUAY-2883) ([#1027](https://github.com/quay/quay/issues/1027))
- [4a02e1bd](https://github.com/quay/quay/commit/4a02e1bd0955b2cffd1805830274607c9b8c932d): Log X-Forwaded-For for requests (PROJQUAY-2883) ([#1026](https://github.com/quay/quay/issues/1026))
### Defaults
- [a29f3e0e](https://github.com/quay/quay/commit/a29f3e0eea6d475d6f621da19b083876737d5262): Update defaults in config and schema (PROJQUAY-2425) ([#923](https://github.com/quay/quay/issues/923))
### Deploy
- [6356fbb1](https://github.com/quay/quay/commit/6356fbb1b9cdddbe1e231d01b196ce7cf926bbb7): Add ignore validation for py3 deployment (PROJQUAY-2542) ([#1121](https://github.com/quay/quay/issues/1121))
- [d43b41c5](https://github.com/quay/quay/commit/d43b41c58a8c53dfc49458e2743fe915725fe269): Add GRPC service for builds (PROJQUAY-3189) ([#1109](https://github.com/quay/quay/issues/1109))
- [293e0619](https://github.com/quay/quay/commit/293e0619de040994331f4437a0b35dac5d10f323): Add LB service with no proxy-protocol (PROJQUAY-2883) ([#1006](https://github.com/quay/quay/issues/1006))
- [1589351b](https://github.com/quay/quay/commit/1589351b7433941411ec4e12d1a3fe9cfdcc5c31): Add clair back fill worker deployment manifests ([#991](https://github.com/quay/quay/issues/991))
- [01d41364](https://github.com/quay/quay/commit/01d4136406e237b32c80d35f6123b2c0b53f5b93): Update syslog image tag(PROJQUAY-2374) ([#966](https://github.com/quay/quay/issues/966))
- [7458578d](https://github.com/quay/quay/commit/7458578d1a5fe669e2d2b4f943360a7acaacac54): Seperate py3 deployment manifests (PROJQUAY-2374) ([#931](https://github.com/quay/quay/issues/931))
- [5a56145b](https://github.com/quay/quay/commit/5a56145ba5d49702430b030b84df8a66426b77c8): Update app-sre build script (PROJQUAY-2374) ([#934](https://github.com/quay/quay/issues/934))
- [6b01bd12](https://github.com/quay/quay/commit/6b01bd124531e428b2ebd99f9f4f59c5907a024c): Push py3 images to a different quay repo (PROJQUAY-2374) ([#930](https://github.com/quay/quay/issues/930))
- [173dfbfc](https://github.com/quay/quay/commit/173dfbfc8adf67286e22e1f5daadf984d5fcbf3d): Update quay deployment manifests for py3 canary (PROJQUAY-2373) ([#902](https://github.com/quay/quay/issues/902))
### Deps
- [bb53127d](https://github.com/quay/quay/commit/bb53127d015c6e9c2fee0643281667c539905f4b): upgrade upstream requirements.txt package versions ([#1072](https://github.com/quay/quay/issues/1072))
### Dockerfile
- [50d2a827](https://github.com/quay/quay/commit/50d2a82783da906a3a68064fe0b9ab10e956f550): ubi8 requires python38, otherwise installs 3.6 by default (PROJQUAY-3148) ([#1092](https://github.com/quay/quay/issues/1092))
- [5267cfe7](https://github.com/quay/quay/commit/5267cfe75189de7df7e61a4daa9ea4570de81cfe): update upstream image to use ubi8 as base (PROJQUAY-3148) ([#1082](https://github.com/quay/quay/issues/1082))
- [085e33be](https://github.com/quay/quay/commit/085e33bed74957fc083a03868bb7bfb1b892dc48): set QUAYRUN in non-standard dockerfiles ([#1013](https://github.com/quay/quay/issues/1013))
- [cdc7b61f](https://github.com/quay/quay/commit/cdc7b61f9e1be90d4dbd621810ea7c30a45bb75a): make sure the production dockerfile doesn't pull from dockerhub ([#929](https://github.com/quay/quay/issues/929))
- [da558b0f](https://github.com/quay/quay/commit/da558b0f68228fad28a7cf3b6019f76dc5355e6d): replace golang base image in production dockerfile ([#928](https://github.com/quay/quay/issues/928))
- [139c9abc](https://github.com/quay/quay/commit/139c9abc66c5f60ec9eaf910057afdb28734413b): use separate dockerfile for production deployment ([#927](https://github.com/quay/quay/issues/927))
- [495dd908](https://github.com/quay/quay/commit/495dd9086ea5ac8bb19b0ac175414df1be85aad3): Update symlink in upstream dockerfile (PROJQUAY-2550) ([#889](https://github.com/quay/quay/issues/889))
### Docs
- [8f64efd6](https://github.com/quay/quay/commit/8f64efd6815a76cd27139da5df16983213c71048): consolidate getting started guides (PROJQUAY-2500) ([#884](https://github.com/quay/quay/issues/884))
### Documentation
- [ae0bd06d](https://github.com/quay/quay/commit/ae0bd06d1dc1124a6b64460884d369d0af997f4a): Added instructions to setup dev environment (PROJQUAY-2277) ([#844](https://github.com/quay/quay/issues/844)) ([#844](https://github.com/quay/quay/issues/844))
### Editor
- [6f7dea7f](https://github.com/quay/quay/commit/6f7dea7f84faeaf7b07b8cc0c5f5063dcbb4fe13): Bump config tool to v0.1.12 (PROJQUAY-3593) ([#1267](https://github.com/quay/quay/issues/1267))
### Email
- [d81efe2f](https://github.com/quay/quay/commit/d81efe2f3ce545a398a2fba0b4fdc4ac7559376b): fix org recovery link in email (PROJQUAY-2589) ([#903](https://github.com/quay/quay/issues/903))
### Endpoints/V2
- [59875347](https://github.com/quay/quay/commit/59875347186757111a6324d29bc2ea64e0f9d499): handle generic proxy related errors ([#1213](https://github.com/quay/quay/issues/1213))
### Feat
- [fe4d66b0](https://github.com/quay/quay/commit/fe4d66b03061078547f517340fba044f459abc5e): pull-thru proxy cache ([#1053](https://github.com/quay/quay/issues/1053))
- [fca67e77](https://github.com/quay/quay/commit/fca67e7729d95e8cafee5029ca08f503c803a51e): mypy type annotations (PROJQUAY-740) ([#455](https://github.com/quay/quay/issues/455))
### Fix
- [d3809b2e](https://github.com/quay/quay/commit/d3809b2e36a926721119726070d465c875110085): pin setuptools to version 57 ([#885](https://github.com/quay/quay/issues/885))
### Fix
- [c82d78ae](https://github.com/quay/quay/commit/c82d78ae8501b040c7539a3e539aaab0485d1052): Adding default vault to quota parameter (PROJQUAY-0000) ([#1171](https://github.com/quay/quay/issues/1171))
### Format
- [ef91c57c](https://github.com/quay/quay/commit/ef91c57c233e9d23372afac34c0d062a38171ffa): Updating black to resolve click dependency issue (PROJQUAY-3487) ([#1209](https://github.com/quay/quay/issues/1209))
### Formatting
- [e4390472](https://github.com/quay/quay/commit/e4390472a47368a42f2fec8c6cef8c428d0ef980): Update code to obey the linter (PROJQUAY-0) ([#1057](https://github.com/quay/quay/issues/1057))
### Gc
- [563d04aa](https://github.com/quay/quay/commit/563d04aa00dce607af8671c2a7fa9599b279478c): remove orphaned storage on repository purge (PROJQUAY-2313) ([#961](https://github.com/quay/quay/issues/961))
### Imagemirror
- [0d3ecb13](https://github.com/quay/quay/commit/0d3ecb132e8afe6eb4184948e05a9717759b70c3): Add unsigned registries mirror option (PROJQUAY-3106) ([#1085](https://github.com/quay/quay/issues/1085))
### Invoice
- [5a1fa17a](https://github.com/quay/quay/commit/5a1fa17a799800f09a9bf447a5c83e3b01bd3ef1): update invoice template to fix layout (PROJQUAY-3267) ([#1182](https://github.com/quay/quay/issues/1182))
### Ipresolver
- [b9557d14](https://github.com/quay/quay/commit/b9557d1486e9a70c0659d8d6d94bae4d053c4eb6): update country mmdb (PROJQUAY-3031) ([#1049](https://github.com/quay/quay/issues/1049))
### Ldap
- [c8a7e641](https://github.com/quay/quay/commit/c8a7e6412aecd3a732aaf9681398c2fe1aa1b382): add test for user filter (PROJQUAY-2766) ([#980](https://github.com/quay/quay/issues/980))
### Makefile
- [10e88d29](https://github.com/quay/quay/commit/10e88d29aa518c53da33da800309cdd3310925a4): Add local-dev-build-frontend step (PROJQUAY-2693) ([#933](https://github.com/quay/quay/issues/933))
### Migration
- [08201dea](https://github.com/quay/quay/commit/08201deaec55fc358e3a395b58ab00c9ee408f4c): skip existing mediatype inserts (PROJQUAY-2811) ([#976](https://github.com/quay/quay/issues/976))
- [712b8d74](https://github.com/quay/quay/commit/712b8d749333e9879d15ecf724d335662ddb7af1): configure logging in alembic's env.py (PROJQUAY-2412) ([#875](https://github.com/quay/quay/issues/875))
### Mirror
- [d2e758da](https://github.com/quay/quay/commit/d2e758dad5a6c01f88e257885f07a4e51f66712a): Get all tags during rollback (PROJQUAY-3146) ([#1244](https://github.com/quay/quay/issues/1244))
- [f3a8b74d](https://github.com/quay/quay/commit/f3a8b74dafb0633b6539d1187b85923a1079ea4e): increased registry user/pass max length (PROJQUAY-2712) ([#945](https://github.com/quay/quay/issues/945))
### Namespacequota
- [61f4bd42](https://github.com/quay/quay/commit/61f4bd4252e5780ef1d1a699bc142bb665586014): return 0 when namespace has no size yet ([#1237](https://github.com/quay/quay/issues/1237))
### Nginix
- [2a38784a](https://github.com/quay/quay/commit/2a38784a689434bd9484cb35cdc49f12dbcc0341): update rate limit values for quay based on traffic (PROJQUAY-3283) ([#1175](https://github.com/quay/quay/issues/1175))
### Nginx
- [aa7068a2](https://github.com/quay/quay/commit/aa7068a2cc32169c92fb2838951c8067714a6136): block v1/tag for helium miner curl calls (PROJQUAY-3594) ([#1248](https://github.com/quay/quay/issues/1248))
- [7b44f8c0](https://github.com/quay/quay/commit/7b44f8c0d0729515a95ab243e852975e78c0b4fc): Update rate limiting for tags API (PROJQUAY-3283) ([#1233](https://github.com/quay/quay/issues/1233))
- [de0d9764](https://github.com/quay/quay/commit/de0d97640f0e471ae56ded9446d36116513e920f): Increase body timeout for buildman (PROJQUAY-3406) ([#1198](https://github.com/quay/quay/issues/1198))
- [ec7b7610](https://github.com/quay/quay/commit/ec7b7610acff9d585053491eb902032dfc835389): add missing semicolon in template (PROJQUAY-2883) ([#1020](https://github.com/quay/quay/issues/1020))
- [03a36256](https://github.com/quay/quay/commit/03a3625650d4e5aa92aafc5325eefc9712443972): rename base http template file ((PROJQUAY-2883) ([#1007](https://github.com/quay/quay/issues/1007))
- [1ba53f4f](https://github.com/quay/quay/commit/1ba53f4f09a46586f970735250f8d9570732c736): support client ip through x-forwarded-for header (PROJQUAY-2883) ([#1003](https://github.com/quay/quay/issues/1003))
- [630d6f46](https://github.com/quay/quay/commit/630d6f4605124de2a799f17447bab097fff67398): use bigger http/2 chunks for blobs ([#630](https://github.com/quay/quay/issues/630))
### Notification
- [3739c1fc](https://github.com/quay/quay/commit/3739c1fc21223df260874aa4793b6c2b10343e7b): fix user ref when creating notification for quota (PROJQUAY-3711) ([#1288](https://github.com/quay/quay/issues/1288))
- [a126ad06](https://github.com/quay/quay/commit/a126ad06d5a48f54188f32d0aa17ad8172aba8fc): check certs exists for webhooks (PROJQUAY-2424) ([#886](https://github.com/quay/quay/issues/886))
### Oci
- [f50f37a3](https://github.com/quay/quay/commit/f50f37a393fa2273234f8ac0aa9f34a03a77a731): Accept the stricter oci layer type used by default in Helm 3.7 (PROJQUAY-2653) ([#922](https://github.com/quay/quay/issues/922))
### PROJQUAY-3750
- [2e2fefe5](https://github.com/quay/quay/commit/2e2fefe5e5c734f1e99fa20a47c10bf74ea28768): support registries that do not return a digest header ([#1313](https://github.com/quay/quay/issues/1313))
### Proxy
- [1342a17b](https://github.com/quay/quay/commit/1342a17b63f3c9f27c09d294923f4499939e7ba7): make upstream related error message more actionable ([#1240](https://github.com/quay/quay/issues/1240))
- [b941a038](https://github.com/quay/quay/commit/b941a0384c19f94cbb8a5a7ef1e1086533ab1b07): raise UpstreamRegistryError if we can't request upstream ([#1220](https://github.com/quay/quay/issues/1220))
- [f248d885](https://github.com/quay/quay/commit/f248d885aab2d95c25c14e73774a8e1940855bc7): don't store entire blob in memory when caching ([#1200](https://github.com/quay/quay/issues/1200))
### Proxy Cache
- [a4c8924f](https://github.com/quay/quay/commit/a4c8924f11d66a34ce3d178d5ed34332cfb3c3a2): Elaborate hint message for anonymous pulls and making a safe request (PROJQUAY - 0000) ([#1222](https://github.com/quay/quay/issues/1222))
### Proxy Cache
- [7524171a](https://github.com/quay/quay/commit/7524171ac8fa1db2a450b96dd2b4240f1512afc5): Interface and UI for Proxy cache Configuration (PROJQUAY-3029) ([#1204](https://github.com/quay/quay/issues/1204))
### Quay
- [162b79ec](https://github.com/quay/quay/commit/162b79ec53b1a38ac4dbbb7e00224a308f7ba3c7): Fixing reclassified CVE ratings source (PROJQUAY-2691) ([#937](https://github.com/quay/quay/issues/937))
### Quay UI
- [51c67513](https://github.com/quay/quay/commit/51c675139defa49c17c7847e89889af4d783cf4f): Converting to nearest integer (PROJQUAY-3602) ([#1285](https://github.com/quay/quay/issues/1285))
### Quay.Io
- [5debec58](https://github.com/quay/quay/commit/5debec58f97ea435ff0826c56202f31bef8c318f): Catching requests from impersonated principals ([#869](https://github.com/quay/quay/issues/869))
### Quay.Io UI
- [20aef6a5](https://github.com/quay/quay/commit/20aef6a589c06d980f24eb866f2328f99b3b2623): Fetching severity from cvss score and removing visibility… ([#887](https://github.com/quay/quay/issues/887))
### Quayio
- [247fec3b](https://github.com/quay/quay/commit/247fec3b0511eef3f5dc58633051a5dab4bc0f2e): Add export compliance service to Red Hat SSO (PROJQUAY-2056) ([#1239](https://github.com/quay/quay/issues/1239))
- [34cf5b92](https://github.com/quay/quay/commit/34cf5b922692ce1d122e9a9f920950e7782a37cd): allow migration to skip adding manifest columns if exists (PROJQUAY-2579) ([#901](https://github.com/quay/quay/issues/901))
### Quota
- [477ccd82](https://github.com/quay/quay/commit/477ccd82f5b96c91933a0225075ce8526b513720): address possible integrity exception if computing size concurrently (PROJQUAY-3752) ([#1308](https://github.com/quay/quay/issues/1308))
### Quota
- [f4093b0d](https://github.com/quay/quay/commit/f4093b0db58fbe4dc4663a948e61d3af09f24653): fix caching (PROJQUAY-3660) ([#1291](https://github.com/quay/quay/issues/1291))
- [1e65bff9](https://github.com/quay/quay/commit/1e65bff9fc7b543b03efe3a665a1c74147b83d43): Raising exception when entered quota size is too big (PROJQUAY-3702) ([#1290](https://github.com/quay/quay/issues/1290))
- [5bb2c121](https://github.com/quay/quay/commit/5bb2c121b1466ccd909ffd746cfe1bc185437f8e): Show a different error message if default quota is set on removing quota (PROJQUAY-3657) ([#1287](https://github.com/quay/quay/issues/1287))
- [eea7389a](https://github.com/quay/quay/commit/eea7389a244d26b54a38d876ce3dd949445f1390): Show system default on UI when quota configuration for the org is not set (PROJQUAY-3518) ([#1280](https://github.com/quay/quay/issues/1280))
### Quota API
- [a983884e](https://github.com/quay/quay/commit/a983884e0fe3436acb9cd7f59fdcfcf0e15fe866): Add super user permissions on Organization endpoints (PROJQUAY-3742) ([#1296](https://github.com/quay/quay/issues/1296))
- [2d63be37](https://github.com/quay/quay/commit/2d63be373f69ea03e47864f4681d7fb36b3499d1): Remove trailing backslash (PROJQUAY-3625) ([#1286](https://github.com/quay/quay/issues/1286))
### Quota Management
- [cd288943](https://github.com/quay/quay/commit/cd2889439b6e55e269916d1d5e62fe66d15fb430): Quota settings on Organization view needs to be read only (PROJQUAY-3622) ([#1263](https://github.com/quay/quay/issues/1263))
### Quota UI
- [d8a7a6d0](https://github.com/quay/quay/commit/d8a7a6d0dcc32c5f52471c0c04eb0625b73e865d): Adding Overall storage consumption for Super users panel page (PROJQUAY-3639) ([#1314](https://github.com/quay/quay/issues/1314))
- [a57594cf](https://github.com/quay/quay/commit/a57594cf017ef043037eb950e8171e086b177720): Fix quota input value (PROJQUAY-3691) ([#1293](https://github.com/quay/quay/issues/1293))
- [03269edc](https://github.com/quay/quay/commit/03269edcbe4f0f499e225905fc3df29a28f0681a): Show message that System wide default cannot be removed from an organization (PROJQUAY-3658) ([#1282](https://github.com/quay/quay/issues/1282))
- [f10690e7](https://github.com/quay/quay/commit/f10690e7d3512a7658bae8779aeae382d9064a3f): Display Error when decimal values entered from UI (PROJQUAY-3627) ([#1272](https://github.com/quay/quay/issues/1272))
- [3176d5ba](https://github.com/quay/quay/commit/3176d5ba41a8c5b0d91e1d1d4b0ea438999d2ea6): Syntax fix to throw error on 0 input (PROJQUAY-3419) ([#1253](https://github.com/quay/quay/issues/1253))
- [923fc72a](https://github.com/quay/quay/commit/923fc72a2821f22a76c07ab90b5e1de707113cae): Showing percent consumed if quota is configured on an organization (PROJQUAY-0000) ([#1249](https://github.com/quay/quay/issues/1249))
### QuotaManagement
- [15fa20a1](https://github.com/quay/quay/commit/15fa20a115b2e82daaa281d2500bfcc902611b1b): Reporting (PROJQUAY-2936) ([#1048](https://github.com/quay/quay/issues/1048))
### Realtime
- [a058235b](https://github.com/quay/quay/commit/a058235b520ea4c1ec7cb9b9c64d6f41a05fc7d9): decode byte to string before using split (PROJQUAY-3180) ([#1107](https://github.com/quay/quay/issues/1107))
### Refactor(Dockerfile)
- [5ad6e0ff](https://github.com/quay/quay/commit/5ad6e0ffa70cd064b8fe47457f8ec805ab7becb9): use pre-built centos 8 stream ([#936](https://github.com/quay/quay/issues/936))
### Registry
- [32322bc1](https://github.com/quay/quay/commit/32322bc1f6bfc919c4366d6063bffb96be491d5a): update blob mount behaviour when from parameter is missing (PROJQUAY-2570) ([#899](https://github.com/quay/quay/issues/899))
### Registry_proxy_model
- [514bc6f1](https://github.com/quay/quay/commit/514bc6f1bab18741520f8ddcb77a6421e04752c9): count repository size when caching images (PROJQUAY-3464) ([#1215](https://github.com/quay/quay/issues/1215))
### Requirements
- [5c11e7a6](https://github.com/quay/quay/commit/5c11e7a6a64927e46d9c1d7eea68e5c5ab5db2ae): bump cryptography package version ([#939](https://github.com/quay/quay/issues/939))
### Requirements-Osbs
- [12705e49](https://github.com/quay/quay/commit/12705e49c81dd2b932539c1231b47cd80739c689): upgrade cryptography package ([#943](https://github.com/quay/quay/issues/943))
### Requirements-Osbs.Txt
- [f3e016f4](https://github.com/quay/quay/commit/f3e016f4f984286edb3cc0d8a50a5b80dc92e897): remove ipython and related deps ([#1069](https://github.com/quay/quay/issues/1069))
### Requirements.Txt
- [897e7e39](https://github.com/quay/quay/commit/897e7e3913c0c18436a41b71f582817e8a273187): remove unused dependencies ([#948](https://github.com/quay/quay/issues/948))
### Revert "Quayio
- [8324586e](https://github.com/quay/quay/commit/8324586e4c577187148a10c93d03ecd2bd34c884): Add export compliance service to Red Hat SSO (PROJQUAY-2056) ([#1239](https://github.com/quay/quay/issues/1239))" ([#1273](https://github.com/quay/quay/issues/1273))
### Revert "Revert "Quayio
- [3140a62e](https://github.com/quay/quay/commit/3140a62e017ae2f19995ca94b1bd3f2bd1c36778): Add export compliance service to Red Hat SSO (PROJQUAY-2056) ([#1239](https://github.com/quay/quay/issues/1239))" ([#1273](https://github.com/quay/quay/issues/1273))" ([#1289](https://github.com/quay/quay/issues/1289))
### Revert "Schema1
- [58b06572](https://github.com/quay/quay/commit/58b065725527ee84fdae3fdf9a7206a860101c68): Permit signed schema1 manifests during conversion (PROJQUAY-PROJQUAY-3285) ([#1146](https://github.com/quay/quay/issues/1146))" ([#1150](https://github.com/quay/quay/issues/1150))
### Revert "Secscan
- [dd1eab52](https://github.com/quay/quay/commit/dd1eab52384c440f1710dc0f95837048e8e4f72c): add a global lock on security worker runs (PROJQUAY-3501) ([#1226](https://github.com/quay/quay/issues/1226))" ([#1232](https://github.com/quay/quay/issues/1232))
### Schema1
- [b5bd74bf](https://github.com/quay/quay/commit/b5bd74bf051e5de81fede6b386b3fbd178d7b8a8): Permit signed schema1 manifests during conversion (PROJQUAY-PROJQUAY-3285) ([#1146](https://github.com/quay/quay/issues/1146))
### Secscan
- [3acc55b9](https://github.com/quay/quay/commit/3acc55b96c0c64e9fcdbd6af359579a0714406b1): split the recent manifest chunk of work into multiple batch (PROJQUAY-3501) ([#1300](https://github.com/quay/quay/issues/1300))
- [f3c3916b](https://github.com/quay/quay/commit/f3c3916bc732642bca747c252d4764814441dd9a): add option to skip recent manifest batch lock (PROJQUAY-3501) ([#1299](https://github.com/quay/quay/issues/1299))
- [9ac30007](https://github.com/quay/quay/commit/9ac30007f9ded33e1f8123ae887b730e97de7709): cleanup secscan interface (PROJQUAY-3501) ([#1284](https://github.com/quay/quay/issues/1284))
- [72c8d7a3](https://github.com/quay/quay/commit/72c8d7a3c51dbb409326826ff444d72cf6cca984): fix config reference (PROJQUAY-3501) ([#1283](https://github.com/quay/quay/issues/1283))
- [ed77147b](https://github.com/quay/quay/commit/ed77147b2166160b9d0d09cda23e90fea2d20e44): split indexing of recent manifest into separate background operation (PROJQUAY-3501) ([#1281](https://github.com/quay/quay/issues/1281))
- [035f5820](https://github.com/quay/quay/commit/035f58207532e4254546ea1691a0a74592047682): fix check for end of table (PROJQUAY-3501) ([#1270](https://github.com/quay/quay/issues/1270))
- [a9e1b71a](https://github.com/quay/quay/commit/a9e1b71a2c34dd88a2e15f2a881d9b4afcfe83e3): fix missing import (PROJQUAY-3501) ([#1261](https://github.com/quay/quay/issues/1261))
- [922892d1](https://github.com/quay/quay/commit/922892d1af262d2eb18f9a9dba05cd6efc2d91e2): configure global lock (PROJQUAY-3501) ([#1255](https://github.com/quay/quay/issues/1255))
- [7d0f318b](https://github.com/quay/quay/commit/7d0f318baa62289137911c5f350a98c844866ce9): update the secscan model interface (PROJQUAY-3501) ([#1254](https://github.com/quay/quay/issues/1254))
- [d719dfad](https://github.com/quay/quay/commit/d719dfadc5f89eca4563337ef085ba7effbac23c): optimize deduplicating manifests for indexing in securityworker (PROJQUAY-3501) ([#1247](https://github.com/quay/quay/issues/1247))
- [53aaa549](https://github.com/quay/quay/commit/53aaa5493bf2c0bbc627fd70cb0fd273f75be076): add indexer service request duration metric (PROJQUAY-3501) ([#1243](https://github.com/quay/quay/issues/1243))
- [a52b0026](https://github.com/quay/quay/commit/a52b00263a5d71c85fa0201fe2b5b15ed8f8ee53): fix database manifest allocator for securityworker (PROJQUAY-3501) ([#1235](https://github.com/quay/quay/issues/1235))
- [9d89b6fa](https://github.com/quay/quay/commit/9d89b6fa47dec4ab0c182d88f56772303adc09a6): add a global lock on security worker runs (PROJQUAY-3501) ([#1226](https://github.com/quay/quay/issues/1226))
- [4295a8f6](https://github.com/quay/quay/commit/4295a8f6604144049b59233371bf508edf3cffc0): scan recent manifests in addition to regular backfill (PROJQUAY-3287) ([#1169](https://github.com/quay/quay/issues/1169))
- [6a8567f8](https://github.com/quay/quay/commit/6a8567f830db1f4835a6e585a8ce3b74f78f94eb): log manifest ID when indexing (PROJQUAY-3287) ([#1166](https://github.com/quay/quay/issues/1166))
- [2b2e795b](https://github.com/quay/quay/commit/2b2e795b9c65e055c221304c43ef5cdbe91c563e): Log start and end index of block in clair (PROJQUAY-3287) ([#1165](https://github.com/quay/quay/issues/1165))
- [7162be37](https://github.com/quay/quay/commit/7162be3791db1ef122a579e5546857dbb55314f3): make batch_size configurable (PROJQUAY-3287) ([#1156](https://github.com/quay/quay/issues/1156))
- [369ee78a](https://github.com/quay/quay/commit/369ee78a2cec2024c0ee31f2b92190d3d69c9286): clairv2 - fix datatype bug (PROJQUAY-3279) ([#1138](https://github.com/quay/quay/issues/1138))
- [b32ca314](https://github.com/quay/quay/commit/b32ca3142a7255d91d70b267fcaee078ed54bc56): ClairV2 datatype compatibility (PROJQUAY-3279) ([#1133](https://github.com/quay/quay/issues/1133))
- [26eb7ff9](https://github.com/quay/quay/commit/26eb7ff9827fda97f775104a3b0d6a04c63ea860): Don't save secscan result if returned state is unknown (PROJQUAY-2939) ([#1047](https://github.com/quay/quay/issues/1047))
- [9f16b324](https://github.com/quay/quay/commit/9f16b3247e1fdd2a97f773657f722067388a8761): fix secscan api ApiRequestFailure test (PROJQUAY-2563) ([#896](https://github.com/quay/quay/issues/896))
- [694fa2ac](https://github.com/quay/quay/commit/694fa2acafbf50d09b1cccb54dcdd3c4aec3c113): continue iterating after failure (PROJQUAY-2563) ([#892](https://github.com/quay/quay/issues/892))
### Sescan
- [4db59990](https://github.com/quay/quay/commit/4db59990372e59c1de436d3fa7f3715e90887e0c): prioritize scanning new pushes (PROJQUAY-3287) ([#1147](https://github.com/quay/quay/issues/1147))
### Setup
- [fd190ad9](https://github.com/quay/quay/commit/fd190ad98468bbeb911bc2327faec14e84764265): Export Quay modules (PROJQUAY-3181) ([#1108](https://github.com/quay/quay/issues/1108))
### Static
- [a13baef9](https://github.com/quay/quay/commit/a13baef9cc15c68f41fd24e0f21a05979f5b4fbd): vendor webfonts dir ([#1016](https://github.com/quay/quay/issues/1016))
- [ab499e8f](https://github.com/quay/quay/commit/ab499e8f2cc72b90d07890bd8b1a5513594ef280): vendor external libraries ([#1014](https://github.com/quay/quay/issues/1014))
### Storage
- [c9c91339](https://github.com/quay/quay/commit/c9c9133914da3e931bab1e21255444a8fbf3e762): allow arbitrary endpoint url for azure storage ([#1071](https://github.com/quay/quay/issues/1071))
- [13a9f8f4](https://github.com/quay/quay/commit/13a9f8f44e59d512c4f01e5cc94a03bd8fca3d10): Add cn-northwest-1 to s3_region northwest (PROJQUAY-3082) ([#1137](https://github.com/quay/quay/issues/1137))
- [ca17eb43](https://github.com/quay/quay/commit/ca17eb43121e4d8ce85bc470e8f90c8feb2551e5): handle cn-north-1 region (PROJQUAY-3082) ([#1129](https://github.com/quay/quay/issues/1129))
- [f6f7b05a](https://github.com/quay/quay/commit/f6f7b05a060edd216354e632854c6ee0f545a768): allow configuration of storage region for cloud storage (PROJQUAY-3082) ([#1081](https://github.com/quay/quay/issues/1081))
### Superuser
- [dad7dfaf](https://github.com/quay/quay/commit/dad7dfaf44da08d4c39c99443c488f026bfa82f3): Fix display of build logs (PROJQUAY-3404) ([#1185](https://github.com/quay/quay/issues/1185))
### Teams
- [639833cc](https://github.com/quay/quay/commit/639833cc15304ec184f51843e18e2337dc29059f): admin team deletion (PROJQUAY-2080) ([#1077](https://github.com/quay/quay/issues/1077))
### Trigger_analyzer
- [861c247f](https://github.com/quay/quay/commit/861c247faf75e60a8ffde0ee58e0148abbb5efb2): fix confusing print (PROJQUAY-1995) ([#1073](https://github.com/quay/quay/issues/1073))
### UI
- [3d6545b9](https://github.com/quay/quay/commit/3d6545b9da1c32591ab0945b1d66282ce058a051): Quota UI enhancements (PROJQUAY-0000) ([#1242](https://github.com/quay/quay/issues/1242))
### Ui
- [e67ea047](https://github.com/quay/quay/commit/e67ea047c41e0feeb191d17a868f39df772da31a): Copy build logs error fix (PROJQUAY-3405) ([#1201](https://github.com/quay/quay/issues/1201))
- [815ef446](https://github.com/quay/quay/commit/815ef44651d0e4a4e6ad4e23f2e77fb58efbaf73): remove deprecated docker-image-id references from ui (PROJQUAY-3418) ([#1197](https://github.com/quay/quay/issues/1197))
- [033c1aaf](https://github.com/quay/quay/commit/033c1aafa1d1364a41a0861f16fa1769315672d6): display manifest list manifest sizes (PROJQUAY-3196) ([#1115](https://github.com/quay/quay/issues/1115))
- [e91ec644](https://github.com/quay/quay/commit/e91ec644fa9581f55a583c7d03a68a9f957c9f03): Depricate getImageCommand in security UI (PROJQUAY-3284) ([#1144](https://github.com/quay/quay/issues/1144))
- [374e957b](https://github.com/quay/quay/commit/374e957bd93d5b6bbb6ddd2080aaa4d67fcdfa74): fix csrf issue when login in with SSO on mobile (PROJQUAY-2340) ([#906](https://github.com/quay/quay/issues/906))
- [bf81bd9b](https://github.com/quay/quay/commit/bf81bd9bae44f6ff870d207026f44010e1b2d229): change angular routing order for repo paths (PROJQUAY-2325) ([#872](https://github.com/quay/quay/issues/872))
### Util
- [42d1cdb4](https://github.com/quay/quay/commit/42d1cdb4a16e961a23b4af9126c96798ecabb7fa): update aws-ip-ranges.json ([#1143](https://github.com/quay/quay/issues/1143))
### Util/Ipresolver
- [9ee1c580](https://github.com/quay/quay/commit/9ee1c580599eb74b83e16fc34f1fea369e2d0d66): manually add aws-ip-ranges.json ([#1065](https://github.com/quay/quay/issues/1065))
### V2auth
- [1f2b0b67](https://github.com/quay/quay/commit/1f2b0b6710ae1f57b6401d51fe4d3de0302c27a0): Check for user before creating org (PROJQUAY-3766) ([#1318](https://github.com/quay/quay/issues/1318))
### [Redhat-3.7] Quota Management
- [88d0549f](https://github.com/quay/quay/commit/88d0549ffe2da30d206e6f1c15d6efac63c523bf): Adding default quota check for image push (PROJQUAY-3789) ([#1319](https://github.com/quay/quay/issues/1319))

<a name="v3.6.2"></a>
## [v3.6.2] - 2021-12-02
### Api
- [6470248b](https://github.com/quay/quay/commit/6470248be1ca55ab3ea6f2a364bc02547976186d): /v1/user/initialize to create first user (PROJQUAY-1926) ([#771](https://github.com/quay/quay/issues/771))
### Backport
- [0520aa7c](https://github.com/quay/quay/commit/0520aa7c49032b37e99077932566aea0e3cc75ca): Quayio nvd data UI improvements  ([#957](https://github.com/quay/quay/issues/957))
### Build
- [1ae91bcc](https://github.com/quay/quay/commit/1ae91bcc8ba95ae38cadf401ce55044da9aaec36): Add required setup.cfg for downstream build (PROJQUAY-2713) ([#946](https://github.com/quay/quay/issues/946)) ([#994](https://github.com/quay/quay/issues/994))
- [4c09559c](https://github.com/quay/quay/commit/4c09559cee9b68493483c6c7b8486afde64c6702): add full python build dependencies (PROJQUAY-2216) ([#822](https://github.com/quay/quay/issues/822))
- [1d63cfa2](https://github.com/quay/quay/commit/1d63cfa255d32c9eece8041452f13d78daab6e1a): update package-lock.json (PROJQUAY-1749) ([#821](https://github.com/quay/quay/issues/821))
- [9c8e3f1f](https://github.com/quay/quay/commit/9c8e3f1f486840513a65197dccdb77585f42c815): remove unused node modules (PROJQUAY-1667) ([#805](https://github.com/quay/quay/issues/805))
- [62e3bd9c](https://github.com/quay/quay/commit/62e3bd9cc7ca743ac472e6ae7f8099ba28a91fd5): update python pillow version (PROJQUAY-1520) ([#809](https://github.com/quay/quay/issues/809))
- [653dc021](https://github.com/quay/quay/commit/653dc021fea6358f8a56c344ade4e775605df15d): update node url-parse to 1.4.3 (PROJQUAY-1749) ([#797](https://github.com/quay/quay/issues/797))
### Build(Deps)
- [98c008e6](https://github.com/quay/quay/commit/98c008e63fbb59f5c58da4f4c7bb96a74a4ff66e): bump pillow from 8.3.1 to 8.3.2 ([#882](https://github.com/quay/quay/issues/882)) ([#958](https://github.com/quay/quay/issues/958))
- [c5488aa3](https://github.com/quay/quay/commit/c5488aa3b52cab1c9e1391e50e0e9732f464d780): bump ssri from 6.0.1 to 6.0.2 ([#818](https://github.com/quay/quay/issues/818))
- [3c355223](https://github.com/quay/quay/commit/3c355223f17833dc5c0a8d95c1db6556b3ef9b44): bump flask-cors from 3.0.8 to 3.0.9 ([#783](https://github.com/quay/quay/issues/783))
### Buildman
- [f5b9492a](https://github.com/quay/quay/commit/f5b9492ac62df7a9b3ee741fc7ef8aba36028b72): Add proxy variables to builds if they exist (PROJQUAY-2120) ([#834](https://github.com/quay/quay/issues/834))
- [bfb8602d](https://github.com/quay/quay/commit/bfb8602d5ae1b3eb56fe57a381a6939fb60f98be): fix vm image name in startup script (PROJQUAY-2120) ([#811](https://github.com/quay/quay/issues/811))
### Cache
- [3dde3646](https://github.com/quay/quay/commit/3dde364615ae3f2b839fb38b7e791805e4243c3c): py2 compatibility, kwargs after named args (PROJQUAY-2101) ([#859](https://github.com/quay/quay/issues/859))
- [cd6871c1](https://github.com/quay/quay/commit/cd6871c14f5e017d70d99664ccde89ccac9e4366): add support for redis cluster mode (PROJQUAY-2101) ([#810](https://github.com/quay/quay/issues/810))
### Chore
- [35e8109c](https://github.com/quay/quay/commit/35e8109c332fed45ace09615c56e27629e415561): v3.6.1 changelog bump (PROJQUAY-2728) ([#955](https://github.com/quay/quay/issues/955))
- [b016844a](https://github.com/quay/quay/commit/b016844a0ff4b78bc03722b52fcd93efef57e7ce): build and publish workflow (PROJQUAY-2556)
- [47a1fdd3](https://github.com/quay/quay/commit/47a1fdd38ecbaffb460ebb4c6d43da4c14986221): remove ui elements for account recovery mode (PROJQUAY-970) ([#853](https://github.com/quay/quay/issues/853))
- [7d7eb755](https://github.com/quay/quay/commit/7d7eb75557fdc58a6c40536ccc807522659bd0d9): return zope.interface to requirements-osbs.txt (PROJQUAY-1535) ([#854](https://github.com/quay/quay/issues/854))
- [0999baa2](https://github.com/quay/quay/commit/0999baa29e76ee7c3118af75bb06b7bd681b66de): fix rediscluster cache config key name (PROJQUAY-2101) ([#849](https://github.com/quay/quay/issues/849))
- [a839a78e](https://github.com/quay/quay/commit/a839a78eb52e612a3f99c573ce1a552c5bb5e7a0): allows Quay to run for account recoveries (PROJQUAY-970) ([#793](https://github.com/quay/quay/issues/793))
- [4880c776](https://github.com/quay/quay/commit/4880c776e264e3fbf553418eff6656c68e5f60f2): remove node modules from final container (PROJQUAY-1822) ([#788](https://github.com/quay/quay/issues/788))
- [4ad5a458](https://github.com/quay/quay/commit/4ad5a458c2927be557f876a5e66928a02c67f87d): remove uploading filtering from imagestorage queries (PROJQUAY-1914) ([#764](https://github.com/quay/quay/issues/764))
### Config
- [c4ad61b5](https://github.com/quay/quay/commit/c4ad61b5831b40e95dab4aeda07f32e802b5cb2b): define default oci artifact types (PROJQUAY-2334) ([#877](https://github.com/quay/quay/issues/877)) ([#881](https://github.com/quay/quay/issues/881))
### Db
- [8591caf0](https://github.com/quay/quay/commit/8591caf0372dc0f68eb146a5e28a06eedd3fea87): remove transaction from empty layer upload (PROJQUAY-1946) ([#775](https://github.com/quay/quay/issues/775))
### Defaults
- [26a06763](https://github.com/quay/quay/commit/26a06763882e6a6df35dd36668df9dc5b95b6976): Update defaults in config and schema (PROJQUAY-2425) ([#923](https://github.com/quay/quay/issues/923)) ([#925](https://github.com/quay/quay/issues/925))
### Deploy
- [ce3cb357](https://github.com/quay/quay/commit/ce3cb357bd2abb7f1f7ddf6bc21f6b0294d9803e): update component label value for recovery (PROJQUAY-970) ([#832](https://github.com/quay/quay/issues/832))
- [d6616e9e](https://github.com/quay/quay/commit/d6616e9e1f4bcfc28ab80339448787cc19eca8d3): Add recovery endpoint deployment manifests (PROJQUAY-970) ([#831](https://github.com/quay/quay/issues/831))
### Deployment
- [242d4def](https://github.com/quay/quay/commit/242d4defc7d0a47f932f5338283f088c92cc8dc7): Change canary to blue deployment (PROJQUAY-1896) ([#781](https://github.com/quay/quay/issues/781))
### Doc
- [7a70a98b](https://github.com/quay/quay/commit/7a70a98b1ea616f79cdd3f691e4d2c55c4be6a7c): Fix broken links in the CHANGELOG (PROJQUAY-2298) ([#858](https://github.com/quay/quay/issues/858))
### Dockerfile
- [61d256fd](https://github.com/quay/quay/commit/61d256fdb25d11a83ad9ac4ec1a874ead1a7be4e): Update symlink in upstream dockerfile (PROJQUAY-2550) ([#889](https://github.com/quay/quay/issues/889)) ([#981](https://github.com/quay/quay/issues/981))
- [1f7d128c](https://github.com/quay/quay/commit/1f7d128c8d38db7de7b909a8229102ae982198b1): Fix downstream python site-packages location (PROJQUAY-2258) ([#842](https://github.com/quay/quay/issues/842))
- [6e809033](https://github.com/quay/quay/commit/6e809033736d5d0d5855457675b91eec794fcdaa): Fix QUAYCONF symlink and config-tool build in refactored Dockerfile (PROJQUAY-2254) ([#837](https://github.com/quay/quay/issues/837))
- [86d150a2](https://github.com/quay/quay/commit/86d150a2044a1eb24140b0940ba6f830b05c842b): refactor dockerfile (PROJQUAY-1997) ([#787](https://github.com/quay/quay/issues/787))
### Email
- [a2ba0a46](https://github.com/quay/quay/commit/a2ba0a4611fdae3fd7cefe368765b1204230df6d): fix org recovery link in email (PROJQUAY-2589) ([#904](https://github.com/quay/quay/issues/904))
### Fips
- [65363057](https://github.com/quay/quay/commit/653630579f63498670215779ab5cf80d61857253): enforce smtp tls (PROJQUAY-1804) ([#782](https://github.com/quay/quay/issues/782)) ([#782](https://github.com/quay/quay/issues/782))
### Local-Dev
- [eea5cfcb](https://github.com/quay/quay/commit/eea5cfcb2bc7099f40d5758e360d16f49492d841): Increase timeout for gunicorn tasks to come up (PROJQUAY-2114) ([#808](https://github.com/quay/quay/issues/808))
### Migration
- [94ed4716](https://github.com/quay/quay/commit/94ed47164bad3ec3b94fa17546bb6d605ec9f188): Add composite index in manifestblob (PROJQUAY-1922) ([#769](https://github.com/quay/quay/issues/769))
### Mirror
- [95ec9478](https://github.com/quay/quay/commit/95ec9478fc6b66f8b87ddcb699c6496f1661c15c): Do not store signatures on repo mirroring (PROJQUAY-2167) ([#816](https://github.com/quay/quay/issues/816))
### Modelcache
- [b33f125c](https://github.com/quay/quay/commit/b33f125c58cadfa0342ad1767517077b1c62a664): Add read and write endpoints to Redis (PROJQUAY-1939) ([#795](https://github.com/quay/quay/issues/795))
- [df4ad945](https://github.com/quay/quay/commit/df4ad9452757dd01fb651e2836abcb4620df9db7): Make ModelCache TTL configurable (PROJQUAY-1878) ([#765](https://github.com/quay/quay/issues/765))
### Notification
- [5996cbec](https://github.com/quay/quay/commit/5996cbecf16680262bbf70d7bd9e5c8d2a14f035): check certs exists for webhooks (PROJQUAY-2424) ([#886](https://github.com/quay/quay/issues/886)) ([#900](https://github.com/quay/quay/issues/900))
### Oauth
- [7f23e584](https://github.com/quay/quay/commit/7f23e584d12f095e4a67e4d7fcd4fbb36693d1cc): add timeout to OAuth token exchange (PROJQUAY-1335) ([#735](https://github.com/quay/quay/issues/735))
### Oci
- [3b13ccd4](https://github.com/quay/quay/commit/3b13ccd4f190f1fce40d27c15a4146f47dfcc4d1): Accept the stricter oci layer type used by default in Helm 3.7 (PROJQUAY-2653) ([#922](https://github.com/quay/quay/issues/922)) ([#949](https://github.com/quay/quay/issues/949))
- [1994f2d1](https://github.com/quay/quay/commit/1994f2d108a30b6d64a1f491f2f6342604758dc9): add support for zstd compression (PROJQUAY-1417) ([#801](https://github.com/quay/quay/issues/801))
- [64bc11fe](https://github.com/quay/quay/commit/64bc11fe46acdc20795f9a51ba2c8c6926579f77): allow oci artifact registration (PROJQUAY-1032) ([#803](https://github.com/quay/quay/issues/803))
### Organization
- [6ba0e881](https://github.com/quay/quay/commit/6ba0e88128b75bc79ca4763d931d2c2be472f8cb): config to allow organization creation on push (PROJQUAY-928) ([#799](https://github.com/quay/quay/issues/799))
### Python
- [2d0adf0c](https://github.com/quay/quay/commit/2d0adf0c189dc446c79ffcb2cdae493307f0d4b2): bump pillow to 8.3.1 (PROJQUAY-2250) ([#852](https://github.com/quay/quay/issues/852))
### Registry
- [b0adc966](https://github.com/quay/quay/commit/b0adc9667c906fcf8f7be7b9818768bf4f9311c7): add support for extended repository names (PROJQUAY-1535) ([#814](https://github.com/quay/quay/issues/814))
### Release
- [28b36abb](https://github.com/quay/quay/commit/28b36abb27954459f41e01cfe8ecda677aeb0ea3): update downstream Dockerfile (PROJQUAY-1861) ([#851](https://github.com/quay/quay/issues/851))
### Repository
- [a1b7e4b5](https://github.com/quay/quay/commit/a1b7e4b51974edfe86f66788621011eef2667e6a): config to allow public repo create (PROJQUAY-1929) ([#772](https://github.com/quay/quay/issues/772))
### Requirements
- [1f9a9aee](https://github.com/quay/quay/commit/1f9a9aeecd987539bc20017f762590ce20dc7bd5): bump cryptography package version ([#939](https://github.com/quay/quay/issues/939)) ([#940](https://github.com/quay/quay/issues/940))
### Secscan
- [1b061534](https://github.com/quay/quay/commit/1b0615341348aafc6ba2776ea90e84e4a6d175e4): continue iterating after failure (PROJQUAY-2563) ([#894](https://github.com/quay/quay/issues/894))
- [79e97785](https://github.com/quay/quay/commit/79e9778576e715da04a5eafc8dbde2e78955a095): handle proxy model fallback to noop v2 (PROJQUAY-2289) ([#847](https://github.com/quay/quay/issues/847))
- [65ec47ab](https://github.com/quay/quay/commit/65ec47ab4b67fcd84fb9a7aa0b4f9f31c5b4d902): handle remote layer url when sending request to Clair (PROJQUAY-2269) ([#841](https://github.com/quay/quay/issues/841))
### Secscan
- [fa0e8618](https://github.com/quay/quay/commit/fa0e8618494138dc78c8496c0d9d6d83b66335ca): clair v4 enrichment (PROJQUAY-2102) ([#840](https://github.com/quay/quay/issues/840))
### Static
- [3488e785](https://github.com/quay/quay/commit/3488e7855a391ec4b446982810c8eed9f28935c3): vendor webfonts dir ([#1017](https://github.com/quay/quay/issues/1017))
- [d93d85fa](https://github.com/quay/quay/commit/d93d85fa6647b7ed57c654e33c5c20bb48a11e39): vendor external libraries ([#1015](https://github.com/quay/quay/issues/1015))
### Templates
- [1c157e2a](https://github.com/quay/quay/commit/1c157e2a5b3ad4d091bc9480761b850d8856a15a): escape templated script value (PROJQUAY-970) ([#828](https://github.com/quay/quay/issues/828))
### Ui
- [a180c52a](https://github.com/quay/quay/commit/a180c52aaab7f7cd7ecc72c5a41b85c75970300e): force uses to sign-in page to fix SSO CSRF cookie issue (PROJQUAY-2340) ([#865](https://github.com/quay/quay/issues/865))
- [97fc1b5c](https://github.com/quay/quay/commit/97fc1b5cc774dbc6d085490548dc4695b440d55e): Require user to enter repository when deleting (PROJQUAY-763) ([#432](https://github.com/quay/quay/issues/432))
- [de12ed74](https://github.com/quay/quay/commit/de12ed7482859e3d6d4ce89d5ece2e701996d6ee): Add repo state column when mirroring enabled (PROJQUAY-591) ([#419](https://github.com/quay/quay/issues/419))
### Util
- [cfd4e8c4](https://github.com/quay/quay/commit/cfd4e8c46b7f174c3bc028a843293e58a5d37eab): fix matching multiples in jsontemplate.py (PROJQUAY-0000) ([#800](https://github.com/quay/quay/issues/800))
### Utility
- [69777301](https://github.com/quay/quay/commit/6977730185710cec71ef39edc55b5d774bc278b4): Fixes backfillreplication script to use manifest blobs (PROJQUAY-2218) ([#826](https://github.com/quay/quay/issues/826))

<a name="v3.6.0-alpha.9"></a>
## [v3.6.0-alpha.9] - 2021-04-21
### Cache
- [1180ea99](https://github.com/quay/quay/commit/1180ea99fae3787eccfa53801af6199d3af3bcac): remove GlobalLock from redis model cache (PROJQUAY-1902) ([#755](https://github.com/quay/quay/issues/755))
- [780685c4](https://github.com/quay/quay/commit/780685c490097ce7cf9515e0642505a45817df6a): add Redis model cache implementation (PROJQUAY-788) ([#444](https://github.com/quay/quay/issues/444))
### Chore
- [8921114d](https://github.com/quay/quay/commit/8921114d41faa184a787a93802394f5ab783d488): v3.6.0-alpha.9 changelog bump (PROJQUAY-1486) ([#763](https://github.com/quay/quay/issues/763))
- [0ffe9cee](https://github.com/quay/quay/commit/0ffe9ceecac456ab2b722459aa5aebe70c902fe9): correct chnglog params (PROJQUAY-1486) ([#762](https://github.com/quay/quay/issues/762))
- [addaeac0](https://github.com/quay/quay/commit/addaeac04aaab3d887258f53fdbb2fc85240bd62): fix release image tag to retain leading 'v' (PROJQUAY-1486) ([#739](https://github.com/quay/quay/issues/739))
- [ce7aa978](https://github.com/quay/quay/commit/ce7aa97802aac4118894cc5e97a81e431fe79f35): bump version to 3.6.0 (PROJQUAY-1861) ([#738](https://github.com/quay/quay/issues/738))
### Ci
- [e6011cff](https://github.com/quay/quay/commit/e6011cff5ba539a51a25ec2f0298068f63819c6e): include optional merge commit number in commit check job (PROJQUAY-1486) ([#742](https://github.com/quay/quay/issues/742))
### Deployment
- [080010e8](https://github.com/quay/quay/commit/080010e8cd7f2646c01fe29f17fae502c3114b31): Add image tag param to the deploy file (PROJQUAY-1896) ([#759](https://github.com/quay/quay/issues/759))
- [03c610d5](https://github.com/quay/quay/commit/03c610d51011061dd33499b5c38aacfcadf0f0c6): Add canary deployment to quay-app (PROJQUAY-1896) ([#754](https://github.com/quay/quay/issues/754))
### Gc
- [efa0692e](https://github.com/quay/quay/commit/efa0692e5ac3c47719dc8940d65feaa5f26a568b): increment quay_gc_repos_purged for NamespaceGCWorker (PROJQUAY-1802) ([#749](https://github.com/quay/quay/issues/749))
- [f774e4c6](https://github.com/quay/quay/commit/f774e4c6b6c674c822057a1d3dd49a3d5c36e6ca): add metrics for deleted resources ([#711](https://github.com/quay/quay/issues/711))
### Lock
- [c12654bf](https://github.com/quay/quay/commit/c12654bf46da701cd30dd9995091444bc046cf69): allows global lock to be used from main app (PROJQUAY-788) ([#745](https://github.com/quay/quay/issues/745))
- [778afaf3](https://github.com/quay/quay/commit/778afaf36be17d54958d5fa5bd8f365bea3ee965): reuse redis client when creating locks (PROJQUAY-1872) ([#741](https://github.com/quay/quay/issues/741))
### Queueworker
- [90f9ef95](https://github.com/quay/quay/commit/90f9ef95af98c7177566abf41213b22839e7206b): prevent stop event on WorkerSleepException (PROJQUAY-1857) ([#737](https://github.com/quay/quay/issues/737))

<a name="v3.6.0-alpha.8"></a>
## [v3.6.0-alpha.8] - 2021-04-09
### Chore
- [ecc125ff](https://github.com/quay/quay/commit/ecc125ff93c5a8328290195ab7dc2156a8ce32df): v3.6.0-alpha.8 changelog bump (PROJQUAY-1486) ([#732](https://github.com/quay/quay/issues/732))
- [166d17ab](https://github.com/quay/quay/commit/166d17ab4fb9ab65ffb0f59c35246e406ffbdf52): correct cut-release.yml (PROJQUAY-1486) ([#731](https://github.com/quay/quay/issues/731))

<a name="v3.6.0-alpha.7"></a>
## [v3.6.0-alpha.7] - 2021-04-09
### Chore
- [b54c8999](https://github.com/quay/quay/commit/b54c89997f64b66431accacc348e8fcefb02a42c): v3.6.0-alpha.7 changelog bump (PROJQUAY-1486) ([#730](https://github.com/quay/quay/issues/730))
- [bfc9d75c](https://github.com/quay/quay/commit/bfc9d75cab49df0bfd901a355a9bcb53bfeb5407): fix cut-release.yml (PROJQUAY-1468) ([#729](https://github.com/quay/quay/issues/729))

<a name="v3.6.0-alpha.6"></a>
## [v3.6.0-alpha.6] - 2021-04-09
### Chore
- [6c7dcb84](https://github.com/quay/quay/commit/6c7dcb8425debd7f9fcfed466a93ec40ad62fb1d): correct git-chglog config (PROJQUAY-1468) ([#728](https://github.com/quay/quay/issues/728))
- [43891120](https://github.com/quay/quay/commit/438911205aed1f543a97f0226319449eac3b927c): v3.6.0-alpha.6 changelog bump (PROJQUAY-1486) ([#727](https://github.com/quay/quay/issues/727))
- [043dbffc](https://github.com/quay/quay/commit/043dbffc59ce92fb125e678db579e7db45590efd): fix changelog template (PROJQUAY-1486) ([#726](https://github.com/quay/quay/issues/726))
- [03347285](https://github.com/quay/quay/commit/033472855fea2226925932486f4a98d8b960a7f7): parse new CHANGELOG.md format (PROJQUAY-1486) ([#725](https://github.com/quay/quay/issues/725))

<a name="v3.6.0-alpha.5"></a>
## [v3.6.0-alpha.5] - 2021-04-08
### Release
- [fba629b2](https://github.com/quay/quay/commit/fba629b2dbd2679071ecdfe13d6463a9b96a2fec): fixing Release action (PROJQUAY-1486) ([#723](https://github.com/quay/quay/issues/723))

<a name="v3.6.0-alpha.4"></a>
## [v3.6.0-alpha.4] - 2021-04-08
### Release
- [9dd55dee](https://github.com/quay/quay/commit/9dd55deed36c82b9499b3d230802e37e35b2cbc7): fixing Release action (PROJQUAY-1486)

[Unreleased]: https://github.com/quay/quay/compare/v3.8.11...HEAD
[v3.8.11]: https://github.com/quay/quay/compare/v3.8.10...v3.8.11
[v3.8.10]: https://github.com/quay/quay/compare/v3.8.9...v3.8.10
[v3.8.9]: https://github.com/quay/quay/compare/v3.8.8...v3.8.9
[v3.8.8]: https://github.com/quay/quay/compare/v3.8.7...v3.8.8
[v3.8.7]: https://github.com/quay/quay/compare/v3.8.6...v3.8.7
[v3.8.6]: https://github.com/quay/quay/compare/v3.8.5...v3.8.6
[v3.8.5]: https://github.com/quay/quay/compare/v3.8.4...v3.8.5
[v3.8.4]: https://github.com/quay/quay/compare/v3.8.3...v3.8.4
[v3.8.3]: https://github.com/quay/quay/compare/v3.8.2...v3.8.3
[v3.8.2]: https://github.com/quay/quay/compare/v3.8.1...v3.8.2
[v3.8.1]: https://github.com/quay/quay/compare/v3.8.0...v3.8.1
[v3.8.0]: https://github.com/quay/quay/compare/v3.7.13...v3.8.0
[v3.7.13]: https://github.com/quay/quay/compare/v3.7.12...v3.7.13
[v3.7.12]: https://github.com/quay/quay/compare/v3.7.11...v3.7.12
[v3.7.11]: https://github.com/quay/quay/compare/v3.7.10...v3.7.11
[v3.7.10]: https://github.com/quay/quay/compare/v3.7.9...v3.7.10
[v3.7.9]: https://github.com/quay/quay/compare/v3.7.8...v3.7.9
[v3.7.8]: https://github.com/quay/quay/compare/v3.7.7...v3.7.8
[v3.7.7]: https://github.com/quay/quay/compare/v3.7.6...v3.7.7
[v3.7.6]: https://github.com/quay/quay/compare/v3.7.5...v3.7.6
[v3.7.5]: https://github.com/quay/quay/compare/v3.7.4...v3.7.5
[v3.7.4]: https://github.com/quay/quay/compare/v3.7.3...v3.7.4
[v3.7.3]: https://github.com/quay/quay/compare/v3.7.2...v3.7.3
[v3.7.2]: https://github.com/quay/quay/compare/v3.7.1...v3.7.2
[v3.7.1]: https://github.com/quay/quay/compare/v3.7.0...v3.7.1
[v3.7.0]: https://github.com/quay/quay/compare/v3.6.2...v3.7.0
[v3.6.2]: https://github.com/quay/quay/compare/v3.6.0-alpha.9...v3.6.2
[v3.6.0-alpha.9]: https://github.com/quay/quay/compare/v3.6.0-alpha.8...v3.6.0-alpha.9
[v3.6.0-alpha.8]: https://github.com/quay/quay/compare/v3.6.0-alpha.7...v3.6.0-alpha.8
[v3.6.0-alpha.7]: https://github.com/quay/quay/compare/v3.6.0-alpha.6...v3.6.0-alpha.7
[v3.6.0-alpha.6]: https://github.com/quay/quay/compare/v3.6.0-alpha.5...v3.6.0-alpha.6
[v3.6.0-alpha.5]: https://github.com/quay/quay/compare/v3.6.0-alpha.4...v3.6.0-alpha.5
[v3.6.0-alpha.4]: https://github.com/quay/quay/compare/v3.6.0-alpha.3...v3.6.0-alpha.4
## Historical Changelog
[CHANGELOG.md](https://github.com/quay/quay/blob/96b17b8338fb10ca2ed12e9bc920dcbba148289c/CHANGELOG.md)
