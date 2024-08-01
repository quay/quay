## Red Hat Quay Release Notes

[Red Hat Customer Portal](https://access.redhat.com/documentation/en-us/red_hat_quay/3.7/html/red_hat_quay_release_notes/index)


<a name="v3.11.0"></a>
## [v3.11.0] - 2024-03-01
### Api
- [46d1322c](https://github.com/quay/quay/commit/46d1322ca7579f5080ed2af3b0b25a43ed123676): Return layer compressed size with manifest request (PROJQUAY-6616) ([#2627](https://github.com/quay/quay/issues/2627))
- [aaba7539](https://github.com/quay/quay/commit/aaba7539b9bd180d9c80e9d71c4d7e4b1780b8f7): adding nickname decorator to autoprune policy endpoints (PROJQUAY-6483) ([#2524](https://github.com/quay/quay/issues/2524))
- [9c89e843](https://github.com/quay/quay/commit/9c89e843f3b8801b7da1a6eb2d3523a7731a9eac): add caching for get_repository method (PROJQUAY-6472) ([#2515](https://github.com/quay/quay/issues/2515))
- [21e502f8](https://github.com/quay/quay/commit/21e502f86e55ee068d57e825679464790b077017): graceful error handling for robot acct already exists (PROJQUAY-6261) ([#2436](https://github.com/quay/quay/issues/2436))
### Autoprune
- [236e2fe4](https://github.com/quay/quay/commit/236e2fe4fd50ef9b3c71c7221b8cc236192d87cf): adding audit logs to namespace autoprune policy API (PROJQUAY-6229) ([#2431](https://github.com/quay/quay/issues/2431))
- [7e7dfc91](https://github.com/quay/quay/commit/7e7dfc919ea9817127b71583f4c36a3f4abeadfe): validating input to autoprune policy (PROJQUAY-6230) ([#2430](https://github.com/quay/quay/issues/2430))
### Backend
- [74fd23d7](https://github.com/quay/quay/commit/74fd23d7d30e3eb64eb752eac3d1581031433060): Syncing teams with OIDC group (PROJQUAY-6290) ([#2693](https://github.com/quay/quay/issues/2693))
### Billing
- [2a4ac093](https://github.com/quay/quay/commit/2a4ac0930608f6d64bbf55b595736da2518a4bea): marketplace UI (PROJQUAY-6551) ([#2595](https://github.com/quay/quay/issues/2595))
- [0b6b1598](https://github.com/quay/quay/commit/0b6b1598de5590ed6eb9c8e24a9aef3045e50a54): apply free trial to stripe checkout sessions (PROJQUAY-6405) ([#2491](https://github.com/quay/quay/issues/2491))
### Build(Deps)
- [e8256477](https://github.com/quay/quay/commit/e825647733fe8d9e47c78be554d2a5cdb3115673): bump github.com/aws/aws-sdk-go from 1.45.24 to 1.50.20 in /config-tool ([#2690](https://github.com/quay/quay/issues/2690))
- [116f19b1](https://github.com/quay/quay/commit/116f19b17726866f8bccfd60efdcb0c9bd510185): bump cryptography from 41.0.4 to 41.0.6 ([#2514](https://github.com/quay/quay/issues/2514))
- [0ea33dc3](https://github.com/quay/quay/commit/0ea33dc303162d3bd7ba145a752e343190615701): bump github.com/spf13/cobra from 1.7.0 to 1.8.0 in /config-tool ([#2455](https://github.com/quay/quay/issues/2455))
- [4a1e44f9](https://github.com/quay/quay/commit/4a1e44f95d5291b76b55c0552477948c654e570f): bump oslo-i18n from 3.25.1 to 6.2.0 ([#2501](https://github.com/quay/quay/issues/2501))
- [2f8efdaa](https://github.com/quay/quay/commit/2f8efdaa8ef428a716eec3a42c9f289129ec34d1): bump websocket-client from 0.57.0 to 1.7.0 ([#2525](https://github.com/quay/quay/issues/2525))
- [da2ffe76](https://github.com/quay/quay/commit/da2ffe762f82e81c35660f9873ccee4a753e7410): bump github.com/minio/minio-go/v7 from 7.0.63 to 7.0.66 in /config-tool ([#2563](https://github.com/quay/quay/issues/2563))
- [f5a5e4e4](https://github.com/quay/quay/commit/f5a5e4e41f15085cdd3addddea35cffd4f225f4e): bump axios from 1.4.0 to 1.6.5 in /web ([#2589](https://github.com/quay/quay/issues/2589))
- [f5c78c5a](https://github.com/quay/quay/commit/f5c78c5ab1f0f32fbbcf2010f356bd84fb62d443): bump jinja2 from 3.1.2 to 3.1.3 ([#2600](https://github.com/quay/quay/issues/2600))
### Build(Deps-Dev)
- [746e3727](https://github.com/quay/quay/commit/746e372741ce5b90f861a0eb9f07e5c391a3314a): bump dotenv-webpack from 7.1.0 to 8.0.1 in /web ([#2255](https://github.com/quay/quay/issues/2255))
- [5e1a54a5](https://github.com/quay/quay/commit/5e1a54a585b19d39248a04d5136eb46c796e9064): bump browserify-sign from 4.2.1 to 4.2.2 in /web ([#2439](https://github.com/quay/quay/issues/2439))
- [52275a3d](https://github.com/quay/quay/commit/52275a3d82f23cbde878b69e54af91a414ef4163): bump eslint from 8.49.0 to 8.56.0 in /web ([#2566](https://github.com/quay/quay/issues/2566))
### Cache
- [a7737722](https://github.com/quay/quay/commit/a7737722fcb335180ec01812d9b3fa472bda3deb): adding caching on look_up repository (PROJQUAY-6472) ([#2521](https://github.com/quay/quay/issues/2521))
### Cdn
- [93c816b2](https://github.com/quay/quay/commit/93c816b2b78881d3aa5ae797e6771d075a3bda30): add namespace and username to CDN redirect for usage calculation (PROJQUAY-5939) ([#2616](https://github.com/quay/quay/issues/2616))
### Chore
- [b23a2282](https://github.com/quay/quay/commit/b23a2282259317723fd85623871516604a5b5c3b): update local development clair to 4.7.2 ([#2692](https://github.com/quay/quay/issues/2692))
- [80c184f1](https://github.com/quay/quay/commit/80c184f168103046b8a2bfab1597ae53a1fbaa8f): extend market place subscription enddate (chore) ([#2663](https://github.com/quay/quay/issues/2663))
- [6d5e6293](https://github.com/quay/quay/commit/6d5e6293e32202967720078206da0a417419ad06): use oci_model directly without proxy object ([#2618](https://github.com/quay/quay/issues/2618))
- [88168d08](https://github.com/quay/quay/commit/88168d0878b98d9f1ac1b3896877435a2624b515): adding debug logging for repository_lookup cache key(PROJQUAY-6472) ([#2610](https://github.com/quay/quay/issues/2610))
### Chore: Amd64 Nightly
- [84ac7f20](https://github.com/quay/quay/commit/84ac7f208985a9bef2da1c9057cb6370bc512ca9): add libpq-dev to fix issue while installing psycopg2 ([#2642](https://github.com/quay/quay/issues/2642))
### Configtool
- [94735bcf](https://github.com/quay/quay/commit/94735bcfbd8ec9613eca0b0b643c44e35bf347cf): Adding validation for IBM Cloud Storage (PROJQUAY-6549) ([#2568](https://github.com/quay/quay/issues/2568))
### Database
- [9621d4ef](https://github.com/quay/quay/commit/9621d4efe356f1c7f9bc072c4d5df3d0af65027c): use psycopg2 instead of psycopg2-binary (PROJQUAY-6453) ([#2511](https://github.com/quay/quay/issues/2511))
### Deploy
- [bb0a6332](https://github.com/quay/quay/commit/bb0a63322fc9cba12ab9b9eccb5d883e30b7db60): update main deployment to add regitry worker count (PROJQUAY-6456) ([#2546](https://github.com/quay/quay/issues/2546))
- [aab56e43](https://github.com/quay/quay/commit/aab56e43977a3d45e314b7386e89e8261289c1b7): fix health check endpoint for quay deployment (PROJQUAY-6456) ([#2544](https://github.com/quay/quay/issues/2544))
- [248ea771](https://github.com/quay/quay/commit/248ea77190cbbf2e604a27b8f123fed2bdd5885d): update deploy template add proxy port (PROJQUAY-6456) ([#2539](https://github.com/quay/quay/issues/2539))
- [2410c7a9](https://github.com/quay/quay/commit/2410c7a99c9d9731df05c889406db80bbe144544): add web worker count to deployment (PROJQUAY-6453) ([#2520](https://github.com/quay/quay/issues/2520))
- [7284542f](https://github.com/quay/quay/commit/7284542f16eb3735bb2228fd7d0a7e15a3061f20): add DB pooling to py3 template (PROJQUAY-5550) ([#2474](https://github.com/quay/quay/issues/2474))
- [3f39a0fc](https://github.com/quay/quay/commit/3f39a0fc6fffd0d3e279a10f99d56f77eabb6d18): Add connection pooling env variable (PROJQUAY-5550) ([#2472](https://github.com/quay/quay/issues/2472))
### Feat
- [98811f53](https://github.com/quay/quay/commit/98811f539731b80c6d2de9a55011674d9225fd3e): Add auto-prune policy at repository level (PROJQUAY-6354) ([#2691](https://github.com/quay/quay/issues/2691))
### Federationuser(Ldap)
- [2c24975d](https://github.com/quay/quay/commit/2c24975dbb5ef7c2471863fb2d50918342ab9aa3): fixing keepalive settings for LDAP connections (PROJQUAY-5137) ([#2440](https://github.com/quay/quay/issues/2440))
### Fix
- [a8381d45](https://github.com/quay/quay/commit/a8381d45d3932451269061ff02b35f0748b0fe5d): pull-through should tolerate missing tag (PROJQUAY-4849) ([#2598](https://github.com/quay/quay/issues/2598))
### Logs
- [e8ff33e7](https://github.com/quay/quay/commit/e8ff33e728eef4f70ceb2834c3431dca0139b09c): add failure logging for login, push, pull and delete events (PROJQUAY-5411) ([#1903](https://github.com/quay/quay/issues/1903))
### Manifest
- [0b3d35b7](https://github.com/quay/quay/commit/0b3d35b71d5a28a5d6c6e0c5dc5c249007dcfd31): support empty config for artifacts (PROJQUAY-6658) ([#2647](https://github.com/quay/quay/issues/2647))
### Marketplace
- [2ab7dc29](https://github.com/quay/quay/commit/2ab7dc29f46c1b24deea5283a784e9ad9072b6fc): add support for quantity from subscriptions api (PROJQUAY-6551) ([#2633](https://github.com/quay/quay/issues/2633))
- [54bc56d5](https://github.com/quay/quay/commit/54bc56d5bee2837b000a2ac22dbdd3839eb7103f): return array of valid subscriptions when looking up subscription (PROJQUAY-6551) ([#2613](https://github.com/quay/quay/issues/2613))
- [26451766](https://github.com/quay/quay/commit/26451766ad5f49aa70d5900e6a42ab69e20921c4): make sure customer id from api is returned as an int (PROJQUAY-233) ([#2590](https://github.com/quay/quay/issues/2590))
- [1c893bab](https://github.com/quay/quay/commit/1c893baba533bb5853c220e0b9cf6ba56a9faa63): update reconciliationworker to use webCustomerId instead of ebsAccountNumber (PROJQUAY-233) ([#2582](https://github.com/quay/quay/issues/2582))
- [79723f1c](https://github.com/quay/quay/commit/79723f1ce3725625ddc8a54351b50e5239ef1e56): add exception handling for reconciler (PROJQUAY-233) ([#2560](https://github.com/quay/quay/issues/2560))
- [1bf3f448](https://github.com/quay/quay/commit/1bf3f44820da011a41cf53db16b9b67901588e02): update user ebs number lookup to find personal account numbers (PROJQUAY-233) ([#2545](https://github.com/quay/quay/issues/2545))
- [4c243341](https://github.com/quay/quay/commit/4c2433413c7a567bba5a23baae761652bc0d549a): add logging for user api (PROJQUAY-233) ([#2513](https://github.com/quay/quay/issues/2513))
- [3aa21213](https://github.com/quay/quay/commit/3aa2121326b07e10dc46a98e4f33a6529bf83713): return None if subscription api times out (PROJQUAY-5363) ([#2437](https://github.com/quay/quay/issues/2437))
### Oci
- [8895caf9](https://github.com/quay/quay/commit/8895caf97ba6e06c885b222010c7159594645ab3): remove platform requirement for image index (PROJQUAY-6658) ([#2657](https://github.com/quay/quay/issues/2657))
### Quayio
- [161a4717](https://github.com/quay/quay/commit/161a4717d28f3da547be2eb605f02823f8233d1b): Remove cpu limits (PROJQUAY-6440) ([#2503](https://github.com/quay/quay/issues/2503))
### Quota
- [29258ae0](https://github.com/quay/quay/commit/29258ae0c7b1ca0db9777042129ee5ac3e5532fb): removing repo size from quota verification (PROJQUAY-6637) ([#2704](https://github.com/quay/quay/issues/2704))
### Registry
- [e91b9e45](https://github.com/quay/quay/commit/e91b9e4543a7fc75abb3cf4bc17cf0a73ec748f0): allow pushing manifests with artifactType and subject fields (PROJQUAY-6673) ([#2659](https://github.com/quay/quay/issues/2659))
### Revert "Api
- [6fc77823](https://github.com/quay/quay/commit/6fc77823da976fc5a73771e81684dd73a3dd6002): add caching for get_repository method (PROJQUAY-6472)" ([#2517](https://github.com/quay/quay/issues/2517))
### Secscan
- [1fa6ed5d](https://github.com/quay/quay/commit/1fa6ed5dfd1ac194eb01015c3b5a1b923677c545): enable gc for manifests by default (PROJQUAY-4126) ([#2485](https://github.com/quay/quay/issues/2485))
### Sso
- [3e6384e6](https://github.com/quay/quay/commit/3e6384e6424cfa5b1873b84fc52793049ba64981): adding error log for export compliance (PROJQUAY-6486) ([#2540](https://github.com/quay/quay/issues/2540))
### Storage
- [e243d233](https://github.com/quay/quay/commit/e243d233f19c418e3d3d3804d05b787d79f68ba7): Fix big layer uploads for Ceph/RADOS driver (PROJQUAY-6586) ([#2601](https://github.com/quay/quay/issues/2601))
- [9f0e60e4](https://github.com/quay/quay/commit/9f0e60e46851311ae0c53e74c68ebe7cdbd04daf): adding IBM COS storage option (PROJQUAY-2679) ([#2470](https://github.com/quay/quay/issues/2470))
- [ad0d979c](https://github.com/quay/quay/commit/ad0d979c488372fec004f5531a83c48954a5d74a): pass S3 region to S3Storage init (PROJQUAY-6375) ([#2459](https://github.com/quay/quay/issues/2459))
### Sts
- [233c1288](https://github.com/quay/quay/commit/233c1288496d360c8f4416d36ecebd63ab0ef4ea): Add STS support for S3 (PROJQUAY-6362) ([#2632](https://github.com/quay/quay/issues/2632))
### Task
- [e6bf6392](https://github.com/quay/quay/commit/e6bf6392aab2c492f1e16fb55ad4e35b89108a89): Upgrade Quay nginx (PROJQUAY-6685) ([#2674](https://github.com/quay/quay/issues/2674))
### Ui
- [b6c6f00c](https://github.com/quay/quay/commit/b6c6f00c3b024547b15d72bac0aba6914ce7e4db): fix bug in usage logs description (PROJQUAY-6755) ([#2711](https://github.com/quay/quay/issues/2711))
- [5e3381a4](https://github.com/quay/quay/commit/5e3381a425e95ab44853164373a7a78b3fa61eb0): add usage log table (PROJQUAY-6702) ([#2695](https://github.com/quay/quay/issues/2695))
- [4cb0a574](https://github.com/quay/quay/commit/4cb0a57488f49f5eea01baa346c425963df4f22d): ui and initial scaffolding for OIDC auth (PROJQUAY-6298) ([#2646](https://github.com/quay/quay/issues/2646))
- [0c03e6af](https://github.com/quay/quay/commit/0c03e6af6b2ea34049ae1bd9d7cf9b32a9d5921d): add chart for usage logs (PROJQUAY-6701) ([#2681](https://github.com/quay/quay/issues/2681))
- [b641538b](https://github.com/quay/quay/commit/b641538badb60742dece91f52eca70519452fc76): removing repo settings and build UI feature flags (PROJQUAY-6617) ([#2680](https://github.com/quay/quay/issues/2680))
- [ca78dddf](https://github.com/quay/quay/commit/ca78dddfc6ab09a6dcbbc0a560801e6737898ac8): add width and height for logo (PROJQUAY-5460) ([#2683](https://github.com/quay/quay/issues/2683))
- [00d983bf](https://github.com/quay/quay/commit/00d983bf4bc09fb4d5522622e60f6d301ce002bc): view builds logs (PROJQUAY-6296) ([#2679](https://github.com/quay/quay/issues/2679))
- [426e1a94](https://github.com/quay/quay/commit/426e1a946d31cf7a35fb37c088c035fef3da2b4a): add overview to plugin (PROJQUAY-5460) ([#2682](https://github.com/quay/quay/issues/2682))
- [417e66ee](https://github.com/quay/quay/commit/417e66ee76d0837ed442e93850110b2c8b5a1289): run builds (PROJQUAY-6297) ([#2636](https://github.com/quay/quay/issues/2636))
- [f312efbc](https://github.com/quay/quay/commit/f312efbce20d94061eef88f4ddd87ca4c3e3671d): fixing build trigger test (PROJQUAY-6695) ([#2677](https://github.com/quay/quay/issues/2677))
- [19f2bb81](https://github.com/quay/quay/commit/19f2bb81d71698a729535496e2bb262c7554ad7d): add breadcrumbs for overview (PROJQUAY-5460) ([#2676](https://github.com/quay/quay/issues/2676))
- [696c35a8](https://github.com/quay/quay/commit/696c35a8ae7ad5b46f41eb5e0a26229f10660457): fix docker and podman login command for windows (PROJQUAY-6648) ([#2644](https://github.com/quay/quay/issues/2644))
- [5f4c15be](https://github.com/quay/quay/commit/5f4c15bebd2722e5ff4c76b78301bfa2f8184d3d): add export button for usage logs (PROJQUAY-6420) ([#2492](https://github.com/quay/quay/issues/2492))
- [5c44cc48](https://github.com/quay/quay/commit/5c44cc483f18a012c81197867c60b963b40c0c1e): add section for RH subscriptions under billing settings (PROJQUAY-5363) ([#2656](https://github.com/quay/quay/issues/2656))
- [df73b6e9](https://github.com/quay/quay/commit/df73b6e9e1ed8f6404b02d2254d81944d08ffc7d): updating references to status.redhat.com (PROJQUAY-6654) ([#2645](https://github.com/quay/quay/issues/2645))
- [0981ce15](https://github.com/quay/quay/commit/0981ce15a203b043ffac236d9adaf442bd81d496): fix scrollbars and various layout issues (PROJQUAY-6619) ([#2629](https://github.com/quay/quay/issues/2629))
- [7ba3a3d9](https://github.com/quay/quay/commit/7ba3a3d98887bb5034b033ccf1d23c6f731660c2): adjusting size of avatar (PROJQUAY-6676) ([#2660](https://github.com/quay/quay/issues/2660))
- [eec2c0fc](https://github.com/quay/quay/commit/eec2c0fc5e95ebfed3c9ce2a424db84d8c342aa0): fixing tag list reset when rendering manifest lists (PROJQUAY-5793) ([#2643](https://github.com/quay/quay/issues/2643))
- [03b7fec2](https://github.com/quay/quay/commit/03b7fec2116854f89272f3103b1699bb59577e17): implementing github and gitlab build triggers (PROJQUAY-6585) ([#2614](https://github.com/quay/quay/issues/2614))
- [40bcd1f1](https://github.com/quay/quay/commit/40bcd1f141dd4141a4ecbb3cb21282053a678203): allow for regular expressions to be used in search (PROJQUAY-6597) ([#2611](https://github.com/quay/quay/issues/2611))
- [7cec2f66](https://github.com/quay/quay/commit/7cec2f66975370d5869f15f7ec67cd433a2a9244): implementing creation of custom git trigger (PROJQUAY-6299) ([#2599](https://github.com/quay/quay/issues/2599))
- [27cceb1b](https://github.com/quay/quay/commit/27cceb1bb4b74a3f4e2a827fdfc347eebd5728ea): adding build trigger table (PROJQUAY-6295) ([#2570](https://github.com/quay/quay/issues/2570))
- [7357e317](https://github.com/quay/quay/commit/7357e317d6951c01d0ee6ff24c0c6c29e6501eb5): adding build avatar image size (PROJQUAY-6575) ([#2580](https://github.com/quay/quay/issues/2580))
- [2a22ed09](https://github.com/quay/quay/commit/2a22ed09c600b9d89d54ce7d6f535402414ac826): add dark mode to see Quay in a new light or lack thereof (PROJQUAY-6570) ([#2575](https://github.com/quay/quay/issues/2575))
- [77d6ad74](https://github.com/quay/quay/commit/77d6ad741b78d483c371ab1ec31b3a66b04f72b5): breadcrumbs fix when org and repo names are identical (PROJQUAY-6504) ([#2569](https://github.com/quay/quay/issues/2569))
- [6f365ed7](https://github.com/quay/quay/commit/6f365ed745b69030f159fe4c4c10ee8a4ff92aad): updating logo for quay.io (PROJQUAY-6531) ([#2559](https://github.com/quay/quay/issues/2559))
- [9b43b475](https://github.com/quay/quay/commit/9b43b4752f73e13fc960c8c8d83c2bf4832da5b7): Prevent switch to beta UI toggle from rendering if user is anonymous (PROJQUAY-6526) ([#2558](https://github.com/quay/quay/issues/2558))
- [4f0c8db1](https://github.com/quay/quay/commit/4f0c8db1055b66712270c0751f88ceaeecddcb2c): show UI toogle to all users in quay.io (PROJQUAY-6505) ([#2553](https://github.com/quay/quay/issues/2553))
- [ac221a60](https://github.com/quay/quay/commit/ac221a601d300561a010b718e9cf133f48dbda98): implementing build history page (PROJQUAY-6293) ([#2523](https://github.com/quay/quay/issues/2523))
- [e6d35781](https://github.com/quay/quay/commit/e6d35781063b5393bb13edf6ce9fe2aa56ff80f6): updates Quay.io documentation redirect link (PROJQUAY-6473) ([#2516](https://github.com/quay/quay/issues/2516))
- [03490a06](https://github.com/quay/quay/commit/03490a0614ca0948a421251a1735fa46075de776): fix broken update of repo description (PROJQUAY-6243) ([#2554](https://github.com/quay/quay/issues/2554))
- [a9eaa380](https://github.com/quay/quay/commit/a9eaa380f1797c7303c34c0d51675134d095eb8e): add breadcrumbs for teams page (PROJQUAY-6442) ([#2504](https://github.com/quay/quay/issues/2504))
- [a7b448c6](https://github.com/quay/quay/commit/a7b448c6300922ac43baca3f3f9ffe07dcf7c310): following capitalisation guidelines in the new ui   (PROJQUAY-6247) ([#2488](https://github.com/quay/quay/issues/2488))
- [29acc8da](https://github.com/quay/quay/commit/29acc8da5e0cba24e70d5c5594fd324e0e7952c9): Allow adding user from create team wizard (PROJQUAY-6336) ([#2468](https://github.com/quay/quay/issues/2468))
- [0c08bfff](https://github.com/quay/quay/commit/0c08bfffa242c56c44220e4ff8fd2b5f8f97b7c0): display manifest list size range (PROJQUAY-6393) ([#2469](https://github.com/quay/quay/issues/2469))
- [d860e40b](https://github.com/quay/quay/commit/d860e40b3d1fd841c768567db3bc4e52dcfb4a3b): breadcrumbs on new ui (PROJQUAY-5452) ([#1893](https://github.com/quay/quay/issues/1893))
- [94ca5b31](https://github.com/quay/quay/commit/94ca5b31c67a8512623792fdf14a05678f20b1d5): fix tab visibility for teams and membership (PROJQUAY-6333) ([#2451](https://github.com/quay/quay/issues/2451))
- [e2d25699](https://github.com/quay/quay/commit/e2d25699d87237361a1c990f112c3c5c3f2c781a): fix search for bulk delete default permission modal (PROJQUAY-6369) ([#2464](https://github.com/quay/quay/issues/2464))
- [ccb3658a](https://github.com/quay/quay/commit/ccb3658a90ac66a285f380e1ce738e97dd7bc3d3): allow current day to be selected for tag expiration (PROJQUAY-6262) ([#2448](https://github.com/quay/quay/issues/2448))
- [0b06da02](https://github.com/quay/quay/commit/0b06da023a3e16fcf1ba404a9eb4c970066c246a): Add form for repository state (PROJQUAY-5715) ([#2449](https://github.com/quay/quay/issues/2449))
- [7c0cc50a](https://github.com/quay/quay/commit/7c0cc50a59845700cd08407f79157984c60cc5a0): Add landing page for quay.io (PROJQUAY-5460) ([#2264](https://github.com/quay/quay/issues/2264))
### User(Robots)
- [0dfa72d0](https://github.com/quay/quay/commit/0dfa72d03607142ebf1e7acb398ac32c9019a717): disallow robot login and create 2nd (PROJQUAY-5968) ([#2483](https://github.com/quay/quay/issues/2483))

<a name="v3.10.4"></a>
## [v3.10.4] - 2024-02-07

<a name="v3.10.3"></a>
## [v3.10.3] - 2024-01-23
### [Redhat-3.10] Fix
- [4dd833ad](https://github.com/quay/quay/commit/4dd833adf16cc3bcd2530028bfb60c5a8d80ac20): pull-through should tolerate missing tag (PROJQUAY-4849) ([#2617](https://github.com/quay/quay/issues/2617))
### [Redhat-3.10] Ui
- [5a9cabd0](https://github.com/quay/quay/commit/5a9cabd00cbe921f02af766d69bff46a0ab04ff1): fix broken update of repo description (PROJQUAY-6243) ([#2612](https://github.com/quay/quay/issues/2612))

<a name="v3.10.2"></a>
## [v3.10.2] - 2024-01-08
### [Redhat-3.10] Configtool
- [a5ec0422](https://github.com/quay/quay/commit/a5ec0422eab667d07d5053bf4d44f78129d663e2): Adding validation for IBM Cloud Storage (PROJQUAY-6549) ([#2581](https://github.com/quay/quay/issues/2581))

<a name="v3.10.1"></a>
## [v3.10.1] - 2023-12-05
### [Redhat-3.10] Api
- [1499ae5c](https://github.com/quay/quay/commit/1499ae5cf2e0b6dc3adf35dd262d2f0d91258a9f): adding nickname decorator to autoprune policy endpoints (PROJQUAY-6483) ([#2535](https://github.com/quay/quay/issues/2535))
### [Redhat-3.10] Autoprune
- [73b36220](https://github.com/quay/quay/commit/73b36220b35e929fb7b57f893dbfccdfb4c45c9c): adding audit logs to namespace autoprune policy API (PROJQUAY-6229) ([#2538](https://github.com/quay/quay/issues/2538))
### [Redhat-3.10] Storage
- [9dde0359](https://github.com/quay/quay/commit/9dde03599862f6f4f3b3ef41ebb1db8234442edb): adding IBM COS storage option (PROJQUAY-2679) ([#2536](https://github.com/quay/quay/issues/2536))
### [Redhat-3.10] Ui
- [d4b18ad4](https://github.com/quay/quay/commit/d4b18ad4fa01eda0cd74d0b9ed3063e5686195c4): fix search for bulk delete default permission modal (PROJQUAY-6369) ([#2467](https://github.com/quay/quay/issues/2467))
- [bf6733ff](https://github.com/quay/quay/commit/bf6733ffa24a67dcb2b5dcddc8e38a883f234328): fix tab visibility for teams and membership (PROJQUAY-6333) ([#2482](https://github.com/quay/quay/issues/2482))
- [fea7c2cb](https://github.com/quay/quay/commit/fea7c2cb7c82b9b08651ba1b3e6212c6ab4d0cec): breadcrumbs on new ui (PROJQUAY-5452) ([#2490](https://github.com/quay/quay/issues/2490))
- [4d3aa4dd](https://github.com/quay/quay/commit/4d3aa4dd0a4c92801c0ea2048fa16e9fac307054): Allow adding user from create team wizard (PROJQUAY-6336) ([#2502](https://github.com/quay/quay/issues/2502))
### [Redhat-3.10] User(Robots)
- [2044413b](https://github.com/quay/quay/commit/2044413b83273bc49ac7d3bb929763722e5a2376): disallow robot login and create 2nd (PROJQUAY-5968) ([#2541](https://github.com/quay/quay/issues/2541))

<a name="v3.10.0"></a>
## [v3.10.0] - 2023-11-15
### Api
- [e5a5e178](https://github.com/quay/quay/commit/e5a5e17814670305463e1c230359963d4ccb01fe): accepting empty body for create robot endpoints (PROJQUAY-6224) ([#2420](https://github.com/quay/quay/issues/2420))
- [c93b6d08](https://github.com/quay/quay/commit/c93b6d080d0464a0ac40b71f0b76b906adebedfa): fix duplicate robot accounts (PROJQUAY-5931) ([#2192](https://github.com/quay/quay/issues/2192))
- [a095e1f9](https://github.com/quay/quay/commit/a095e1f938827b18fc987d3bfa7bf2e0f1207e91): Adding ignore timezone flag when parsing datetime (PROJQUAY-5360) ([#2027](https://github.com/quay/quay/issues/2027))
- [2371c4d6](https://github.com/quay/quay/commit/2371c4d605a3b2a6c8ac239e39a461cb621f7089): allow robot token creation with a pre-defined token (PROJQUAY-5414) ([#1972](https://github.com/quay/quay/issues/1972))
- [e38d70f0](https://github.com/quay/quay/commit/e38d70f0cb4136e2fd79e5dafaced6736110b699): add permanently delete tag usage log (PROJQUAY-5496) ([#1887](https://github.com/quay/quay/issues/1887))
### Audit
- [e1e8dc8e](https://github.com/quay/quay/commit/e1e8dc8efb12ee362123da67b0ba87de77fcf4bd): ignore errors due to read-only mode in audit logs (PROJQUAY-5598) ([#1928](https://github.com/quay/quay/issues/1928))
### Authentication(LDAP)
- [7ecf97b9](https://github.com/quay/quay/commit/7ecf97b9fc1aa43a7dec4cf498ca0e8e05344492): allow LDAP referrals to not be followed (PROJQUAY-5291)  ([#1905](https://github.com/quay/quay/issues/1905))
### Autoprune
- [30efa2af](https://github.com/quay/quay/commit/30efa2af7670c62f72ac62af4dde272270bb78eb): preventing prune of mirror or readonly repos (PROJQUAY-6235) ([#2425](https://github.com/quay/quay/issues/2425))
- [e8a6552c](https://github.com/quay/quay/commit/e8a6552cd0e8f8e8ebb48b26f2d4cdc0ff363eb6): updating task status to running (PROJQUAY-6213) ([#2413](https://github.com/quay/quay/issues/2413))
- [fa8aaa32](https://github.com/quay/quay/commit/fa8aaa328fa62ba7b969e1527c58b95691bef16b): background worker (PROJQUAY-6095) ([#2402](https://github.com/quay/quay/issues/2402))
- [1676cc04](https://github.com/quay/quay/commit/1676cc04e5538017175eb5a547d3c0dbd07dadc6): UI settings (PROJQUAY-6097) ([#2399](https://github.com/quay/quay/issues/2399))
- [22c4bbfe](https://github.com/quay/quay/commit/22c4bbfee5c3c05559993f3f7279ff26bcfc49e4): add auto-prune policy endpoints (PROJQUAY-6096) ([#2393](https://github.com/quay/quay/issues/2393))
- [0e496b46](https://github.com/quay/quay/commit/0e496b46a5d9b794c9c58318724e8bb84a7f9fcc): add initial setup for the autoprune feature (PROJQUAY-6094) ([#2277](https://github.com/quay/quay/issues/2277))
### Billing
- [e44783fe](https://github.com/quay/quay/commit/e44783fe19abb98e71358a58d5f769fa042f752e): Assign SKU to org (PROJQUAY-5363) ([#1989](https://github.com/quay/quay/issues/1989))
### Build(Deps)
- [74248c6e](https://github.com/quay/quay/commit/74248c6ef4039bb40c97e719ff6d884f7a60b773): bump urllib3 from 1.26.17 to 1.26.18 ([#2416](https://github.com/quay/quay/issues/2416))
- [5cadff86](https://github.com/quay/quay/commit/5cadff869d45b42cd5aea9d66072a83752dbe17b): bump golang.org/x/oauth2 from 0.12.0 to 0.13.0 in /config-tool ([#2390](https://github.com/quay/quay/issues/2390))
- [577d6824](https://github.com/quay/quay/commit/577d682485f78dbab0ebd8e7273d69746fcc26d4): bump golang.org/x/net from 0.15.0 to 0.17.0 in /config-tool ([#2403](https://github.com/quay/quay/issues/2403))
- [2b5325ed](https://github.com/quay/quay/commit/2b5325ed7d50e306ea5d54e565ad170277d44b84): bump [@patternfly](https://github.com/patternfly)/react-charts from 7.0.1 to 7.1.1 in /web ([#2387](https://github.com/quay/quay/issues/2387))
- [632a9a59](https://github.com/quay/quay/commit/632a9a59bbf6c2e805291cf513f335617cb170c4): bump github.com/aws/aws-sdk-go from 1.45.22 to 1.45.24 in /config-tool ([#2392](https://github.com/quay/quay/issues/2392))
- [30c628af](https://github.com/quay/quay/commit/30c628af02846ded621248cccff2ae1ba464f5eb): bump sqlalchemy from 1.4.31 to 1.4.49 ([#2377](https://github.com/quay/quay/issues/2377))
- [f672d67b](https://github.com/quay/quay/commit/f672d67bcf70d201d8b63d6704417f5301f8802f): bump deprecated from 1.2.7 to 1.2.14 ([#2374](https://github.com/quay/quay/issues/2374))
- [d35aace9](https://github.com/quay/quay/commit/d35aace93073eb42fb6f8dac00e05f6451b06cc7): bump flask-restful from 0.3.9 to 0.3.10 ([#2379](https://github.com/quay/quay/issues/2379))
- [a05017c3](https://github.com/quay/quay/commit/a05017c3e1df6cecd300143d109ddf9bf06e7460): bump zope-event from 4.5.0 to 5.0 ([#2378](https://github.com/quay/quay/issues/2378))
- [ba188717](https://github.com/quay/quay/commit/ba188717336cec1601873fa333ea9c76a60126d1): bump python-swiftclient from 3.8.1 to 4.4.0 ([#2372](https://github.com/quay/quay/issues/2372))
- [e7661f7e](https://github.com/quay/quay/commit/e7661f7e9b86511fcd157d6662ad41be431e3a78): bump react-scripts from 5.0.0 to 5.0.1 in /web ([#2297](https://github.com/quay/quay/issues/2297))
- [fbfd4d8d](https://github.com/quay/quay/commit/fbfd4d8d8bc76a6fa0273e348c6e86f9d7461cf0): bump splunk-sdk from 1.7.3 to 1.7.4 ([#2371](https://github.com/quay/quay/issues/2371))
- [57cb5210](https://github.com/quay/quay/commit/57cb5210d1deb4ea0e3259b2be328dd4942f243c): bump pymysql from 0.9.3 to 1.1.0 ([#2375](https://github.com/quay/quay/issues/2375))
- [004090cb](https://github.com/quay/quay/commit/004090cb5dd6a5ee0d29d2c98aa019bfec6efe52): bump github.com/Azure/azure-storage-blob-go from 0.11.0 to 0.15.0 in /config-tool ([#2322](https://github.com/quay/quay/issues/2322))
- [ed85c27d](https://github.com/quay/quay/commit/ed85c27d2a88830030d7ab10a22cc9cc9f24650a): bump decorator from 4.4.1 to 5.1.1 ([#2369](https://github.com/quay/quay/issues/2369))
- [b6088b47](https://github.com/quay/quay/commit/b6088b471b8622a721dad278d403f1760bcef92e): bump jsonpointer from 2.0 to 2.4 ([#2365](https://github.com/quay/quay/issues/2365))
- [365c3228](https://github.com/quay/quay/commit/365c3228c400f6867267ed51c171ad70bc831958): bump python-ldap from 3.4.0 to 3.4.3 ([#2362](https://github.com/quay/quay/issues/2362))
- [092f5a34](https://github.com/quay/quay/commit/092f5a343d27492169fb7613fb5dc18a4626d8a4): bump pygithub from 1.45 to 2.1.1 ([#2354](https://github.com/quay/quay/issues/2354))
- [e00b314a](https://github.com/quay/quay/commit/e00b314a742beeb10589309729dfe706af70fa32): bump psycopg2-binary from 2.9.3 to 2.9.9 ([#2356](https://github.com/quay/quay/issues/2356))
- [5ef0bc6c](https://github.com/quay/quay/commit/5ef0bc6c9035d56e0019821127340ed5948d66fc): bump zipp from 2.1.0 to 3.17.0 ([#2355](https://github.com/quay/quay/issues/2355))
- [0bf258f9](https://github.com/quay/quay/commit/0bf258f9715a954c3b79ce7d54284e2509ed8c9e): bump pip from 22.2.1 to 23.2.1 ([#2351](https://github.com/quay/quay/issues/2351))
- [6d580332](https://github.com/quay/quay/commit/6d580332aba856b0642b6bc7474ddc685371f6d9): bump setuptools-scm[toml] from 7.1.0 to 8.0.4 ([#2353](https://github.com/quay/quay/issues/2353))
- [bf914c54](https://github.com/quay/quay/commit/bf914c54d7cc4c3428423be89cb923184ead1787): bump protobuf from 3.18.3 to 3.20.3 ([#2348](https://github.com/quay/quay/issues/2348))
- [d7ea068e](https://github.com/quay/quay/commit/d7ea068e987187beee234ecf2aaee2490159f127): bump netifaces from 0.10.9 to 0.11.0 ([#2350](https://github.com/quay/quay/issues/2350))
- [1de5983c](https://github.com/quay/quay/commit/1de5983ca79121c35c311c2fd7caf48f687c4a99): bump boto3 from 1.21.42 to 1.28.61 ([#2347](https://github.com/quay/quay/issues/2347))
- [f5bd2f75](https://github.com/quay/quay/commit/f5bd2f75b181d8b1eabfd092b13a467ea3f99df2): bump toposort from 1.5 to 1.10 ([#2346](https://github.com/quay/quay/issues/2346))
- [8e2324a5](https://github.com/quay/quay/commit/8e2324a5cc0c335bd86b05113c3ef4d25ed5dabe): bump github.com/olekukonko/tablewriter from 0.0.5-0.20200416053754-163badb3bac6 to 0.0.5 in /config-tool ([#2327](https://github.com/quay/quay/issues/2327))
- [5057d524](https://github.com/quay/quay/commit/5057d5244aa944358707497bf5c387300d689a41): bump mako from 1.2.2 to 1.2.4 ([#2343](https://github.com/quay/quay/issues/2343))
- [c67f623e](https://github.com/quay/quay/commit/c67f623ec373307597552018f58bdb1f59ed3f15): bump babel from 2.9.1 to 2.13.0 ([#2340](https://github.com/quay/quay/issues/2340))
- [f6c5463a](https://github.com/quay/quay/commit/f6c5463a2cccbc77e0627cf8a2ba120e03d89e86): bump requests-aws4auth from 0.9 to 1.2.3 ([#2338](https://github.com/quay/quay/issues/2338))
- [c0a4ea9d](https://github.com/quay/quay/commit/c0a4ea9de311da09c4b82906c3e7ce156855ad0c): bump github.com/minio/minio-go/v7 from 7.0.40 to 7.0.63 in /config-tool ([#2326](https://github.com/quay/quay/issues/2326))
- [3cf8a3b8](https://github.com/quay/quay/commit/3cf8a3b88d5f5f2d450602b10fa442454a9facc4): bump github.com/swaggo/http-swagger from 1.3.3 to 1.3.4 in /config-tool ([#2320](https://github.com/quay/quay/issues/2320))
- [3937ae19](https://github.com/quay/quay/commit/3937ae19ab9fff5a067d0c933f54cb5b68c530b5): bump gunicorn from 20.1.0 to 21.2.0 ([#2335](https://github.com/quay/quay/issues/2335))
- [9598f0e2](https://github.com/quay/quay/commit/9598f0e2882e427fabb8dd90eacf757dab031746): bump click from 8.1.3 to 8.1.7 ([#2334](https://github.com/quay/quay/issues/2334))
- [450351a2](https://github.com/quay/quay/commit/450351a2bca4cfc3f2a16663c23ebde9194c4fa9): bump github.com/jackc/pgx/v4 from 4.11.0 to 4.18.1 in /config-tool ([#2317](https://github.com/quay/quay/issues/2317))
- [8513df69](https://github.com/quay/quay/commit/8513df69d87768489e52961648aefb705f72328a): bump hashids from 1.2.0 to 1.3.1 ([#2332](https://github.com/quay/quay/issues/2332))
- [27fceecb](https://github.com/quay/quay/commit/27fceecbdabb08410993ceec5324bcb22bf262a5): bump peewee from 3.13.1 to 3.16.3 ([#2323](https://github.com/quay/quay/issues/2323))
- [adbe34be](https://github.com/quay/quay/commit/adbe34be671fba7c67f692d7abb35d3aec04c1e1): bump tldextract from 2.2.2 to 3.6.0 ([#2310](https://github.com/quay/quay/issues/2310))
- [0604ee7d](https://github.com/quay/quay/commit/0604ee7d39a5fe036cb122b3bf18120d8d9699e4): bump python-magic from 0.4.15 to 0.4.27 ([#2324](https://github.com/quay/quay/issues/2324))
- [79f92d79](https://github.com/quay/quay/commit/79f92d794d4e778e733637086b78d0b0937a31c0): bump github.com/ncw/swift from 1.0.52 to 1.0.53 in /config-tool ([#2316](https://github.com/quay/quay/issues/2316))
- [598c4499](https://github.com/quay/quay/commit/598c4499f63e45b39b9117e2b10154c9decf6e93): bump github.com/sirupsen/logrus from 1.9.0 to 1.9.3 in /config-tool ([#2318](https://github.com/quay/quay/issues/2318))
- [26ec33cd](https://github.com/quay/quay/commit/26ec33cd3e02a0db08be36ffcf133305e0f65c6b): bump github.com/aws/aws-sdk-go from 1.44.282 to 1.45.22 in /config-tool ([#2319](https://github.com/quay/quay/issues/2319))
- [2f146e37](https://github.com/quay/quay/commit/2f146e375446a22bc4677164e90163aed973efd8): bump supervisor from 4.1.0 to 4.2.5 ([#2314](https://github.com/quay/quay/issues/2314))
- [bb0aadef](https://github.com/quay/quay/commit/bb0aadef25b76f1ae53d52ebed5a0194fe26e09c): bump lxml from 4.9.2 to 4.9.3 ([#2311](https://github.com/quay/quay/issues/2311))
- [f8442e27](https://github.com/quay/quay/commit/f8442e2764341f1109b88d6ad1e8ad20493ffb76): bump stevedore from 1.31.0 to 5.1.0 ([#2313](https://github.com/quay/quay/issues/2313))
- [aca6ff5c](https://github.com/quay/quay/commit/aca6ff5c2e49dcd2d5e8833659a8fd814628a45e): bump github.com/dave/jennifer from 1.4.0 to 1.7.0 in /config-tool ([#2306](https://github.com/quay/quay/issues/2306))
- [f6edd199](https://github.com/quay/quay/commit/f6edd1994eb2d3b4489e5c310e76a35c9bef3299): bump github.com/creasty/defaults from 1.4.0 to 1.7.0 in /config-tool ([#2295](https://github.com/quay/quay/issues/2295))
- [e64dc6e9](https://github.com/quay/quay/commit/e64dc6e9f2e1a0e2d4068de97e080148e988dd73): bump github.com/go-redis/redis/v8 from 8.0.0-beta.6 to 8.11.5 in /config-tool ([#2292](https://github.com/quay/quay/issues/2292))
- [4dca4fff](https://github.com/quay/quay/commit/4dca4fff34c1dea298191b65a190d58e8347f1d3): bump github.com/go-ldap/ldap/v3 from 3.2.4 to 3.4.6 in /config-tool ([#2305](https://github.com/quay/quay/issues/2305))
- [b5e3077a](https://github.com/quay/quay/commit/b5e3077a147519188185a9e83ff3173a235e4d4f): bump github.com/swaggo/swag from 1.8.1 to 1.16.2 in /config-tool ([#2304](https://github.com/quay/quay/issues/2304))
- [ef41e99f](https://github.com/quay/quay/commit/ef41e99f8c415d2977a57bd0017860fb62af979d): bump rehash from 1.0.0 to 1.0.1 ([#2289](https://github.com/quay/quay/issues/2289))
- [1821afaf](https://github.com/quay/quay/commit/1821afaf125deeeace6b84ef767c79569498a47e): bump bintrees from 2.1.0 to 2.2.0 ([#2287](https://github.com/quay/quay/issues/2287))
- [108ed710](https://github.com/quay/quay/commit/108ed710e218d744e0673c414ad06def492d41eb): bump github.com/lib/pq from 1.10.7 to 1.10.9 in /config-tool ([#2302](https://github.com/quay/quay/issues/2302))
- [f1cf5ea8](https://github.com/quay/quay/commit/f1cf5ea8d4c4771bceecc7a8bfe0401791e78021): bump golang.org/x/oauth2 from 0.0.0-20190226205417-e64efc72b421 to 0.12.0 in /config-tool ([#2301](https://github.com/quay/quay/issues/2301))
- [9071a0dd](https://github.com/quay/quay/commit/9071a0dd7cbfbd7b592f8088c34e16e63e801f26): bump github.com/go-sql-driver/mysql from 1.5.0 to 1.7.1 in /config-tool ([#2293](https://github.com/quay/quay/issues/2293))
- [6c8078f1](https://github.com/quay/quay/commit/6c8078f1b203d717e9151d4c1cdcec7ea597c421): bump cuelang.org/go from 0.2.1 to 0.6.0 in /config-tool ([#2294](https://github.com/quay/quay/issues/2294))
- [665364e0](https://github.com/quay/quay/commit/665364e0b991b87a3c72ef42c4792e11e06b7203): bump dumb-init from 1.2.2 to 1.2.5.post1 ([#2286](https://github.com/quay/quay/issues/2286))
- [834f2b9a](https://github.com/quay/quay/commit/834f2b9a3a22bfb994ddaedbe06afee44e2f0a6e): bump github.com/iancoleman/strcase from 0.0.0-20191112232945-16388991a334 to 0.3.0 in /config-tool ([#2290](https://github.com/quay/quay/issues/2290))
- [ef9faee7](https://github.com/quay/quay/commit/ef9faee763751e6c759f6084ba9aa00e1de22939): bump pillow from 9.3.0 to 10.0.1 ([#2283](https://github.com/quay/quay/issues/2283))
- [d2e5a69b](https://github.com/quay/quay/commit/d2e5a69b26338cf4282d8b673b4a1a3e4b52092e): bump pyjwt from 2.4.0 to 2.8.0 ([#2166](https://github.com/quay/quay/issues/2166))
- [b4e1640f](https://github.com/quay/quay/commit/b4e1640fb954b74ac12cd076a2db5e85c93735a7): bump tzlocal from 2.0.0 to 5.0.1 ([#2139](https://github.com/quay/quay/issues/2139))
- [6ea6609f](https://github.com/quay/quay/commit/6ea6609f71f75a73a65301200c8e05cd55484f87): bump urllib3 from 1.26.9 to 1.26.17 ([#2278](https://github.com/quay/quay/issues/2278))
- [da9d29fb](https://github.com/quay/quay/commit/da9d29fb290cb4ef30c40ffe45a2df14197ed28e): bump oslo-utils from 4.12.2 to 6.2.1 ([#2224](https://github.com/quay/quay/issues/2224))
- [e9395138](https://github.com/quay/quay/commit/e93951389552db4f51fbd5442f19c5a3e67d1b75): bump gevent from 21.8.0 to 23.9.1 ([#2260](https://github.com/quay/quay/issues/2260))
- [6afb41d5](https://github.com/quay/quay/commit/6afb41d5f4dbd4392aa48d7c0b8a68520430c014): bump [@cypress](https://github.com/cypress)/request and cypress in /config-tool/pkg/lib/editor ([#2259](https://github.com/quay/quay/issues/2259))
- [07fab33f](https://github.com/quay/quay/commit/07fab33f2eae8b18e0561220546a70cf87226f43): bump cryptography from 41.0.3 to 41.0.4 ([#2248](https://github.com/quay/quay/issues/2248))
- [8c80c804](https://github.com/quay/quay/commit/8c80c80492b22b78139acb4ea9388c20a21c941c): bump [@patternfly](https://github.com/patternfly)/react-charts from 6.94.19 to 7.0.1 in /web ([#2254](https://github.com/quay/quay/issues/2254))
- [de234ad8](https://github.com/quay/quay/commit/de234ad8a707d8de2ddb269606cfadae45385b6a): bump [@types](https://github.com/types)/node from 16.18.46 to 20.6.5 in /web ([#2251](https://github.com/quay/quay/issues/2251))
- [e3d9b3ef](https://github.com/quay/quay/commit/e3d9b3ef942a554418007bb84157f7792192755b): bump highlight.js from 9.18.3 to 11.8.0 in /config-tool/pkg/lib/editor ([#2226](https://github.com/quay/quay/issues/2226))
- [eff731e0](https://github.com/quay/quay/commit/eff731e0a82507b22bf65cc333f66238693b4e95): bump [@redhat](https://github.com/redhat)-cloud-services/frontend-components-config-utilities from 1.5.31 to 3.0.4 in /web ([#2241](https://github.com/quay/quay/issues/2241))
- [2736b96d](https://github.com/quay/quay/commit/2736b96de0b0b4b3bedc90157cda91a87a4cfe1f): bump grpcio from 1.53.0 to 1.58.0 ([#2238](https://github.com/quay/quay/issues/2238))
- [98836c4b](https://github.com/quay/quay/commit/98836c4b2fcd569ae82db965bdbfd9898accac2d): bump requests-oauthlib from 1.3.0 to 1.3.1 ([#2223](https://github.com/quay/quay/issues/2223))
- [de6582e7](https://github.com/quay/quay/commit/de6582e7be1acd01b6ebb30db03f5c894986788a): bump web-vitals from 2.1.4 to 3.4.0 in /web ([#2219](https://github.com/quay/quay/issues/2219))
- [d894940f](https://github.com/quay/quay/commit/d894940f2e43b077db86af9922988d6840da602c): bump loader-utils, css-loader, karma-webpack, ngtemplate-loader and style-loader in /config-tool/pkg/lib/editor ([#2184](https://github.com/quay/quay/issues/2184))
- [8c96c1eb](https://github.com/quay/quay/commit/8c96c1ebdda99e0a6292642b6fa6803aad2da7d4): bump isodate from 0.6.0 to 0.6.1 ([#2199](https://github.com/quay/quay/issues/2199))
- [8cd72db0](https://github.com/quay/quay/commit/8cd72db07cb372be3e468170f91a9d8edd75d4f0): bump setuptools from 65.5.1 to 68.1.2 ([#2179](https://github.com/quay/quay/issues/2179))
- [4f1dc068](https://github.com/quay/quay/commit/4f1dc0689bdf2e9ada7ee4b123fcd2b9e7827070): bump cypress from 10.10.0 to 12.17.4 in /web ([#2171](https://github.com/quay/quay/issues/2171))
- [63d33c3a](https://github.com/quay/quay/commit/63d33c3a5c1779fb9035c804719ddc120d6df3f9): bump idna from 2.8 to 3.4 ([#2178](https://github.com/quay/quay/issues/2178))
- [085e488c](https://github.com/quay/quay/commit/085e488c01a8997c6b1918a3a9f6415a1c9d5d68): bump pycparser from 2.20 to 2.21 ([#2169](https://github.com/quay/quay/issues/2169))
- [f6d9d00e](https://github.com/quay/quay/commit/f6d9d00e35cd7f225adb155ca935be6d3bcb9b13): bump react-router-dom from 6.3.0 to 6.15.0 in /web ([#2174](https://github.com/quay/quay/issues/2174))
- [1cfee1c7](https://github.com/quay/quay/commit/1cfee1c778fbd8ae641a7e4e885be09f7a8f3ab1): bump pyasn1-modules from 0.2.8 to 0.3.0 ([#2168](https://github.com/quay/quay/issues/2168))
- [a531a79f](https://github.com/quay/quay/commit/a531a79fbc1979ed9679afd804e5aaa41b482f72): bump urijs from 1.19.2 to 1.19.11 in /config-tool/pkg/lib/editor ([#2164](https://github.com/quay/quay/issues/2164))
- [0046cb51](https://github.com/quay/quay/commit/0046cb518c25c621841b015f243ebc7c38d98b89): bump moment-timezone from 0.4.1 to 0.5.35 in /config-tool/pkg/lib/editor ([#2158](https://github.com/quay/quay/issues/2158))
- [1e18a546](https://github.com/quay/quay/commit/1e18a5466be500b628a1f5e3139afe193df776f0): bump ejs and webpack-bundle-analyzer in /config-tool/pkg/lib/editor ([#2163](https://github.com/quay/quay/issues/2163))
- [5a0d4001](https://github.com/quay/quay/commit/5a0d400192c4dee9c20c7f8938cd64d415305960): bump jsrsasign from 10.1.13 to 10.5.25 in /config-tool/pkg/lib/editor ([#2161](https://github.com/quay/quay/issues/2161))
- [da0e6efd](https://github.com/quay/quay/commit/da0e6efdd4bd2eb230a608d12b0fdcb0a9721c40): bump moment from 2.27.0 to 2.29.4 in /config-tool/pkg/lib/editor ([#2160](https://github.com/quay/quay/issues/2160))
- [9fbd49b3](https://github.com/quay/quay/commit/9fbd49b37b09e1c323b738f29eab1d4939af2579): bump jszip from 3.5.0 to 3.8.0 in /config-tool/pkg/lib/editor ([#2073](https://github.com/quay/quay/issues/2073))
- [743fa178](https://github.com/quay/quay/commit/743fa178a1c5e9203590dcc4beed71467cbacd91): bump jquery from 1.12.4 to 3.5.0 in /config-tool/pkg/lib/editor ([#2075](https://github.com/quay/quay/issues/2075))
- [c31f8eea](https://github.com/quay/quay/commit/c31f8eeab71e8254428dd522c5518a51204c888e): bump tqdm from 4.65.0 to 4.66.1 ([#2142](https://github.com/quay/quay/issues/2142))
- [48da4ccd](https://github.com/quay/quay/commit/48da4ccdb249a6d2ace0e5c58952da8820d37b3a): bump [@types](https://github.com/types)/jest from 27.4.1 to 29.5.3 in /web ([#2144](https://github.com/quay/quay/issues/2144))
- [f25d99ac](https://github.com/quay/quay/commit/f25d99acb860b7f051a6684b06d11ff63991aa00): bump [@testing](https://github.com/testing)-library/user-event in /web ([#2147](https://github.com/quay/quay/issues/2147))
- [65b8037b](https://github.com/quay/quay/commit/65b8037bd9285946ba94c821614d8760ad85e880): bump packaging from 21.3 to 23.1 ([#2141](https://github.com/quay/quay/issues/2141))
- [cffbedbf](https://github.com/quay/quay/commit/cffbedbf544246c325ed7285f251d59efe00e88e): bump authlib from 1.2.0 to 1.2.1 ([#2143](https://github.com/quay/quay/issues/2143))
- [1548b618](https://github.com/quay/quay/commit/1548b6186cc15f7221b09aa796f35cfd6f4b7f07): bump msrest from 0.6.21 to 0.7.1 ([#2125](https://github.com/quay/quay/issues/2125))
- [d2b8cdd4](https://github.com/quay/quay/commit/d2b8cdd40d1f5773618ee8139487a92cb4663ade): bump stripe from 5.2.0 to 5.5.0 ([#2127](https://github.com/quay/quay/issues/2127))
- [60083341](https://github.com/quay/quay/commit/60083341e0637e545198464a860f69f95c5e9962): bump setuptools-scm[toml] from 4.1.2 to 7.1.0 ([#2124](https://github.com/quay/quay/issues/2124))
- [b31c95d3](https://github.com/quay/quay/commit/b31c95d399a4c5e7ccdbb30dd01be5ea1879a327): bump [@patternfly](https://github.com/patternfly)/react-icons from 4.93.6 to 4.93.7 in /web ([#2122](https://github.com/quay/quay/issues/2122))
- [1668d714](https://github.com/quay/quay/commit/1668d714f0493eee16b71438a89d86c0358e1952): bump requests-file from 1.4.3 to 1.5.1 ([#2126](https://github.com/quay/quay/issues/2126))
- [13e14e7d](https://github.com/quay/quay/commit/13e14e7d5e03544df7a77b2c63860d157058fd2c): bump typing-extensions from 4.0.1 to 4.7.1 ([#2123](https://github.com/quay/quay/issues/2123))
- [5c497a6a](https://github.com/quay/quay/commit/5c497a6affb1ec5767416c8ed13efbf1d97517a0): bump cryptography from 3.3.2 to 41.0.3 ([#2090](https://github.com/quay/quay/issues/2090))
- [14712ac7](https://github.com/quay/quay/commit/14712ac7bc197242017cd42c1ea861cd6e9c8691): bump mini-css-extract-plugin from 2.6.1 to 2.7.6 in /web ([#2101](https://github.com/quay/quay/issues/2101))
- [8d4ed561](https://github.com/quay/quay/commit/8d4ed561fa17374fbdd03e9ab0916c45d6024ca0): bump ts-jest from 26.5.6 to 29.1.1 in /web ([#2103](https://github.com/quay/quay/issues/2103))
- [356dea09](https://github.com/quay/quay/commit/356dea09f137ee50698c6ced30a0786bfacef68a): bump semantic-version from 2.8.4 to 2.10.0 ([#2099](https://github.com/quay/quay/issues/2099))
- [0da495f5](https://github.com/quay/quay/commit/0da495f5ff7ef696aae0dddd28531373822045e9): bump cryptography and pyOpenSSL (PROJQUAY-5120) ([#2086](https://github.com/quay/quay/issues/2086))
- [9c4f0be8](https://github.com/quay/quay/commit/9c4f0be885819394572e5edcd03754ba2802c42c): bump golang.org/x/net (PROJQUAY-5339) ([#2091](https://github.com/quay/quay/issues/2091))
- [b9262fd9](https://github.com/quay/quay/commit/b9262fd9c54b93a332f6ae7d3d68a2e1823e701f): bump pbr from 5.10.0 to 5.11.1 ([#2050](https://github.com/quay/quay/issues/2050))
- [8d9a5bc7](https://github.com/quay/quay/commit/8d9a5bc752a2e8ce128c9c9a876604a805f7aed7): bump axios from 0.27.2 to 1.4.0 in /web ([#2047](https://github.com/quay/quay/issues/2047))
- [a175f9dc](https://github.com/quay/quay/commit/a175f9dc900a643e57cbece68f190982ddf0d01d): bump recoil from 0.7.2 to 0.7.7 in /web ([#2045](https://github.com/quay/quay/issues/2045))
- [6c1f4972](https://github.com/quay/quay/commit/6c1f49729d1190dcac27c22957d9e0e9780d7f99): bump certifi from 2022.12.7 to 2023.7.22 ([#2061](https://github.com/quay/quay/issues/2061))
- [82f1a217](https://github.com/quay/quay/commit/82f1a2173d95d66194ce1c03f1246d8fd964571b): bump config-tool to v0.1.21 ([#2051](https://github.com/quay/quay/issues/2051))
- [81a236de](https://github.com/quay/quay/commit/81a236de5f38d1e5e5035ec95618b194087d4275): bump minimatch, recursive-readdir and serve in /web ([#1686](https://github.com/quay/quay/issues/1686))
- [9ddc60ed](https://github.com/quay/quay/commit/9ddc60edf81dfe2ed6b4fb3cf472d1692a7360e3): bump config-tool to v0.1.20 ([#2039](https://github.com/quay/quay/issues/2039))
- [31bc720a](https://github.com/quay/quay/commit/31bc720a6a77eb4a6bf40bcce646f04e889a091c): bump [@patternfly](https://github.com/patternfly)/react-charts in /web ([#2034](https://github.com/quay/quay/issues/2034))
- [700adb74](https://github.com/quay/quay/commit/700adb74ce2982b7908a2c9c682d285a9b9e0717): bump reportlab from 3.5.55 to 3.6.13 (PROJQUAY-5691) ([#2000](https://github.com/quay/quay/issues/2000))
- [a1b416d0](https://github.com/quay/quay/commit/a1b416d06e216e560f5d2adf065128b43f80c56f): bump word-wrap from 1.2.3 to 1.2.4 in /web ([#2018](https://github.com/quay/quay/issues/2018))
- [b77f5fef](https://github.com/quay/quay/commit/b77f5fefb92c999008cba6a3d48111d3ba0db00a): bump semver from 5.7.1 to 5.7.2 in /web ([#2012](https://github.com/quay/quay/issues/2012))
- [b1d36d34](https://github.com/quay/quay/commit/b1d36d34f94a2655baca9cbf6ca00890961ddacb): bump grpcio from 1.46.3 to 1.53.0 ([#2003](https://github.com/quay/quay/issues/2003))
- [c0fcf246](https://github.com/quay/quay/commit/c0fcf2469e7e58cc09048d6771e8d8e35e42dd7d): bump config-tool to v0.1.19 ([#2001](https://github.com/quay/quay/issues/2001))
- [9db821c8](https://github.com/quay/quay/commit/9db821c898af3d180253083863e8bd2b409279dd): bump pypdf2 from 1.27.6 to 1.27.9 ([#1998](https://github.com/quay/quay/issues/1998))
- [cb7b3791](https://github.com/quay/quay/commit/cb7b37912e5c5ee1ca5a49da1e1f9de466a5c3b4): bump requests from 2.27.1 to 2.31.0 ([#1899](https://github.com/quay/quay/issues/1899))
### Build(Deps-Dev)
- [4ebed1f5](https://github.com/quay/quay/commit/4ebed1f5e1acca0fb57147a04453c3c684e7d4cd): bump webpack-merge from 5.9.0 to 5.10.0 in /web ([#2410](https://github.com/quay/quay/issues/2410))
- [0e51b040](https://github.com/quay/quay/commit/0e51b040d427668d27536616222d12f24e7b3507): bump ts-loader from 9.4.4 to 9.5.0 in /web ([#2388](https://github.com/quay/quay/issues/2388))
- [f74d0481](https://github.com/quay/quay/commit/f74d04812456027fc4751fc55e2c7218ef9747d3): bump types-docutils from 0.17.1 to 0.20.0.3 ([#2376](https://github.com/quay/quay/issues/2376))
- [eaee1d6a](https://github.com/quay/quay/commit/eaee1d6a7b7a104bff8cf69151b427e779fc9a6d): bump tsconfig-paths-webpack-plugin from 3.5.2 to 4.1.0 in /web ([#2298](https://github.com/quay/quay/issues/2298))
- [3dbf7ce0](https://github.com/quay/quay/commit/3dbf7ce031004729645d168181245236d7f3ec16): bump types-tzlocal from 3.0.0 to 5.1.0.0 ([#2370](https://github.com/quay/quay/issues/2370))
- [a8883507](https://github.com/quay/quay/commit/a888350739ff7cd6626a612f1d0691e337bb4599): bump types-html5lib from 1.1.11.14 to 1.1.11.15 ([#2366](https://github.com/quay/quay/issues/2366))
- [02b270d3](https://github.com/quay/quay/commit/02b270d3094a998abe49e876658522f5ba80e41b): bump types-python-dateutil from 2.8.2 to 2.8.19.14 ([#2368](https://github.com/quay/quay/issues/2368))
- [26ab1166](https://github.com/quay/quay/commit/26ab11669c0d067b6e7a2c69a85b5246d37ea900): bump types-boto from 2.49.2 to 2.49.18.9 ([#2361](https://github.com/quay/quay/issues/2361))
- [3b48cf37](https://github.com/quay/quay/commit/3b48cf372e3a43cf55d67b0baddb2de347de7cc4): bump types-setuptools from 57.4.2 to 68.2.0.0 ([#2363](https://github.com/quay/quay/issues/2363))
- [90d36a04](https://github.com/quay/quay/commit/90d36a04184d698986d7cf675e6317824c409975): bump types-freezegun from 1.1.2 to 1.1.10 ([#2359](https://github.com/quay/quay/issues/2359))
- [1b016de4](https://github.com/quay/quay/commit/1b016de4f311abe897994ce3022fcfded04e8e37): bump types-stripe from 3.5.2.10 to 3.5.2.14 ([#2352](https://github.com/quay/quay/issues/2352))
- [31400f49](https://github.com/quay/quay/commit/31400f4983c06bb9326166cd5490d998ac4ba3aa): bump termcolor from 1.1.0 to 2.3.0 ([#2344](https://github.com/quay/quay/issues/2344))
- [37078841](https://github.com/quay/quay/commit/37078841aa9cd8831ca36cf61d6201a37879f678): bump types-pytz from 2021.3.0 to 2023.3.1.1 ([#2342](https://github.com/quay/quay/issues/2342))
- [f4c45814](https://github.com/quay/quay/commit/f4c458148abeade6a7934963c6d61a5133b946bb): bump types-ipaddress from 1.0.1 to 1.0.8 ([#2339](https://github.com/quay/quay/issues/2339))
- [94e019b9](https://github.com/quay/quay/commit/94e019b9c592c54b026d83d6c244c56974ffbeba): bump types-six from 1.16.2 to 1.16.21.9 ([#2333](https://github.com/quay/quay/issues/2333))
- [95196162](https://github.com/quay/quay/commit/95196162e3ab8ef42ad75a98ce0b851c2835fe99): bump moto from 4.1.4 to 4.2.5 ([#2330](https://github.com/quay/quay/issues/2330))
- [927de34f](https://github.com/quay/quay/commit/927de34f96b50d3b13340c86857913473ca08906): bump types-mock from 4.0.3 to 5.1.0.2 ([#2328](https://github.com/quay/quay/issues/2328))
- [68ef32a5](https://github.com/quay/quay/commit/68ef32a55bf8df18b211a8c9b22a91dc02fa5ee9): bump types-deprecated from 1.2.3 to 1.2.9.3 ([#2315](https://github.com/quay/quay/issues/2315))
- [fb735b5f](https://github.com/quay/quay/commit/fb735b5fa588a533a5e89db051719cbbf3b18267): bump parameterized from 0.8.1 to 0.9.0 ([#2312](https://github.com/quay/quay/issues/2312))
- [eeff86cc](https://github.com/quay/quay/commit/eeff86cc4f62320b7f39bbdb62d5499e02153bb3): bump types-beautifulsoup4 from 4.12.0.5 to 4.12.0.6 ([#2288](https://github.com/quay/quay/issues/2288))
- [31e435c6](https://github.com/quay/quay/commit/31e435c66ff3841fc29c63e6354930283b052554): bump postcss from 8.4.29 to 8.4.31 in /config-tool/pkg/lib/editor ([#2284](https://github.com/quay/quay/issues/2284))
- [0349923f](https://github.com/quay/quay/commit/0349923fcece1d1baf8c51a4b94b2f7f08c89df3): bump prettier from 3.0.2 to 3.0.3 in /web ([#2272](https://github.com/quay/quay/issues/2272))
- [5e3f1329](https://github.com/quay/quay/commit/5e3f13299289dcf12a0a52beea78234fc6084081): bump axios-mock-adapter from 1.20.0 to 1.22.0 in /web ([#2222](https://github.com/quay/quay/issues/2222))
- [d50fef9e](https://github.com/quay/quay/commit/d50fef9e603bf6d8ca0dcdafb77c9224c32814cb): bump json5 from 1.0.1 to 1.0.2 in /config-tool/pkg/lib/editor ([#2211](https://github.com/quay/quay/issues/2211))
- [a0e1f4ae](https://github.com/quay/quay/commit/a0e1f4ae5341562c683c439ef5071c78f70cd70f): bump css-minimizer-webpack-plugin from 3.4.1 to 5.0.1 in /web ([#2239](https://github.com/quay/quay/issues/2239))
- [0ff7862d](https://github.com/quay/quay/commit/0ff7862df8b0e56227547e6c468191c7d0261b10): bump eslint from 8.48.0 to 8.49.0 in /web ([#2220](https://github.com/quay/quay/issues/2220))
- [c7f9bc04](https://github.com/quay/quay/commit/c7f9bc048326c0ba3166dcd2ebfd567c3c6c0a66): bump eslint-plugin-import from 2.28.0 to 2.28.1 in /web ([#2203](https://github.com/quay/quay/issues/2203))
- [ac0a0e7c](https://github.com/quay/quay/commit/ac0a0e7ccfe25f452bd2443819f648ef74a9ede8): bump httmock from 1.3.0 to 1.4.0 ([#2200](https://github.com/quay/quay/issues/2200))
- [5c5f45f5](https://github.com/quay/quay/commit/5c5f45f5e06a975106ed67d32be924c5fb861c81): bump webpack-merge from 5.8.0 to 5.9.0 in /web ([#2204](https://github.com/quay/quay/issues/2204))
- [109bc965](https://github.com/quay/quay/commit/109bc965e2e1ca2d4999eadc4d21a9de998156ae): bump eslint from 8.13.0 to 8.48.0 in /web ([#2206](https://github.com/quay/quay/issues/2206))
- [706a873d](https://github.com/quay/quay/commit/706a873db13cb75fd795b446e5febda8e2761af6): bump prettier from 2.6.2 to 3.0.2 in /web ([#2146](https://github.com/quay/quay/issues/2146))
- [e400a0c2](https://github.com/quay/quay/commit/e400a0c22c5f89dd35d571654b13d262b1f6e3b3): bump source-map-loader from 0.1.5 to 1.1.3 in /config-tool/pkg/lib/editor ([#2181](https://github.com/quay/quay/issues/2181))
- [0e75ffa3](https://github.com/quay/quay/commit/0e75ffa34230a6749543f6cea61d258443ed19a1): bump svg-url-loader from 7.1.1 to 8.0.0 in /web ([#2176](https://github.com/quay/quay/issues/2176))
- [72ae94ea](https://github.com/quay/quay/commit/72ae94ea7f230fb1670e5d69831704336c1b981a): bump angular-mocks and [@types](https://github.com/types)/angular-mocks in /config-tool/pkg/lib/editor ([#2172](https://github.com/quay/quay/issues/2172))
- [d51dae5f](https://github.com/quay/quay/commit/d51dae5f21cce5fb1d1f49e4b078fd5fb24e74dd): bump webpack-cli from 3.3.9 to 4.10.0 in /config-tool/pkg/lib/editor ([#2170](https://github.com/quay/quay/issues/2170))
- [4fcc2c94](https://github.com/quay/quay/commit/4fcc2c9427c2981b53c58be5d190206f43ab6ac5): bump qs in /config-tool/pkg/lib/editor ([#2072](https://github.com/quay/quay/issues/2072))
- [ceac5375](https://github.com/quay/quay/commit/ceac5375a5cf31a1739cb52b80145f6c710abe1f): bump eslint-config-prettier in /web ([#2145](https://github.com/quay/quay/issues/2145))
- [4594d647](https://github.com/quay/quay/commit/4594d64758a5a850ec39d078f0c547ebe1b5d151): bump style-loader from 3.3.1 to 3.3.3 in /web ([#2119](https://github.com/quay/quay/issues/2119))
- [79a49be3](https://github.com/quay/quay/commit/79a49be3c1d630f3ea89825146005318fc147eb2): bump eslint-plugin-react-hooks in /web ([#2118](https://github.com/quay/quay/issues/2118))
- [6dbf6f16](https://github.com/quay/quay/commit/6dbf6f1627a90e29a2fbf07b6f48d879f4278481): bump css-loader from 6.7.1 to 6.8.1 in /web ([#2121](https://github.com/quay/quay/issues/2121))
- [24da4954](https://github.com/quay/quay/commit/24da495449d89914f0cc6af895b36fdb1ceab5ac): bump eslint-plugin-jsx-a11y from 6.5.1 to 6.7.1 in /web ([#2100](https://github.com/quay/quay/issues/2100))
- [8e0ca32c](https://github.com/quay/quay/commit/8e0ca32c8fc90cd7cb8b535297c8bf2142eae5fd): bump webpack-cli from 4.9.2 to 5.1.4 in /web ([#2102](https://github.com/quay/quay/issues/2102))
- [8c4d37a4](https://github.com/quay/quay/commit/8c4d37a4e875eb50e61d018053b4ba0264f0aeab): bump word-wrap in /config-tool/pkg/lib/editor ([#2074](https://github.com/quay/quay/issues/2074))
- [c8b788f1](https://github.com/quay/quay/commit/c8b788f1ca33f3e1de00d8510197ca5bd50b5152): bump sass from 1.51.0 to 1.64.1 in /web ([#2048](https://github.com/quay/quay/issues/2048))
- [0bf9269e](https://github.com/quay/quay/commit/0bf9269e607679d8ad7dcdaf514440fc010c656f): bump terser-webpack-plugin from 5.3.3 to 5.3.9 in /web ([#2046](https://github.com/quay/quay/issues/2046))
- [f8bb624a](https://github.com/quay/quay/commit/f8bb624a13dde24eeaf174259ebd0bf215aa8613): bump eslint-plugin-import from 2.26.0 to 2.28.0 in /web ([#2067](https://github.com/quay/quay/issues/2067))
- [f30eefb5](https://github.com/quay/quay/commit/f30eefb5a4045143562f95dab203bede860559e5): bump ts-node from 10.7.0 to 10.9.1 in /web ([#2033](https://github.com/quay/quay/issues/2033))
- [a653e147](https://github.com/quay/quay/commit/a653e147d7cba50fc21becb867c81f5bea1667c1): bump types-cryptography from 3.3.7 to 3.3.23.2 ([#2030](https://github.com/quay/quay/issues/2030))
- [e4f61049](https://github.com/quay/quay/commit/e4f610491021f8e7438b4edad9bd5e2a06c55825): bump ts-loader from 9.3.0 to 9.4.4 in /web ([#2031](https://github.com/quay/quay/issues/2031))
- [8d5fa6ff](https://github.com/quay/quay/commit/8d5fa6ffd6ebec2f5887c966327f97ab306120c1): bump eslint-plugin-react from 7.29.4 to 7.33.0 in /web ([#2032](https://github.com/quay/quay/issues/2032))
- [fb9ea5f1](https://github.com/quay/quay/commit/fb9ea5f1ca65268b42513420293d51e096b30bb6): bump webpack from 5.72.1 to 5.76.0 in /web ([#1787](https://github.com/quay/quay/issues/1787))
### Chore
- [636f31af](https://github.com/quay/quay/commit/636f31af8b5b211c87d5ee8750fa2ed3429d4bbb): add build dependencies for build dependencies ([#2396](https://github.com/quay/quay/issues/2396))
- [cd444974](https://github.com/quay/quay/commit/cd4449740842ec4f606222fc1accdd9687e76a31): add hack/update-requirements-build.sh ([#2384](https://github.com/quay/quay/issues/2384))
- [6c186928](https://github.com/quay/quay/commit/6c1869288c67e1155b03ad5ed62b45b22864267f): update dependabot.yml ([#2329](https://github.com/quay/quay/issues/2329))
- [3d896ba1](https://github.com/quay/quay/commit/3d896ba125880961ad54529a5dec070d4e2b205e): add requirements-build.txt ([#2321](https://github.com/quay/quay/issues/2321))
- [57d9daab](https://github.com/quay/quay/commit/57d9daab6095e822a15955d48c5af4a05b0d2460): enable dependabot for config-tool ([#2285](https://github.com/quay/quay/issues/2285))
- [5dbdd378](https://github.com/quay/quay/commit/5dbdd378385d011db4e13a34aac1852309916765): add tests for blobupload ([#2216](https://github.com/quay/quay/issues/2216))
- [44d24a25](https://github.com/quay/quay/commit/44d24a259e53bad8a62d5a3a831bc9d14685c822): remove cached data from the final image ([#2275](https://github.com/quay/quay/issues/2275))
- [41d49eb6](https://github.com/quay/quay/commit/41d49eb6a487a8841d342c3895354b371f9bcf10): preinstall grpcio for Z ([#2263](https://github.com/quay/quay/issues/2263))
- [6bdb1147](https://github.com/quay/quay/commit/6bdb1147a05e659832c465a943b6197bfd6eb34a): fix missing grpc build with openssl for Z ([#2262](https://github.com/quay/quay/issues/2262))
- [e1e98e96](https://github.com/quay/quay/commit/e1e98e96319b2949496a5983713a8ba63b13b389): fix failing nightly and also use ssh action for ppc64le ([#2261](https://github.com/quay/quay/issues/2261))
- [912f99c1](https://github.com/quay/quay/commit/912f99c174aa659b49a2c464b3c8df6d634f85bc): add **/node_modules to dockerignore ([#2258](https://github.com/quay/quay/issues/2258))
- [ef1b4a97](https://github.com/quay/quay/commit/ef1b4a97b05103e7b2259fddef325fd9ab98745c): make eslint to ignore css files ([#2243](https://github.com/quay/quay/issues/2243))
- [7ab69bed](https://github.com/quay/quay/commit/7ab69bed6be00735fc55cec4c6d28bf118fe0856): don't chmod on every file in Dockerfile ([#2233](https://github.com/quay/quay/issues/2233))
- [72f7c64e](https://github.com/quay/quay/commit/72f7c64ed6511ba9c0c140eb76aa99a765e6b393): update werkzeug and related package versions (PROJQUAY-5098) ([#1982](https://github.com/quay/quay/issues/1982))
- [fb29b525](https://github.com/quay/quay/commit/fb29b52581cd33c4c9184bcff726de55651d107e): add /config-tool/pkg/lib/editor to dependabot.yml ([#2165](https://github.com/quay/quay/issues/2165))
- [bda3de65](https://github.com/quay/quay/commit/bda3de656b1e46be46daabfcf17cfc2f731d4936): remove set buildx rc version as not needed anymore ([#2162](https://github.com/quay/quay/issues/2162))
- [5f63b3a7](https://github.com/quay/quay/commit/5f63b3a7bb878c0393a24e313cc9b180b8885ccd): drop deprecated tables and remove unused code (PROJQUAY-522) ([#2089](https://github.com/quay/quay/issues/2089))
- [e72773bb](https://github.com/quay/quay/commit/e72773bbce80b9f2422e66739b0d030137313e80): add cypress tests for config-tool ([#2152](https://github.com/quay/quay/issues/2152))
- [5c871540](https://github.com/quay/quay/commit/5c8715400930fcb386529b130ba06c9b590cd5c7): upload coverage reports to Codecov ([#2150](https://github.com/quay/quay/issues/2150))
- [cf687a61](https://github.com/quay/quay/commit/cf687a619f27eebb052aaf15a230719a4e31e732): fix s390x nightly ci ([#2138](https://github.com/quay/quay/issues/2138))
- [35d27085](https://github.com/quay/quay/commit/35d2708583ec3bcf3252c23f6925889371116b28): fix ppc64le nightly test run ([#2134](https://github.com/quay/quay/issues/2134))
- [f7d08df9](https://github.com/quay/quay/commit/f7d08df9eb2664b7cbc1e3b52a31d556433ba7b5): remove husky ([#2130](https://github.com/quay/quay/issues/2130))
- [4363c516](https://github.com/quay/quay/commit/4363c516677af78124c58cf531844e1128ebaea4): run pre-commit checks only on pull requests ([#2129](https://github.com/quay/quay/issues/2129))
- [b051a00c](https://github.com/quay/quay/commit/b051a00c9ce2ae51c404ca32ac249c4c6e52896d): fix build of PyYAML on linux/ppc64le ([#2109](https://github.com/quay/quay/issues/2109))
- [20845a13](https://github.com/quay/quay/commit/20845a136f31a2206af22f947a085d0a973e4736): Remove reference to Image table from the backfill replication script ([#2110](https://github.com/quay/quay/issues/2110))
- [309c007b](https://github.com/quay/quay/commit/309c007b0f3efedcc5111638845caa4d72f8236e): updated build-and-publish for s390x ([#2098](https://github.com/quay/quay/issues/2098))
- [e5d7fc57](https://github.com/quay/quay/commit/e5d7fc57a64413cad59668056297b423dc014ddf): Run pre-commit checks on pull requests ([#1978](https://github.com/quay/quay/issues/1978))
- [5e76a528](https://github.com/quay/quay/commit/5e76a528e44993b70ae9f86f03533665b048ff4f): Add build dependency for reportlab ([#2087](https://github.com/quay/quay/issues/2087))
- [17c94959](https://github.com/quay/quay/commit/17c94959521e0ec347530228aaedec4395ff5f34): Reformat python scripts in config-tool
- [efc3206d](https://github.com/quay/quay/commit/efc3206da7b4c57b9ffc51df767bd6136c61dcff): Merge config-tool/.github into .github
- [02463a7e](https://github.com/quay/quay/commit/02463a7e1ae70f35b333ebba40fd51e59fcf3c6d): Rename github.com/quay/config-tool to github.com/quay/quay/config-tool
- [9aa07cc0](https://github.com/quay/quay/commit/9aa07cc0dcfef8b45ad5fa4a87bbf810bd0376dd): Use config-tool from this repo
- [7a487644](https://github.com/quay/quay/commit/7a487644e1c121d132d00023c8157658684b8704): use isinstance to check instance type ([#2068](https://github.com/quay/quay/issues/2068))
- [c1a5fceb](https://github.com/quay/quay/commit/c1a5fcebbe8e61374cb5471d535a8602321f3bfc): Bump pushgateway to 1.6.0 (PROJQUAY-5874) ([#2040](https://github.com/quay/quay/issues/2040))
- [4a816c76](https://github.com/quay/quay/commit/4a816c765d4fd961a029e13e0ee6fab5695a80e1): Add build dependencies for lxml 4.9.2 ([#2053](https://github.com/quay/quay/issues/2053))
- [8f8fff74](https://github.com/quay/quay/commit/8f8fff74f3cc78389e33f24174e0d918530c844b): Do not require ticket for build(deps-dev) ([#2037](https://github.com/quay/quay/issues/2037))
- [ab13b4ce](https://github.com/quay/quay/commit/ab13b4ce24f9badf5a52bb699ad226755539b44f): Add config for dependabot ([#2029](https://github.com/quay/quay/issues/2029))
- [2fbc7a09](https://github.com/quay/quay/commit/2fbc7a09f828932a7ef412d24ebe4f0094b57a73): Fix regexp in pull_request_linting.yaml ([#2026](https://github.com/quay/quay/issues/2026))
- [0555695e](https://github.com/quay/quay/commit/0555695e218342c51fe8da08c30ab8da43d49f5e): Use stable Cython ([#2021](https://github.com/quay/quay/issues/2021))
- [1b00005f](https://github.com/quay/quay/commit/1b00005fb41cbbde295ad2c15de7be7625b0269d): Use latest go-toolset for config-tool ([#2019](https://github.com/quay/quay/issues/2019))
- [ae53ae8b](https://github.com/quay/quay/commit/ae53ae8bd249a0dd75e95f44d00903245601b3ab): Bump PyYAML ([#2017](https://github.com/quay/quay/issues/2017))
- [380aa777](https://github.com/quay/quay/commit/380aa7770c3ee9ec50e5ccb12ab85f87c52a665a): Use conventional-commit-checker-action for Jira check (PROJQUAY-5672) ([#1990](https://github.com/quay/quay/issues/1990))
- [ea49bb53](https://github.com/quay/quay/commit/ea49bb53a33db3153be403b30ab045f563f24849): Bump mypy ([#1962](https://github.com/quay/quay/issues/1962))
- [64fe64fd](https://github.com/quay/quay/commit/64fe64fda24161174a34894cb4c62f1f647c8995): Updated checks for s390x ZVSI builder ([#1987](https://github.com/quay/quay/issues/1987))
- [d622a788](https://github.com/quay/quay/commit/d622a788d72e1783cf1b249d6376d066b61e1e2f): Unhandled exceptions should not occur during OCI conformance tests ([#1984](https://github.com/quay/quay/issues/1984))
- [6c26a591](https://github.com/quay/quay/commit/6c26a591e3701031ba4ee5f730edcfcb8a08a168): updated secrets and added status of ZVSI ([#1981](https://github.com/quay/quay/issues/1981))
- [13351ac6](https://github.com/quay/quay/commit/13351ac6b79386eb9b285eabd873cabf98185abe): Bump dependencies that cause syntax warnings (PROJQUAY-5650) ([#1976](https://github.com/quay/quay/issues/1976))
- [e317abc3](https://github.com/quay/quay/commit/e317abc3e61830f526447fddda83469870ac3251): Bump gitleaks, add isort and lint-staged to pre-commit ([#1963](https://github.com/quay/quay/issues/1963))
- [d48df9b2](https://github.com/quay/quay/commit/d48df9b251ef929923d295e3905832c9e552edf7): deprecate image table support (PROJQUAY-522) ([#1841](https://github.com/quay/quay/issues/1841))
- [6d7c6d73](https://github.com/quay/quay/commit/6d7c6d73327ec521550ca95daa7f5defb83e335f): Use buildx v0.11.0-rc2 ([#1960](https://github.com/quay/quay/issues/1960))
- [3b588041](https://github.com/quay/quay/commit/3b58804172c56da7f17fda74a9b8962b6e14c2a1): Get REGISTRY from GitHub secrets ([#1958](https://github.com/quay/quay/issues/1958))
- [bad80f11](https://github.com/quay/quay/commit/bad80f11edb13ebbcb2dc0c0e725b8fc39621c7d): Disable provenance for Quay images ([#1955](https://github.com/quay/quay/issues/1955))
- [1a96bd2f](https://github.com/quay/quay/commit/1a96bd2f299f1199436a264f0d3afb8ff6f1ab60): updated s390x builder ([#1931](https://github.com/quay/quay/issues/1931))
### Chore: Fix Isort Config And Remove `Isort
- [84fa795a](https://github.com/quay/quay/commit/84fa795ae7567a0e249c5e50fe0e16dd8a8897ae): skip_file` ([#2196](https://github.com/quay/quay/issues/2196))
### Compliance
- [8314a585](https://github.com/quay/quay/commit/8314a5851564025ed353cb968bcd5e3ddc4cb432): Update export hold email (PROJQUAY-6024) ([#2230](https://github.com/quay/quay/issues/2230))
### Config
- [eede634a](https://github.com/quay/quay/commit/eede634af92c09c3f9f4e363d5f3a16558e1521d): updating GeoLite2-Country (PROJQUAY-6023) ([#2218](https://github.com/quay/quay/issues/2218))
- [e6224142](https://github.com/quay/quay/commit/e622414280f4760fe449800b0429eb84f71271b5): Enable notifications for new indexes by default (PROJQUAY-5682) ([#1993](https://github.com/quay/quay/issues/1993))
### Core
- [700884f4](https://github.com/quay/quay/commit/700884f462828f406dea64cc381ddc7e595d7374): fix nightly test failures ([#2133](https://github.com/quay/quay/issues/2133))
### Data
- [ff68f86c](https://github.com/quay/quay/commit/ff68f86c90f1931675ff3d2655287683c518cdc7): Fix error getting tag while calculating scan results SLO ([#1952](https://github.com/quay/quay/issues/1952))
### Database
- [d47cea46](https://github.com/quay/quay/commit/d47cea46fa99eb01151fe50942a67d63dd6e77b3): remove foreign key constraints from deprecated tables (PROJQUAY-4879) ([#1348](https://github.com/quay/quay/issues/1348))
### Deploy
- [848ed3c3](https://github.com/quay/quay/commit/848ed3c333d1f85b2c3b9ca7805534d4718263de): update configmap for slo dashboard (PROJQUAY-6221) ([#2419](https://github.com/quay/quay/issues/2419))
- [ee2e12ab](https://github.com/quay/quay/commit/ee2e12abd4413c6df12c892be6aba7239b8d37f1): Add a startup probe to the py3 deployment (PROJQUAY-522) ([#2149](https://github.com/quay/quay/issues/2149))
### Documentation
- [b42f2d7a](https://github.com/quay/quay/commit/b42f2d7a23a2373300a5dc04a6b87ee56acf4a7a): Change tag template link location for build triggers (PROJQUAY-6044) ([#2234](https://github.com/quay/quay/issues/2234))
### Feat(Config-Tool)
- [9ab64f20](https://github.com/quay/quay/commit/9ab64f205239994ce003578ca242e89af0f49a49): add SSL client authentication (PROJQUAY-2417) ([#2157](https://github.com/quay/quay/issues/2157))
### Federationuser(Ldap)
- [4719f46c](https://github.com/quay/quay/commit/4719f46c2c837714e6a89cde4358b9de13e96563): adding keepalive settings for LDAP connections (PROJQUAY-5137) ([#1975](https://github.com/quay/quay/issues/1975))
### Fix
- [1643b40c](https://github.com/quay/quay/commit/1643b40c3a448d5405d2272255cb6b42179464c9): Pass CONTAINER_RUNTIME to quay-builder (PROJQUAY-5910) ([#2096](https://github.com/quay/quay/issues/2096))
### Frontend
- [02feee3e](https://github.com/quay/quay/commit/02feee3efe1539dfe0b364e3261251130360c6bd): Change frontend name so that correct paths will be generated (RHCLOUD-28385) ([#2244](https://github.com/quay/quay/issues/2244))
### Geo-Rep
- [88fd1bae](https://github.com/quay/quay/commit/88fd1bae9a12428d715d93e635e3d60ea84d1846): Initialize features from config in util script (PROJQUAY-5627) ([#1966](https://github.com/quay/quay/issues/1966))
- [2d93fc7c](https://github.com/quay/quay/commit/2d93fc7cd09236412a108b5f644a0470c9ac7c1e): Add util script to remove geo-rep location and corresponding image locations (PROJQUAY-4995) ([#1892](https://github.com/quay/quay/issues/1892))
### Georep
- [faa0315a](https://github.com/quay/quay/commit/faa0315a04cf6eb8e55197d303f556974035464c): Add error handling for remove location script (PROJQUAY-5878) ([#2071](https://github.com/quay/quay/issues/2071))
### Georeplication
- [abfde5b9](https://github.com/quay/quay/commit/abfde5b9d2cf7d7145e68a00c9274011b4fe0661): Enqueue blobs for replication on manifest list pushes (PROJQUAY-5256) ([#2212](https://github.com/quay/quay/issues/2212))
### Init(Postgresclientcerts)
- [324844bd](https://github.com/quay/quay/commit/324844bd5ca0f18c20823e805814e4251de2912a): add Postgresql client certificate authentication (PROJQUAY-2417) ([#2156](https://github.com/quay/quay/issues/2156))
### Logs
- [3fd695cf](https://github.com/quay/quay/commit/3fd695cf8627bddf04ad83e8ddcc4e6ca89bfb08): Add autologin to splunk's connect() to allow retries (PROJQUAY-5621) ([#1956](https://github.com/quay/quay/issues/1956))
- [f5be32d8](https://github.com/quay/quay/commit/f5be32d840822d8ce5fcaa303d3586bc25342172): ssl_ca_path should be optional (PROJQUAY-4993) ([#1913](https://github.com/quay/quay/issues/1913))
### Marketplace
- [685cbef1](https://github.com/quay/quay/commit/685cbef1a2ad7bdf27a2ed6728814ea7576208b7): use get method for ebsAccountNumber lookup (PROJQUAY-6219) ([#2417](https://github.com/quay/quay/issues/2417))
### Oci
- [d193d90a](https://github.com/quay/quay/commit/d193d90a0ef1bc14eef348d6f19dc6498180e405): Allow optional components in the image config to be set to "null" (PROJQUAY-5634) ([#1961](https://github.com/quay/quay/issues/1961))
### Pagination
- [f56382ee](https://github.com/quay/quay/commit/f56382eeb96e7fafb7a3758954c54c0b43af3ccd): Fixing paginate for /api/v1/superuser/logs API ([#2006](https://github.com/quay/quay/issues/2006))
### Quota
- [2a672551](https://github.com/quay/quay/commit/2a672551fc8bc55e2b59f3c9bfacb76f96692a66): prevent tag creation on rejected manifest (PROJQUAY-3906) ([#2247](https://github.com/quay/quay/issues/2247))
- [9a9355e5](https://github.com/quay/quay/commit/9a9355e5f2202ed4c50184fdfc33ba8ce3e9cc14): adding indexes to the quota size tables (PROJQUAY-6048) ([#2268](https://github.com/quay/quay/issues/2268))
- [dcdf132f](https://github.com/quay/quay/commit/dcdf132fceff9ac12acc5b0ce285b2474111084b): removing extra calls to get namespace quotas (PROJQUAY-6048) ([#2267](https://github.com/quay/quay/issues/2267))
- [d453882b](https://github.com/quay/quay/commit/d453882bd0e2029e5d4b07f28514b79a55e2964b): fixing registry total worker failing to start (PROJQUAY-6010) ([#2217](https://github.com/quay/quay/issues/2217))
- [db4fc041](https://github.com/quay/quay/commit/db4fc04124af1606af2f221ddf1fa59d5742ba30): disabling quota worker when running config editor (PROJQUAY-5925) ([#2131](https://github.com/quay/quay/issues/2131))
### Reconfigure
- [f013a27b](https://github.com/quay/quay/commit/f013a27b6f37e842f1cef646f34a3a675513142d): Remove ca-bundle.crt and service-ca.crt (PROJQUAY-5233) ([#2231](https://github.com/quay/quay/issues/2231))
### Revert "Build(Deps)
- [e3c15efa](https://github.com/quay/quay/commit/e3c15efa32b2927cf69e954f841a02ba2c3c99b9): bump tldextract from 2.2.2 to 3.6.0 ([#2310](https://github.com/quay/quay/issues/2310))" ([#2414](https://github.com/quay/quay/issues/2414))
- [cb9d068b](https://github.com/quay/quay/commit/cb9d068b8eb96969aac029e74ffa379fa08abc1d): bump peewee from 3.13.1 to 3.16.3 ([#2323](https://github.com/quay/quay/issues/2323))" ([#2398](https://github.com/quay/quay/issues/2398))
- [4e88cd8b](https://github.com/quay/quay/commit/4e88cd8b80478d3d481a02bfc53bc2900cdea7f9): bump pymysql from 0.9.3 to 1.1.0" ([#2397](https://github.com/quay/quay/issues/2397))
### Revert "Chore
- [93033cb4](https://github.com/quay/quay/commit/93033cb4276bc065e6e4023f38144edc3d0ca16e): Bump PyYAML ([#2017](https://github.com/quay/quay/issues/2017))" ([#2044](https://github.com/quay/quay/issues/2044))
- [284b1059](https://github.com/quay/quay/commit/284b10595b15c40a6c1c65c51eba40b860cb38b8): Use stable Cython ([#2021](https://github.com/quay/quay/issues/2021))" ([#2043](https://github.com/quay/quay/issues/2043))
- [6b0c22d5](https://github.com/quay/quay/commit/6b0c22d5a769a4f67b2b726a3591672ed211df73): Bump dependencies that cause syntax warnings (PROJQUAY-5650) ([#1976](https://github.com/quay/quay/issues/1976))" ([#1983](https://github.com/quay/quay/issues/1983))
### Secscan
- [54fcfd14](https://github.com/quay/quay/commit/54fcfd14f9b0b6632e0dffe0b5ade7216eb7708d): Cache clair vuln reports (PROJQUAY-6057) ([#2245](https://github.com/quay/quay/issues/2245))
- [8d0ee386](https://github.com/quay/quay/commit/8d0ee3865ed6a60c9086a123dee032a4d8e1c906): fix metrics to track all request types to secscan service (PROJQUAY-3839) ([#2108](https://github.com/quay/quay/issues/2108))
- [93086fa5](https://github.com/quay/quay/commit/93086fa5888601996c7d4dfe4b936ed59c2ecd9c): update error from secscan delete (PROJQUAY-0000) ([#2077](https://github.com/quay/quay/issues/2077))
- [0ea48269](https://github.com/quay/quay/commit/0ea4826956b534b22e068e10c0112cce52f7c346): garbage collect manifests ([#1663](https://github.com/quay/quay/issues/1663))
### Secscan_model
- [50224e2d](https://github.com/quay/quay/commit/50224e2dd1d5d37bb058887b82bed1aea024356c): attempt urldecoding `fixed_in_version` (PROJQUAY-5886) ([#2060](https://github.com/quay/quay/issues/2060))
### Setup
- [ce1c043e](https://github.com/quay/quay/commit/ce1c043e8fab28ebc96bff4883d62160e4dba96f): Add models pkgs to setup.py (PROJQUAY-5414) ([#2002](https://github.com/quay/quay/issues/2002))
### Storage
- [3e9cff6c](https://github.com/quay/quay/commit/3e9cff6cf314c3f8a08fbf0b47e71173c4a1e1d7): adding maximum_chunk_size_gb storage option (PROJQUAY-2679) ([#2186](https://github.com/quay/quay/issues/2186))
- [af97203e](https://github.com/quay/quay/commit/af97203ec7815f075b2200d6af29d3c3c716e980): Check for request context before getting host header (PROJQUAY-5860) ([#2024](https://github.com/quay/quay/issues/2024))
- [8cacdf19](https://github.com/quay/quay/commit/8cacdf19b2662e6add0b2613e0a423f4ec20c6d7): make cloudfront_distribution_org_overrides optional (PROJQUAY-5788) ([#2004](https://github.com/quay/quay/issues/2004))
- [c49077cf](https://github.com/quay/quay/commit/c49077cff641d03ef2891c396c54db5b28707a8b): Do nothing when completing chunked upload if chunk list is empty (PROJQUAY-5489) ([#2005](https://github.com/quay/quay/issues/2005))
- [a985bb6c](https://github.com/quay/quay/commit/a985bb6c28949afb6043ac1b69a224e306f1f5df): Add Host header matching for multi CDN storage (PROJQUAY-5415) ([#1969](https://github.com/quay/quay/issues/1969))
### Superuser
- [6a39d59f](https://github.com/quay/quay/commit/6a39d59f6514bc11fda300027fbabdbe88dac447): lowering page limit (PROJQUAY-5178) ([#1912](https://github.com/quay/quay/issues/1912))
### UI
- [f1f61024](https://github.com/quay/quay/commit/f1f6102464b409a3aafb4e6cdc6fefbf159a82a2): Delete normal user org by super user (PROJQUAY-5639) ([#1994](https://github.com/quay/quay/issues/1994))
- [6b9c0f72](https://github.com/quay/quay/commit/6b9c0f7259b28dee2fe126f196a1076325f58c82): Replace time to wait with event waits in cypress tests ([#1980](https://github.com/quay/quay/issues/1980))
- [00b3a02e](https://github.com/quay/quay/commit/00b3a02ef088d1a30028b08ad0a4dbf3278f753b): Robot Accounts page perms fix (PROJQUAY-5487) ([#1977](https://github.com/quay/quay/issues/1977))
### Ui
- [2ec1eea3](https://github.com/quay/quay/commit/2ec1eea340524ad7cbdff8ef8d654d302c217772): fixing RobotAccount AddToTeam console error (PROJQUAY-6233) ([#2424](https://github.com/quay/quay/issues/2424))
- [88f40d9a](https://github.com/quay/quay/commit/88f40d9a50ca9cf72febed79ed34b4a7c96a97fd): Implement drawer to add a new team member (PROJQUAY-6032) ([#2270](https://github.com/quay/quay/issues/2270))
- [72f0a895](https://github.com/quay/quay/commit/72f0a895d48d2c4e3ef75f59869e9123c0ec63b3): Add organization and user account settings (PROJQUAY-4553) ([#2151](https://github.com/quay/quay/issues/2151))
- [5d5e7c16](https://github.com/quay/quay/commit/5d5e7c16b13247723f09190f97e6a297ff9b2264): Add create new team button (PROJQUAY-5685) ([#2309](https://github.com/quay/quay/issues/2309))
- [81bf6347](https://github.com/quay/quay/commit/81bf63474942351422055f4cb4970284b6042f86): Add bulk deletion for default permissions (PROJQUAY-6093) ([#2336](https://github.com/quay/quay/issues/2336))
- [38fd992f](https://github.com/quay/quay/commit/38fd992f305cb271f1481a3deaf87d80bc7b67e4): Fix styling conflict with RedHatInsights (PROJQUAY-6085) ([#2418](https://github.com/quay/quay/issues/2418))
- [fb5eb3fa](https://github.com/quay/quay/commit/fb5eb3fa09974c31b0e4e56f77fbb4c2b7ec740a): Compact tables & extend page count to 20 (PROJQUAY-6183) ([#2412](https://github.com/quay/quay/issues/2412))
- [2b07f1af](https://github.com/quay/quay/commit/2b07f1afbb2832ab03c96953c0ade34a6a1a6901): Update all Patternfly deprecated components (PROJQUAY-6085) ([#2401](https://github.com/quay/quay/issues/2401))
- [7a407435](https://github.com/quay/quay/commit/7a40743593952f6ac48bb6bdbd7c80ebc0571878): Add missing props for create robot acocunt modal (PROJQUAY-6184) ([#2405](https://github.com/quay/quay/issues/2405))
- [ad6b1c83](https://github.com/quay/quay/commit/ad6b1c8367b62153e31e6785a805fa61de6561fd): fix for useTeams hook when data is null (PROJQUAY-6177) ([#2404](https://github.com/quay/quay/issues/2404))
- [27f1699b](https://github.com/quay/quay/commit/27f1699b72c213033bce99dfcddc9ee70f2d3dd2): Add delay after write operations (PROJQUAY-6146) ([#2400](https://github.com/quay/quay/issues/2400))
- [033bcf67](https://github.com/quay/quay/commit/033bcf677217e89c4d1396b6264ea27d82d8d656): Upgrade to PatternFly v5 (PROJQUAY-6085) ([#2281](https://github.com/quay/quay/issues/2281))
- [48b300a8](https://github.com/quay/quay/commit/48b300a8bfe2ad781bf938d64330ea01bde7b93c): adding alerts for robot account actions (PROJQUAY-5946) ([#2228](https://github.com/quay/quay/issues/2228))
- [e428d88a](https://github.com/quay/quay/commit/e428d88a8aef17440bcf996e0cf4885ec5ea8a9a): combining robot account hooks into a single file (PROJQUAY-5945) ([#2266](https://github.com/quay/quay/issues/2266))
- [ff602c2e](https://github.com/quay/quay/commit/ff602c2ef326526de0fa1c2ffaf5788bfc2e8263): adding robot account support for user namespace (PROJQUAY-5945) ([#2183](https://github.com/quay/quay/issues/2183))
- [b76fa5bc](https://github.com/quay/quay/commit/b76fa5bc9fa8b1dde7ddcac861f8fa81d00292c3): Default Permissions tab (PROJQUAY-4570) ([#1856](https://github.com/quay/quay/issues/1856))
- [8a704ae2](https://github.com/quay/quay/commit/8a704ae26cb7f0c0e84fde175214900e70792980): Fix public path for console dot (PROJQUAY-5938) ([#2194](https://github.com/quay/quay/issues/2194))
- [59288733](https://github.com/quay/quay/commit/59288733f97cb927f67e285834a23abc23f52aa1): Get public path form env variable (PROJQUAY-5938) ([#2193](https://github.com/quay/quay/issues/2193))
- [226684df](https://github.com/quay/quay/commit/226684dfc784b2cd549cf39aba5cc3184d015020): Teams and members (PROJQUAY-4569) ([#2007](https://github.com/quay/quay/issues/2007))
- [3ad94608](https://github.com/quay/quay/commit/3ad9460846cee83a23d4c4359f07e3cf2e91ab48): adding tag history panel (PROJQUAY-5720) ([#2115](https://github.com/quay/quay/issues/2115))
- [c62dae11](https://github.com/quay/quay/commit/c62dae11b3aca8f5463edb287ced2ce8a02214a3): adding delete tag by row (PROJQUAY-5933) ([#2117](https://github.com/quay/quay/issues/2117))
- [36a78ade](https://github.com/quay/quay/commit/36a78ade508e02cc431caaabf150e19c49b9cfe0): Robot Accounts tab fixes (PROJQUAY-5914) ([#2097](https://github.com/quay/quay/issues/2097))
- [a5d22fc4](https://github.com/quay/quay/commit/a5d22fc4b06b6375f2abeb58b6610b5b1f40c007): adding set expiration tag option (PROJQUAY-5290) ([#2059](https://github.com/quay/quay/issues/2059))
- [62ce1574](https://github.com/quay/quay/commit/62ce1574fa581cdf5a06172058c3e1683b18e5c4): adding edit labels tag operation (PROJQUAY-5290) ([#2028](https://github.com/quay/quay/issues/2028))
- [c8bc48e3](https://github.com/quay/quay/commit/c8bc48e3268656129d4b7c907e0bd35a4c9ffbd5): adding create tag option and generic alerts (PROJQUAY-5290) ([#1996](https://github.com/quay/quay/issues/1996))
- [65c1829b](https://github.com/quay/quay/commit/65c1829b82960ff6b59aa0120478a71bdcdf2a43): displaying quota totals on user namespaces (PROJQUAY-5581) ([#1953](https://github.com/quay/quay/issues/1953))
- [d7864ed4](https://github.com/quay/quay/commit/d7864ed4eeec57cdf9573b5d4cfadb33ba7ebb93): Add custom TOS support (PROJQUAY-5648) ([#1973](https://github.com/quay/quay/issues/1973))
- [3152b102](https://github.com/quay/quay/commit/3152b1021e70061737c39f18f849c2755b77f08c): display sizes as base 2  (PROJQUAY-5524) ([#1968](https://github.com/quay/quay/issues/1968))
- [78598d6a](https://github.com/quay/quay/commit/78598d6ab33c377979305229dc00ae8ee222c2cf): adding null check on dark logo ([#1942](https://github.com/quay/quay/issues/1942))
- [e97a3eb4](https://github.com/quay/quay/commit/e97a3eb48f083ace2ed47ee94eee43ebe3895d0b): changing quota configuration byte units to base 1000 (PROJQUAY-5595) ([#1939](https://github.com/quay/quay/issues/1939))
### User
- [dd96025f](https://github.com/quay/quay/commit/dd96025ff56f92f87042655cd65302a9d49e8b98): Support custom LDAP memberOf attribute (PROJQUAY-5928) ([#2406](https://github.com/quay/quay/issues/2406))
### User(Robots)
- [67028af9](https://github.com/quay/quay/commit/67028af9e22c2d5e3754e3700eaba8a71473eb50): disallow robot login and create (PROJQUAY-5968) ([#2155](https://github.com/quay/quay/issues/2155))
### [Redhat-3.10] Autoprune
- [3f733179](https://github.com/quay/quay/commit/3f7331794d3668ca84eb4ccb1b8498beabc61518): validating input to autoprune policy (PROJQUAY-6230) ([#2461](https://github.com/quay/quay/issues/2461))
### [Redhat-3.10] Federationuser(Ldap)
- [8ecfd47f](https://github.com/quay/quay/commit/8ecfd47f6a7ed1eb0321c789bc1730cb34ecf9b8): fixing keepalive settings for LDAP connections (PROJQUAY-5137) ([#2489](https://github.com/quay/quay/issues/2489))
### [Redhat-3.10] Secscan
- [db1c7368](https://github.com/quay/quay/commit/db1c7368253917b34650359774dcd2c9781e010c): enable gc for manifests by default (PROJQUAY-4126) ([#2486](https://github.com/quay/quay/issues/2486))
### [Redhat-3.10] Ui
- [304d35b8](https://github.com/quay/quay/commit/304d35b86def7bf6624a61e7585829df67307b23): Add form for repository state (PROJQUAY-5715) ([#2484](https://github.com/quay/quay/issues/2484))
- [026561ce](https://github.com/quay/quay/commit/026561ce932b237494b0f773714222f6950db38c): allow current day to be selected for tag expiration (PROJQUAY-6262) ([#2466](https://github.com/quay/quay/issues/2466))
### Pull Requests
- Merge pull request [#2065](https://github.com/quay/quay/issues/2065) from dmage/merge-config-tool


<a name="v3.9.6"></a>
## [v3.9.6] - 2024-01-09
### Reconfigure
- [25516930](https://github.com/quay/quay/commit/255169303def620618ec410294d34637852d8821): Add auth to comit to operator endpoint

<a name="v3.9.5"></a>
## [v3.9.5] - 2023-11-07
### Build(Deps)
- [384aa6e5](https://github.com/quay/quay/commit/384aa6e5df2af3ca4fd46b8f7243ca167676716a): bump urllib3 from 1.26.9 to 1.26.18 (PROJQUAY-6110) ([#2458](https://github.com/quay/quay/issues/2458))

<a name="v3.9.4"></a>
## [v3.9.4] - 2023-10-26
### Build(Deps)
- [ef2035c7](https://github.com/quay/quay/commit/ef2035c7489649542374ecc4792139ed9745f7f0): bump golang.org/x/net from 0.13.0 to 0.17.0 (PROJQUAY-6208) ([#2435](https://github.com/quay/quay/issues/2435))

<a name="v3.9.3"></a>
## [v3.9.3] - 2023-10-10
### Quota
- [a4a23414](https://github.com/quay/quay/commit/a4a23414f83a6878cce866686e9fcaf48b56dc8e): prevent tag creation on rejected manifest (PROJQUAY-3906) ([#2282](https://github.com/quay/quay/issues/2282))
### [Redhat-3.9] Build(Deps)
- [db00f7f7](https://github.com/quay/quay/commit/db00f7f7713071879a10f86d4d5b0707962dfe19): bump cypress from 10.10.0 to 12.17.4 in /web ([#2308](https://github.com/quay/quay/issues/2308))
### [Redhat-3.9] Chore
- [30132066](https://github.com/quay/quay/commit/30132066e32a462489dd5c0466e2c1efe43b387c): remove husky ([#2307](https://github.com/quay/quay/issues/2307))
### [Redhat-3.9] Reconfigure
- [8b47d3fd](https://github.com/quay/quay/commit/8b47d3fdd580737ca9a676ffbbfe3cdf3e451d21): Remove ca-bundle.crt and service-ca.crt (PROJQUAY-5233) ([#2257](https://github.com/quay/quay/issues/2257))

<a name="v3.9.2"></a>
## [v3.9.2] - 2023-09-19
### [Redhat-3.9] Api
- [a7555f48](https://github.com/quay/quay/commit/a7555f4813a62cf2e88a5b7fb58828ad6fe11303): fix duplicate robot accounts (PROJQUAY-5931) ([#2198](https://github.com/quay/quay/issues/2198))
### [Redhat-3.9] Georeplication
- [7152164c](https://github.com/quay/quay/commit/7152164c87b816a02b2d2689a0329f146a552e38): Enqueue blobs for replication on manifest list pushes (PROJQUAY-5256) ([#2232](https://github.com/quay/quay/issues/2232))

<a name="v3.9.1"></a>
## [v3.9.1] - 2023-08-30
### Build(Deps)
- [7d19eac7](https://github.com/quay/quay/commit/7d19eac7a0bdfb649f2be1f7de29f9e0d723d86b): bump certifi from 2022.12.7 to 2023.7.22 ([#2062](https://github.com/quay/quay/issues/2062))
- [d3b05d4b](https://github.com/quay/quay/commit/d3b05d4b8757fab82321e57db4065c682e0d0cda): bump reportlab from 3.5.55 to 3.6.13 (PROJQUAY-5691) ([#2056](https://github.com/quay/quay/issues/2056))
### Chore
- [dc67d473](https://github.com/quay/quay/commit/dc67d473e7a3820e90d71708793721e62f416667): v3.9.1 changelog bump (PROJQUAY-5937) ([#2154](https://github.com/quay/quay/issues/2154))
- [ea71ac15](https://github.com/quay/quay/commit/ea71ac151b10bc2f64f94d5a579e6c4fe3134b76): Bump pushgateway to 1.6.0 (PROJQUAY-5874) ([#2058](https://github.com/quay/quay/issues/2058))
- [0b3c93f0](https://github.com/quay/quay/commit/0b3c93f0e5a2f08f5e2d05266cb927a71076e248): Add build dependency for reportlab ([#2137](https://github.com/quay/quay/issues/2137))
- [a2e23e68](https://github.com/quay/quay/commit/a2e23e68d1058c88924ddba34c74144532845afb): Add build dependencies for lxml 4.9.2 ([#2136](https://github.com/quay/quay/issues/2136))
- [e8acc54f](https://github.com/quay/quay/commit/e8acc54fb01b1745a25e74c20ba4dec2254c3441): fix build of PyYAML on linux/ppc64le ([#2114](https://github.com/quay/quay/issues/2114))
### [Redhat-3.9] Chore
- [2032ffa7](https://github.com/quay/quay/commit/2032ffa742492c96050f4f3f710c5780f6195a53): pull changes for s390x from master ([#2107](https://github.com/quay/quay/issues/2107))
### [Redhat-3.9] Storage
- [a6776d94](https://github.com/quay/quay/commit/a6776d940c497c75948e436504d2ae2f065fe41f): adding maximum_chunk_size_gb storage option (PROJQUAY-2679) ([#2191](https://github.com/quay/quay/issues/2191))
### [Redhat-3.9] Ui
- [a659db25](https://github.com/quay/quay/commit/a659db25ec67a2237205ebb3c4a33c20cf61adf4): Robot Accounts tab fixes (PROJQUAY-5914) ([#2135](https://github.com/quay/quay/issues/2135))
- [7f54e765](https://github.com/quay/quay/commit/7f54e76599eec683633e16514a390ec9db61129c): displaying quota totals on user namespaces (PROJQUAY-5581) ([#2128](https://github.com/quay/quay/issues/2128))

<a name="v3.9.0"></a>
## [v3.9.0] - 2023-08-07
### API/UI
- [5c342969](https://github.com/quay/quay/commit/5c342969203e28124818407a97cf078aba6a47f6): Filtering of tags API through query parameter (PROJQUAY-5362) ([#1839](https://github.com/quay/quay/issues/1839))
### Api
- [b911d480](https://github.com/quay/quay/commit/b911d480cf801dbef929338f8458ee38c9780b78): allow manifests to be pulled by digest (PROJQUAY-5467) ([#1877](https://github.com/quay/quay/issues/1877))
- [84abdba0](https://github.com/quay/quay/commit/84abdba07616ffabb2afb42673ec0bf2cf5badd0): Allow setting multiple CORS_ORIGIN (PROJQUAY-5213) ([#1791](https://github.com/quay/quay/issues/1791))
### Arch
- [434c193b](https://github.com/quay/quay/commit/434c193b9408367fe1800f7e9a01e92ef59a6e86): Map aarch64 to arm64 in ARCH variable ([#1602](https://github.com/quay/quay/issues/1602))
- [d08298bc](https://github.com/quay/quay/commit/d08298bc60858ac6b2c07387116f03d439188d31): add ppc64le support to quay (PROJQUAY-4595) ([#1535](https://github.com/quay/quay/issues/1535))
### Auth
- [d34e9399](https://github.com/quay/quay/commit/d34e9399af9e02f4beb7ed59cc8ff7124ecfece2): Adding wraps to user namespace decorator (PROJQUAY-4694) ([#1607](https://github.com/quay/quay/issues/1607))
- [ea90cc4f](https://github.com/quay/quay/commit/ea90cc4f26a625f4d228dae9cd362be8c0cc9ce9): Speed up permissions loading (PROJQUAY-4004) ([#1566](https://github.com/quay/quay/issues/1566))
### Billing
- [2d949b3b](https://github.com/quay/quay/commit/2d949b3b2e5ac76c1415350cb908a942e89b85c4): allow changing subscription on empty stripe_id (PROJQUAY-5413) ([#1857](https://github.com/quay/quay/issues/1857))
- [e7a7b4a0](https://github.com/quay/quay/commit/e7a7b4a05003ed59f4ae7e1c5df9265d31a6b822): fallback to cards api if paymentmethod is not set (PROJQUAY-5129) ([#1826](https://github.com/quay/quay/issues/1826))
- [89725309](https://github.com/quay/quay/commit/89725309be8f73c5041513bd2d70adb5db4a24d7): update Stripe checkout to support 3DS (PROJQUAY-5129) ([#1818](https://github.com/quay/quay/issues/1818))
- [d05c32b9](https://github.com/quay/quay/commit/d05c32b9d11fd268b86198e2c62cc19179649f0a): update default subscription payment behavior ([#1778](https://github.com/quay/quay/issues/1778))
### Build
- [47141afc](https://github.com/quay/quay/commit/47141afc83a511bbd103aca82109071153d14687): disable push to backup repo for quayio-frontend (PROJQUAY-5229) ([#1834](https://github.com/quay/quay/issues/1834))
- [b7d95a18](https://github.com/quay/quay/commit/b7d95a180a56f08064b1662b6c5c30f4a07673cd): Add template for deploying quayio frontend in console (PROJQUAY-5229) ([#1835](https://github.com/quay/quay/issues/1835))
- [05e3773b](https://github.com/quay/quay/commit/05e3773b741289111d2590d0f1d909fd23c38166): Add build scripts for quay.io frontend (PROJQUAY-5229) ([#1833](https://github.com/quay/quay/issues/1833))
### Build(Deps)
- [f8146c2d](https://github.com/quay/quay/commit/f8146c2de847254bae690de9d3e099006142fbed): bump config-tool to v0.1.21 ([#2051](https://github.com/quay/quay/issues/2051)) ([#2057](https://github.com/quay/quay/issues/2057))
- [f0e97152](https://github.com/quay/quay/commit/f0e97152cde66cf4f6b02ba189d081545c0f8a5c): bump pypdf2 from 1.27.6 to 1.27.9 ([#2052](https://github.com/quay/quay/issues/2052))
- [debc5b4e](https://github.com/quay/quay/commit/debc5b4e3fbfd1803123559063fd52ac7e8cd743): bump requests from 2.27.1 to 2.31.0 ([#1985](https://github.com/quay/quay/issues/1985))
- [117c5a86](https://github.com/quay/quay/commit/117c5a86065608e7a819454181d4c6ab9d3fc5d0): bump dns-packet from 5.3.1 to 5.4.0 in /web ([#1771](https://github.com/quay/quay/issues/1771))
- [a4384dbd](https://github.com/quay/quay/commit/a4384dbd8640ae76d9c877f18fb0e217c4830584): bump decode-uri-component from 0.2.0 to 0.2.2 in /web ([#1684](https://github.com/quay/quay/issues/1684))
- [4455df84](https://github.com/quay/quay/commit/4455df84440fd1b71a3a4f663d867fed14387ff7): bump loader-utils from 1.4.0 to 1.4.2 in /web ([#1685](https://github.com/quay/quay/issues/1685))
- [44363562](https://github.com/quay/quay/commit/443635629e1d34487afb746c2d5dcd99e16a79d7): bump json5 from 1.0.1 to 1.0.2 in /web ([#1699](https://github.com/quay/quay/issues/1699))
- [774efe37](https://github.com/quay/quay/commit/774efe37657ae804e325a4f6ea0bd27e36aa763e): bump oauthlib from 3.2.1 to 3.2.2 ([#1738](https://github.com/quay/quay/issues/1738))
- [50b14fe8](https://github.com/quay/quay/commit/50b14fe8278c829f3a1df7494a3fd333162b9dca): bump pillow from 9.0.1 to 9.3.0 ([#1633](https://github.com/quay/quay/issues/1633))
- [f42497f9](https://github.com/quay/quay/commit/f42497f95f8e666bb3276434ee131114f922db93): reduce CVEs in dependencies and runtime environment (PROJQUAY-4777) ([#1644](https://github.com/quay/quay/issues/1644))
- [972cab14](https://github.com/quay/quay/commit/972cab147bfcc763be1106c69cfde771b8e663eb): bump certifi from 2019.11.28 to 2022.12.7 ([#1665](https://github.com/quay/quay/issues/1665))
- [70473f00](https://github.com/quay/quay/commit/70473f000b8f93acd3c15a0cde6dd2a837a4fc3f): bump wheel from 0.35.1 to 0.38.1 ([#1690](https://github.com/quay/quay/issues/1690))
- [0dd53edf](https://github.com/quay/quay/commit/0dd53edf15ea7bfb836255be12b8ba1e0ce9f6f3): bump setuptools from 63.4.0 to 65.5.1 ([#1691](https://github.com/quay/quay/issues/1691))
- [42f46c93](https://github.com/quay/quay/commit/42f46c93c12453bd34ceff3de26c5cf23518d1da): bump express from 4.17.1 to 4.18.2 ([#1664](https://github.com/quay/quay/issues/1664))
- [6473166d](https://github.com/quay/quay/commit/6473166d0e9ab498977c99caa2ad8f9926dffcc5): bump decode-uri-component from 0.2.0 to 0.2.2 ([#1656](https://github.com/quay/quay/issues/1656))
- [d9352f0e](https://github.com/quay/quay/commit/d9352f0e9f80b1394b61dfe55e3218ac211b1f2f): bump protobuf from 3.15.0 to 3.18.3 ([#1541](https://github.com/quay/quay/issues/1541))
### Builders
- [7c72e313](https://github.com/quay/quay/commit/7c72e3132e49b82279fdc3dff47db9a1c5391acc): Update scope for gitlab to include write access (PROJQUAY-5181) ([#1785](https://github.com/quay/quay/issues/1785))
- [890e2ce9](https://github.com/quay/quay/commit/890e2ce9412af7f74616a29d0fd5b023ffd8f0c9): Add scopes to the oauth call to gitlab for build trigger (PROJQUAY-5181) ([#1784](https://github.com/quay/quay/issues/1784))
### Buildman
- [1a60cbe7](https://github.com/quay/quay/commit/1a60cbe7fbdd391f073035d94596bbad8f8c0842): add SLO metric that calculates build success (PROJQUAY-4486) ([#1609](https://github.com/quay/quay/issues/1609))
- [ea67af5a](https://github.com/quay/quay/commit/ea67af5a04753df2e06007394d58bbc0667acba4): add SLO metric for time spent in queue for build jobs (PROJQUAY-4487) ([#1575](https://github.com/quay/quay/issues/1575))
- [9a11e476](https://github.com/quay/quay/commit/9a11e4760e809a4cc4ac893382ec7d2654e26a87): allow fallback on non-exception build failures (PROJQUAY-4609) ([#1605](https://github.com/quay/quay/issues/1605))
### Chore
- [44db77ba](https://github.com/quay/quay/commit/44db77ba6c3acd1f3b1a946c01c73749c3f15914): Reformat python scripts in config-tool
- [9351d03a](https://github.com/quay/quay/commit/9351d03a63f6f3eb6e16e7324cb9420b69794fc6): Merge config-tool/.github into .github
- [bb4a9c9d](https://github.com/quay/quay/commit/bb4a9c9d184ff3563aeed6e390f7b949e6a7f4b2): Rename github.com/quay/config-tool to github.com/quay/quay/config-tool
- [09d5ab46](https://github.com/quay/quay/commit/09d5ab4664f0d74fcd9ebc11f745ea134fdd3ede): Use config-tool from this repo
- [3298995a](https://github.com/quay/quay/commit/3298995a79cde7dba03645c4593bd11699d6c0c7): Do not require ticket for build(deps-dev) ([#2081](https://github.com/quay/quay/issues/2081))
- [1c85c563](https://github.com/quay/quay/commit/1c85c563b9db80e2d2b1aee583492e7afe9ba590): use isinstance to check instance type ([#2070](https://github.com/quay/quay/issues/2070))
- [0429d796](https://github.com/quay/quay/commit/0429d79696c5a716cb05d5bbe82d68c9435445be): Move config-tool into its own directory
- [95a51576](https://github.com/quay/quay/commit/95a51576d52e4762de76eeb4db483c44ab6e13f0): Fix regexp in pull_request_linting.yaml ([#2054](https://github.com/quay/quay/issues/2054))
- [49efb78c](https://github.com/quay/quay/commit/49efb78ce39e5980fcbf106e6a2c81f7e89e0a4a): Use stable Cython ([#2025](https://github.com/quay/quay/issues/2025))
- [24b5fed0](https://github.com/quay/quay/commit/24b5fed01cddcf6fa5e00956e27653bcd8198ada): Use conventional-commit-checker-action for Jira check (PROJQUAY-5672) ([#2023](https://github.com/quay/quay/issues/2023))
- [97c5a722](https://github.com/quay/quay/commit/97c5a7226043ce3c4283f02580ea97bf8420651d): Bump PyYAML ([#2022](https://github.com/quay/quay/issues/2022))
- [e3c6e257](https://github.com/quay/quay/commit/e3c6e2573cfa8136039af531c79bcf5ae4524c86): Use latest go-toolset for config-tool ([#2020](https://github.com/quay/quay/issues/2020))
- [cc4bb0cc](https://github.com/quay/quay/commit/cc4bb0cc8eb59a19e4b326f3adcd8ea91c153d73): Use buildx v0.11.0-rc2 ([#1960](https://github.com/quay/quay/issues/1960)) ([#1971](https://github.com/quay/quay/issues/1971))
- [ef31a820](https://github.com/quay/quay/commit/ef31a82021e5a2d3ee64e1aa203636145d93c02e): v3.9.0 changelog bump (PROJQUAY-5065) ([#1944](https://github.com/quay/quay/issues/1944))
- [6a664d8c](https://github.com/quay/quay/commit/6a664d8cb0a569c78d922eef24e5e02ba6df38a3): update ppc64le builder ([#1904](https://github.com/quay/quay/issues/1904))
- [8e326f27](https://github.com/quay/quay/commit/8e326f278c02546ee17bfc9b677b232566d86087): Use external builders ([#1898](https://github.com/quay/quay/issues/1898))
- [42c9ebc4](https://github.com/quay/quay/commit/42c9ebc45cfe5b402c5c5ed831c399d570342fe6): Delete outdated k8 manifests (PROJQUAY-5490) ([#1880](https://github.com/quay/quay/issues/1880))
- [53e43942](https://github.com/quay/quay/commit/53e439427287029e221c625691346b1c0b12aaa0): Remove Docker Build jobs (PROJQUAY-5519) ([#1888](https://github.com/quay/quay/issues/1888))
- [d49dbd15](https://github.com/quay/quay/commit/d49dbd1515b3a17d21127b881461d333045552a5): Update db data for UI tests ([#1874](https://github.com/quay/quay/issues/1874))
- [80602e04](https://github.com/quay/quay/commit/80602e0421fc164ae358006a82ef5c6469479f04): Fix UI tests (PROJQUAY-5424) ([#1858](https://github.com/quay/quay/issues/1858))
- [8a235155](https://github.com/quay/quay/commit/8a235155ca9e111c3d811f2f808230a50720473d): Remove cachito magic for PyPDF2 ([#1838](https://github.com/quay/quay/issues/1838))
- [b4418062](https://github.com/quay/quay/commit/b4418062f93ddf45e1c1aad0a77b0b2193f1d2ef): Ensure use of HTTP 1.1 when proxying storage (PROJQUAY-5140) ([#1825](https://github.com/quay/quay/issues/1825))
- [fa50c70e](https://github.com/quay/quay/commit/fa50c70ed0cb86fa67141f6a34c772aa8bd154c0): Simplify base image (PROJQUAY-4837) ([#1709](https://github.com/quay/quay/issues/1709))
- [0ef6c67a](https://github.com/quay/quay/commit/0ef6c67a9e5d4f2cf69702eea09e4c5880811d8c): Fixes for local-dev-up-with-clair ([#1819](https://github.com/quay/quay/issues/1819))
- [58e0958c](https://github.com/quay/quay/commit/58e0958c67b7872c2fef676b5fc8eabc61a31fa1): Pin distribution-spec conformance tests ([#1809](https://github.com/quay/quay/issues/1809))
- [a8bf1c98](https://github.com/quay/quay/commit/a8bf1c98cfa5525e3e89aa1542240f24cfe756b0): Downgrade cryptography to 3.3.2 (PROJQUAY-5120) ([#1803](https://github.com/quay/quay/issues/1803))
- [e4df7102](https://github.com/quay/quay/commit/e4df710253889eacef0e2e985331c2c425e75d28): Add setuptools-rust as a build dependency ([#1788](https://github.com/quay/quay/issues/1788))
- [4d1989cc](https://github.com/quay/quay/commit/4d1989cc8d0d2fa6e7aeaed92b0cf8a868e48abe): Bump pyOpenSSL and cryptography (PROJQUAY-5120) ([#1777](https://github.com/quay/quay/issues/1777))
- [b7340739](https://github.com/quay/quay/commit/b7340739594da8ca7d2c522837ed2bf293bbecc3): Bump Authlib (PROJQUAY-5120) ([#1773](https://github.com/quay/quay/issues/1773))
- [8b14160c](https://github.com/quay/quay/commit/8b14160cea357018abb711c25b7c169bb9f8eabf): Bump config-tool to 1.15 (PROJQUAY-3643) ([#1763](https://github.com/quay/quay/issues/1763))
- [61913f86](https://github.com/quay/quay/commit/61913f86f83d54c1c7303c973db761f1c4a23791): bump config-tool version to latest (PROJQUAY-5048) ([#1754](https://github.com/quay/quay/issues/1754))
- [ab78f63d](https://github.com/quay/quay/commit/ab78f63d08594348427742a405be3b322ca714a9): Remove appr dependencies (PROJQUAY-4992) ([#1728](https://github.com/quay/quay/issues/1728))
- [9cc94feb](https://github.com/quay/quay/commit/9cc94feb5b37d634ea81e71dc8c60308982a7044): remove yapf (PROJQUAY-4865) ([#1693](https://github.com/quay/quay/issues/1693))
- [4efa48e3](https://github.com/quay/quay/commit/4efa48e3e074512b5938f38281b122b2e8c76a37): Use GitHub Actions cache for Docker Build jobs (PROJQUAY-4970) ([#1710](https://github.com/quay/quay/issues/1710))
- [ff498b39](https://github.com/quay/quay/commit/ff498b39812379c611f49621feae492dbb2f5297): v3.8.1 changelog bump (PROJQUAY-4716) ([#1721](https://github.com/quay/quay/issues/1721))
- [6e8e2d2f](https://github.com/quay/quay/commit/6e8e2d2fe71bb243f448f4b07e7e99d5865d0e15): remove deprecated appr code (PROJQUAY-4992) ([#1718](https://github.com/quay/quay/issues/1718))
- [6c454444](https://github.com/quay/quay/commit/6c45444496c104fa29165934ce8aac43840acfb3): Update Dockerfile to reduce size of image (PROJQUAY-4837) ([#1675](https://github.com/quay/quay/issues/1675)) ([#1681](https://github.com/quay/quay/issues/1681))
- [589fbb49](https://github.com/quay/quay/commit/589fbb49892c674637bf78f8004e1f4805de1822): Update Dockerfile to reduce size of image (PROJQUAY-4837) ([#1675](https://github.com/quay/quay/issues/1675))
- [cdb52ed0](https://github.com/quay/quay/commit/cdb52ed023c8222f2eeb95a1c71c403a06655ed8): Add server side assembly of chunked metadata for RADOSGW driver (PROJQUAY-4592) ([#1557](https://github.com/quay/quay/issues/1557))
### Chore: V3.7.10 Changelog Bump (Https
- [612a6537](https://github.com/quay/quay/commit/612a65379d261931786a5a8540b2373afcbb9561): //issues.redhat.com/browse/PROJQUAY-4627) ([#1591](https://github.com/quay/quay/issues/1591))
### Chore: V3.7.11 Changelog Bump (Https
- [a2aa6397](https://github.com/quay/quay/commit/a2aa6397af6a12ab10b8a985e75ab7c67d9f19fb): //issues.redhat.com/browse/PROJQUAY-4790) ([#1650](https://github.com/quay/quay/issues/1650))
### Chore: V3.7.9 Changelog Bump (Https
- [2ec6405a](https://github.com/quay/quay/commit/2ec6405a15f6d2b8f3a827ca511ae8195e38942e): //issues.redhat.com/browse/PROJQUAY-4478) ([#1568](https://github.com/quay/quay/issues/1568))
### Cleanup
- [304087f9](https://github.com/quay/quay/commit/304087f9c911071b083d87fce798b12d52f9ed0d): Remove old validation code (PROJQUAY-4606) ([#1562](https://github.com/quay/quay/issues/1562))
### Config
- [6eeb45b7](https://github.com/quay/quay/commit/6eeb45b7c003d582d43cba88f46ecca16d2fc1aa): Set feature flag default for new vulnerability notifications to True ([#1995](https://github.com/quay/quay/issues/1995))
- [9a7239e8](https://github.com/quay/quay/commit/9a7239e8746c2f0c7ec6af28105c777d9d6b5341): updating quota defaults (PROJQUAY-5546) ([#1901](https://github.com/quay/quay/issues/1901))
- [34a6e5fe](https://github.com/quay/quay/commit/34a6e5fea85e13bd00da5e4b8729d6adf6e59f70): clean upload folder by default (PROJQUAY-4395) ([#1731](https://github.com/quay/quay/issues/1731))
- [6bbfdf5e](https://github.com/quay/quay/commit/6bbfdf5e78e37eeafb3f422253785cf0ddc590a7): Remove whitespace from config (PROJQUAY-4666) ([#1596](https://github.com/quay/quay/issues/1596))
- [ff8043dd](https://github.com/quay/quay/commit/ff8043dd85732aa96ac7d90218a4ef416ef56cea): Add conftest mediatypes to default Quay configuration (PROJQUAY-4614) ([#1567](https://github.com/quay/quay/issues/1567))
### Config
- [4ebad4dc](https://github.com/quay/quay/commit/4ebad4dcd8b4d7562171e5c7f56ee133305cb932): Updating Cosign SBOM Media Types on Quay (PROJQUAY-4591) ([#1554](https://github.com/quay/quay/issues/1554))
### Cors
- [98d89a1f](https://github.com/quay/quay/commit/98d89a1fcef2c7ffdec3bfda5ea86f2e9c4261f6): check for request_origin being set (PROJQUAY-5213) ([#1811](https://github.com/quay/quay/issues/1811))
- [017c4f0b](https://github.com/quay/quay/commit/017c4f0ba1f28acdb22924f3f660f2dbbe4a98ff): Adding missing method type (PROJQUAY-4800) ([#1651](https://github.com/quay/quay/issues/1651))
### Deploy
- [d72b1bb3](https://github.com/quay/quay/commit/d72b1bb3dc8b0c01be567417dc004c414db8b74d): Allow for dynamic service names (PROJQUAY-5103) ([#1759](https://github.com/quay/quay/issues/1759))
- [aa78a8c8](https://github.com/quay/quay/commit/aa78a8c80faea723cb7503bfbeb0137b47477525): add value for empty annotation (PROJQUAY-3860) ([#1755](https://github.com/quay/quay/issues/1755))
- [a0ea7d7b](https://github.com/quay/quay/commit/a0ea7d7bf645f20315cbe521fe01f34f58b98086): add annotation for disabling DVO check (PROJQUAY-3680) ([#1753](https://github.com/quay/quay/issues/1753))
- [633cfaec](https://github.com/quay/quay/commit/633cfaec40b1be7ac1f335fef5691e0eef34146d): fix units in slo panel (PROJQUAY-4956) ([#1749](https://github.com/quay/quay/issues/1749))
- [b39876d5](https://github.com/quay/quay/commit/b39876d5e685e2121ca33f307436ad401275cc91): change push-pull panel (PROJQUAY-4956) ([#1735](https://github.com/quay/quay/issues/1735))
- [f3f608f2](https://github.com/quay/quay/commit/f3f608f22c82e0af2aa76ac50bb3fdbde7b9e00e): change slo dashboard (PROJQUAY-5026) ([#1732](https://github.com/quay/quay/issues/1732))
- [ea0f6f02](https://github.com/quay/quay/commit/ea0f6f02488c854512aa57f3e73d7a5b03b5ebed): update slo dashboard (PROJQUAY-4488) ([#1712](https://github.com/quay/quay/issues/1712))
- [b0b35184](https://github.com/quay/quay/commit/b0b35184f94dbe337aa6c54c94c1d07df2f3ef68): add weight to anti-affinity (PROJQUAY-3684) ([#1711](https://github.com/quay/quay/issues/1711))
- [45a40d4d](https://github.com/quay/quay/commit/45a40d4d6a6ee98f07605dc9cc71a238ba059768): add podAntiAffinity to deployment (PROJQUAY-3684) ([#1700](https://github.com/quay/quay/issues/1700))
- [a6177291](https://github.com/quay/quay/commit/a6177291c1ff2af207a6f18812a471133fe3bb16): add panel to dashboard (PROJQUAY-4486) ([#1698](https://github.com/quay/quay/issues/1698))
- [b69f3f36](https://github.com/quay/quay/commit/b69f3f36af0f3a7f80e57cd291b6b523576634ee): fix api panels in dashboard (PROJQUAY-4485) ([#1668](https://github.com/quay/quay/issues/1668))
- [cc5c3c79](https://github.com/quay/quay/commit/cc5c3c7996d9a498d890ea124fffb878551519ba): update grafana dashboard (PROJQUAY-4484) ([#1655](https://github.com/quay/quay/issues/1655))
- [ad4c13d7](https://github.com/quay/quay/commit/ad4c13d713f1022ba571e21580417b23ed86905f): Add deployment manifests for CloudFlare (PROJQUAY-3512) ([#1604](https://github.com/quay/quay/issues/1604))
### Feat
- [be1bddfd](https://github.com/quay/quay/commit/be1bddfd6a5bcedec411bb0140c6f153a4d044b3): Allow action logs to be forwarded to Splunk (PROJQUAY-4993) ([#1764](https://github.com/quay/quay/issues/1764))
### Fix
- [80cd9c33](https://github.com/quay/quay/commit/80cd9c332492bf29fd8139c8abfeef4c4ff9b6f5): Pass CONTAINER_RUNTIME to quay-builder (PROJQUAY-5910) ([#2105](https://github.com/quay/quay/issues/2105))
### Geo-Rep
- [0e08328b](https://github.com/quay/quay/commit/0e08328b1d4ca9a7361aade8a1e190f99cbc4223): Initialize features from config in util script (PROJQUAY-5627) ([#1967](https://github.com/quay/quay/issues/1967))
- [95819675](https://github.com/quay/quay/commit/958196757f63b70391562b09e922959a04c35c84): Add util script to remove geo-rep location and corresponding image locations (PROJQUAY-4995) ([#1943](https://github.com/quay/quay/issues/1943))
### Georep
- [b5b7aabe](https://github.com/quay/quay/commit/b5b7aabefa4b261e40b840fe7836b5c08bad544e): Add error handling for remove location script (PROJQUAY-5878) ([#2094](https://github.com/quay/quay/issues/2094))
### Healthcheck
- [2dd0d3e2](https://github.com/quay/quay/commit/2dd0d3e248d5dc23097f65a283661ef5972edd05): fix invalid Exception attribute (PROJQUAY-5047) ([#1782](https://github.com/quay/quay/issues/1782))
### Ldap
- [b2a5b3ab](https://github.com/quay/quay/commit/b2a5b3abb73fd7846a3d8061a02b71c76133ce50): Don't convert dashes to underscores in usernames (PROJQUAY-5253) ([#1808](https://github.com/quay/quay/issues/1808))
### Locking
- [780bca5e](https://github.com/quay/quay/commit/780bca5eeb4b72ba1517134874fc853d7045f381): change log severity (PROJQUAY-5221) ([#1820](https://github.com/quay/quay/issues/1820))
### Login
- [c5ea9fa1](https://github.com/quay/quay/commit/c5ea9fa16924b865822f902811e3d10d74743047): Use dedicated mailing list for export compliance email (PROJQUAY-4844) ([#1730](https://github.com/quay/quay/issues/1730))
- [68844dbf](https://github.com/quay/quay/commit/68844dbf5e6fbfe814b0c917a3026efc3f982639): Re-raise the export compliance exception on RHSSO (prod) (PROJQUAY-4844) ([#1726](https://github.com/quay/quay/issues/1726))
- [f2b70c50](https://github.com/quay/quay/commit/f2b70c50316c8c6fe24496e1060b8327006aed9f): Re-raise the export compliance exception on RHSSO (PROJQUAY-4844) ([#1725](https://github.com/quay/quay/issues/1725))
- [cb590f9a](https://github.com/quay/quay/commit/cb590f9a636ccc09daf8a62479c646a2c1246c9d): Add error message for exprot compliance hold (PROJQUAY-4844) ([#1715](https://github.com/quay/quay/issues/1715))
- [442bb168](https://github.com/quay/quay/commit/442bb1689dc42b919b6472e65a31ef8346c9cf1c): Use the correct username for export compliance (PROJQUAY-4844) ([#1696](https://github.com/quay/quay/issues/1696))
- [5bd24264](https://github.com/quay/quay/commit/5bd2426400d46f350b97755974cdc2e9dfc4588b): Add subject in debug logs for export compliance (PROJQUAY-4844) ([#1695](https://github.com/quay/quay/issues/1695))
### Logs
- [0c2f4c92](https://github.com/quay/quay/commit/0c2f4c9224e7d72fcf978c0f51bfaa44a9359319): Add autologin to splunk's connect() to allow retries (PROJQUAY-5621) ([#1957](https://github.com/quay/quay/issues/1957))
- [171f9cc1](https://github.com/quay/quay/commit/171f9cc14c182bd4d928964cbcea1504b2cc9449): ssl_ca_path should be optional (PROJQUAY-4993) ([#1920](https://github.com/quay/quay/issues/1920))
- [490a6b2c](https://github.com/quay/quay/commit/490a6b2ce8d4fd24147f39a04ca8339a94772cce): Add SSL cert support and test coverage for splunk logging (PROJQUAY-4993) ([#1878](https://github.com/quay/quay/issues/1878))
- [41cd8330](https://github.com/quay/quay/commit/41cd8330d0e7be8941776dc4e06957017f5fa605): add audit log events for login/logout to Quay (PROJQUAY-2344) ([#1866](https://github.com/quay/quay/issues/1866))
- [37e4990b](https://github.com/quay/quay/commit/37e4990b075ab7268d2707e032f4022093b1e76d): Add audit logs for organization and user namespace activities (PROJQUAY-3482) ([#1846](https://github.com/quay/quay/issues/1846))
- [ed86a102](https://github.com/quay/quay/commit/ed86a102ce0c619033714e0afe30a71a331465f4): validate date range is within configuration (PROJQUAY-4959) ([#1707](https://github.com/quay/quay/issues/1707))
- [1bd016fd](https://github.com/quay/quay/commit/1bd016fda56c1a7bd0940e6a204476c5777198b7): Add repository information for build audit logs (PROJQUAY-4726) ([#1705](https://github.com/quay/quay/issues/1705))
- [33451ca9](https://github.com/quay/quay/commit/33451ca96e3996a7107d8645dcdec178cda420cc): audit logs on manual build triggers and build cancellations (PROJQUAY-4726) ([#1682](https://github.com/quay/quay/issues/1682))
- [fe2b89d6](https://github.com/quay/quay/commit/fe2b89d6563df35dbe8c6cb891d7cd9f5d90df8d): create action logs on proxy cache config creation/deletion (PROJQUAY-4718) ([#1625](https://github.com/quay/quay/issues/1625))
### Marketplace
- [de8c48fa](https://github.com/quay/quay/commit/de8c48fa28130f425acc962b739b7ced9a667009): fixing allowed repo count (PROJQUAY-5513) ([#1891](https://github.com/quay/quay/issues/1891))
- [c3539469](https://github.com/quay/quay/commit/c3539469105386150fad2e2163e8afefb3fd26d3): fix path to api cert (PROJQUAY-5409) ([#1870](https://github.com/quay/quay/issues/1870))
- [0a1c7fb2](https://github.com/quay/quay/commit/0a1c7fb22e0ff1261bb49f1c4dc12125d78c2f6d): add reconciler (PROJQUAY-5320) ([#1817](https://github.com/quay/quay/issues/1817))
### Nginx
- [056b6fca](https://github.com/quay/quay/commit/056b6fca306dc7cbc2a16bc55e92703e195dba43): Minor update to fix toggling issue on Safari (PROJQUAY-4527) ([#1670](https://github.com/quay/quay/issues/1670))
### Oci/Index.Py
- [e262f062](https://github.com/quay/quay/commit/e262f062b7155a0d35a442ddfc2b3340f0f0bbe5): support docker schema2 sub-manifest types ([#1649](https://github.com/quay/quay/issues/1649))
### Permissions
- [16e53211](https://github.com/quay/quay/commit/16e53211082e007f7704abe7f8f0df9d8f8a8b2b): lazy-load superuser permissions (PROJQUAY-5117) ([#1761](https://github.com/quay/quay/issues/1761))
### Pg
- [133437f2](https://github.com/quay/quay/commit/133437f23146f707058c902dad3150218e4850e6): Add warning log when Postgres version less than 13 ([#218](https://github.com/quay/quay/issues/218))
### Proxy
- [ba29a40b](https://github.com/quay/quay/commit/ba29a40b80f637aecabb264062488b63c5157bc4): allowing expiring tags with timemachine set to 0 (PROJQUAY-5558) ([#1907](https://github.com/quay/quay/issues/1907))
- [e349762d](https://github.com/quay/quay/commit/e349762d780c67803e8e2e740178fda7db0b6656): Allow anonymous pulls from registries (PROJQUAY-5273) ([#1906](https://github.com/quay/quay/issues/1906))
### Quay
- [dcf5a377](https://github.com/quay/quay/commit/dcf5a377a93c2d16bd2400747106adfd88a25982): Cloudfront multi domain (PROJQUAY-4506) ([#1598](https://github.com/quay/quay/issues/1598))
### Quay UI
- [3a90e1b4](https://github.com/quay/quay/commit/3a90e1b433111224b151932c3403af08e3b1bbad): Creating new username for accounts that login via SSO (PROJQUAY-5289) ([#1831](https://github.com/quay/quay/issues/1831))
### Quota
- [6cf0a353](https://github.com/quay/quay/commit/6cf0a3531b7e5538266d11b12a158b8b11d12f67): calculating registry size (PROJQUAY-5476) ([#1879](https://github.com/quay/quay/issues/1879))
- [cf509011](https://github.com/quay/quay/commit/cf50901159c5d232bc61c6c3ff142668a9d92651): moving resetting of child manifest temporary tags to delete endpoint (PROJQUAY-5512) ([#1894](https://github.com/quay/quay/issues/1894))
- [e6f2dc33](https://github.com/quay/quay/commit/e6f2dc3354de47d4f3542e77c1b91be6a144dc7b): excluding robots from quota total (PROJQUAY-5469) ([#1871](https://github.com/quay/quay/issues/1871))
- [a2c379d4](https://github.com/quay/quay/commit/a2c379d47c905e5e6649d3a68bd39459e559df58): Include blob deduplication in totals (PROJQUAY-3942) ([#1751](https://github.com/quay/quay/issues/1751))
### Registry
- [23b39720](https://github.com/quay/quay/commit/23b39720d1062fa917926e0f52c14fc886101605): add option to ignore unknown mediatypes (PROJQUAY-5018) ([#1750](https://github.com/quay/quay/issues/1750))
### Repomirror
- [ff66a93e](https://github.com/quay/quay/commit/ff66a93eb7c1b466b2dffd5e62187d7824e6ccad): Add default value for `REPO_MIRROR_ROLLBACK`to config (PROJQUAY-4296) ([#1786](https://github.com/quay/quay/issues/1786))
- [15ea8350](https://github.com/quay/quay/commit/15ea8350db3dd3321801b9b7b8fed8ba252a5b30): Use skopeo list-tags to get repo tags (PROJQUAY-2179) ([#1427](https://github.com/quay/quay/issues/1427))
### Revert "Chore
- [fe4f7593](https://github.com/quay/quay/commit/fe4f7593eafe890dff68fc2628485b487c4cb645): Use stable Cython ([#2025](https://github.com/quay/quay/issues/2025))" ([#2042](https://github.com/quay/quay/issues/2042))
- [209299fc](https://github.com/quay/quay/commit/209299fc80897f7a7d4b1bf15e047064d40021f9): Bump PyYAML ([#2022](https://github.com/quay/quay/issues/2022))" ([#2041](https://github.com/quay/quay/issues/2041))
- [04358d26](https://github.com/quay/quay/commit/04358d26af974da57b627ab186137a091668fff7): Update Dockerfile to reduce size of image (PROJQUAY-4837) ([#1675](https://github.com/quay/quay/issues/1675))" ([#1678](https://github.com/quay/quay/issues/1678))
- [e4e00f70](https://github.com/quay/quay/commit/e4e00f706a065eeb5fd889a0c2273efa07cd7fb5): Add server side assembly of chunked metadata for RADOSGW driver (PROJQUAY-4592) ([#1557](https://github.com/quay/quay/issues/1557))" ([#1642](https://github.com/quay/quay/issues/1642))
### Revert "Secscan
- [5e4ae649](https://github.com/quay/quay/commit/5e4ae6495a41fd770ea3a986a66d5100e3ab2e75): add metric for scan results (PROJQUAY-4488) ([#1674](https://github.com/quay/quay/issues/1674))" ([#1714](https://github.com/quay/quay/issues/1714))
### Scripts
- [facb4b1e](https://github.com/quay/quay/commit/facb4b1e5b45eafb25e7f3ae0cbdf90e21a38550): push to ecr backup when building quay.io (PROJQUAY-3273) ([#1578](https://github.com/quay/quay/issues/1578))
### Secscan
- [c3fc3a82](https://github.com/quay/quay/commit/c3fc3a82ab3280d6df51fcbb955f197a55e39ebe): send notifications for new indexes (PROJQUAY-4659) ([#1813](https://github.com/quay/quay/issues/1813))
- [4aa84a52](https://github.com/quay/quay/commit/4aa84a528c7ad47993c0e8ee123053a48a388644): fix string to int conversion (PROJQUAY-4395) ([#1736](https://github.com/quay/quay/issues/1736))
- [e1985942](https://github.com/quay/quay/commit/e1985942a6eab3b553c35364bcbe365dd4538d72): handle non backfilled layers_compressed_size (PROJQUAY-4395) ([#1734](https://github.com/quay/quay/issues/1734))
- [d84b67c7](https://github.com/quay/quay/commit/d84b67c73ca6d86d0301d90943f79f683c8dad2e): add scan metric (PROJQUAY-4488) ([#1719](https://github.com/quay/quay/issues/1719))
- [80fdb924](https://github.com/quay/quay/commit/80fdb92462ee31a1b56785a7e495c254da16a764): add config to limit manifests with layer size too large to index (PROJQUAY-4957) ([#1733](https://github.com/quay/quay/issues/1733))
- [709487b3](https://github.com/quay/quay/commit/709487b36306fb7721b5cfde0a7648dc83a6bb83): add timeout to indexing requests ([#1727](https://github.com/quay/quay/issues/1727))
- [8f9d6c94](https://github.com/quay/quay/commit/8f9d6c9447b3e8dc8d0b94dad4417b5bbeb41ff4): add metric for scan results (PROJQUAY-4488) ([#1674](https://github.com/quay/quay/issues/1674))
- [84786b9c](https://github.com/quay/quay/commit/84786b9c6fcf851c2beeb04e1c61683ec22dd46f): Correct links (PROJQUAY-2164) ([#1552](https://github.com/quay/quay/issues/1552))
- [98801bfd](https://github.com/quay/quay/commit/98801bfd3e8cb0b81f83cbbcac0346302eef7b8c): Generate key to reduce vulnerabilities (PROJQUAY-4562) ([#1547](https://github.com/quay/quay/issues/1547))
### Secscan_model
- [37578247](https://github.com/quay/quay/commit/37578247088bc86e80f33f106d8aac5177b488f0): attempt urldecoding `fixed_in_version` (PROJQUAY-5886) ([#2063](https://github.com/quay/quay/issues/2063))
### Security
- [95a59325](https://github.com/quay/quay/commit/95a5932528cde8937a21cf88fe45a5664c44489f): Change error messages in UI during LDAP login (PROJQUAY-4845) ([#1767](https://github.com/quay/quay/issues/1767))
### Storage
- [63888379](https://github.com/quay/quay/commit/63888379812908c52c22d951b794af04545835b2): add option to validate all configured storages (PROJQUAY-5074) ([#1752](https://github.com/quay/quay/issues/1752))
- [0ae31c6e](https://github.com/quay/quay/commit/0ae31c6ebcbc1441a18e33eb2e3c8be1c1e90d81): Add MultiCDN storage provider (PROJQUAY-5048) ([#1747](https://github.com/quay/quay/issues/1747))
- [f4d9dda2](https://github.com/quay/quay/commit/f4d9dda27d59df582b73d0a57122cae335123799): Add **kwargs to get_direct_download_url for CloudFlare storage (PROJQUAY-3512) ([#1594](https://github.com/quay/quay/issues/1594))
- [40735569](https://github.com/quay/quay/commit/407355691ba593ca9a26ffd9be48cd4826c89669): Add Cloudflare as a CDN provider for an S3 backed storage (PROJQUAY-3699) ([#1294](https://github.com/quay/quay/issues/1294))
### Storagereplication
- [c0efc752](https://github.com/quay/quay/commit/c0efc75207a50cf6d168fe16bc887ff43c834d8b): add retry logic without exhausting queue retries (PROJQUAY-4793) ([#1832](https://github.com/quay/quay/issues/1832))
- [2e5f2572](https://github.com/quay/quay/commit/2e5f25726aae04c6527a2c8a5399d3e6ab03cf7a): sleep on unexpected exception for retry (PROJQUAY-4792) ([#1792](https://github.com/quay/quay/issues/1792))
### Superuser
- [9adf2d8c](https://github.com/quay/quay/commit/9adf2d8cf05303668362d176ac655e9969408116): paginate user's list (PROJQUAY-4297) ([#1881](https://github.com/quay/quay/issues/1881))
- [c505a6ba](https://github.com/quay/quay/commit/c505a6bae8c93c4bead3acffc189c4d5e5bfef96): paginating superuser organization list (PROJQUAY-4297) ([#1876](https://github.com/quay/quay/issues/1876))
### Superusers
- [45d00a6b](https://github.com/quay/quay/commit/45d00a6b8ff9989e893c656a3e71ad7cf09d144f): gives superusers access to team invite api (PROJQUAY-4765) ([#1694](https://github.com/quay/quay/issues/1694))
- [64ec1560](https://github.com/quay/quay/commit/64ec15605c6dd8d3e1d66442c97a4511c6d22d04): grant superusers additinonal org permissions (PROJQUAY-4687) ([#1613](https://github.com/quay/quay/issues/1613))
### Tox
- [5f43b3f8](https://github.com/quay/quay/commit/5f43b3f81e1e6047ebab21357ed2facf6980fa5b): allow /bin/sh (PROJQUAY-5092) ([#1757](https://github.com/quay/quay/issues/1757))
### UI
- [5198db57](https://github.com/quay/quay/commit/5198db57445487a32adcaa066d4acb2ae422de9b): Robot Accounts page perms fix (PROJQUAY-5487) ([#2088](https://github.com/quay/quay/issues/2088))
- [8c21856b](https://github.com/quay/quay/commit/8c21856b716c9a4279fdf32d3d0ba5290c9479a2): Delete normal user org by super user (PROJQUAY-5639) ([#2008](https://github.com/quay/quay/issues/2008))
- [98a0f8bb](https://github.com/quay/quay/commit/98a0f8bb4d7a79be95310544c37647baaf0b0ac2): Fixing failing tests ([#1890](https://github.com/quay/quay/issues/1890))
- [c014b6af](https://github.com/quay/quay/commit/c014b6af03d98a29538ef2f0dd534f2e8a3d4c23): Adding functionality to update organization settings (PROJQUAY-5402) ([#1864](https://github.com/quay/quay/issues/1864))
- [7be6c3d2](https://github.com/quay/quay/commit/7be6c3d22780f4b6811bb3853a271753e2a7021c): Fix visibility of organization and user settings on new UI (PROJQUAY-5500) ([#1882](https://github.com/quay/quay/issues/1882))
- [e6d834f2](https://github.com/quay/quay/commit/e6d834f23d562f7e00f2e63c2d91590870a7a410): Fixing repository name for nested repos (PROJQUAY-5446) ([#1873](https://github.com/quay/quay/issues/1873))
- [37723b96](https://github.com/quay/quay/commit/37723b964cca099b334962df90b4115bc1ae026b): Removing Cancel button from Robot account credentials modal (PROJQUAY-5426) ([#1867](https://github.com/quay/quay/issues/1867))
- [c6f35b3d](https://github.com/quay/quay/commit/c6f35b3d25cf99f2517cf478e4cc9e5ee55119d9): Removing isHidden from Tab as incompatible with console dot (PROJQUAY-4553) ([#1863](https://github.com/quay/quay/issues/1863))
- [dcd192d5](https://github.com/quay/quay/commit/dcd192d5249e77ccb99c09c86a3a0475172e2bc1): Using organizationName variable and using isHidden to hide tabs (PROJQUAY-4553) ([#1862](https://github.com/quay/quay/issues/1862))
- [d20fd5e7](https://github.com/quay/quay/commit/d20fd5e7468912d6b741aa4594549e1f335e75b6): Robot token fetch & regenerate fix for user namespace (PROJQUAY-5419) ([#1860](https://github.com/quay/quay/issues/1860))
- [22d28f9f](https://github.com/quay/quay/commit/22d28f9fcdea157d503c36bcac307535f92a3973): Filtering security report vulnerabilities (PROJQUAY-5401) ([#1861](https://github.com/quay/quay/issues/1861))
- [1634f817](https://github.com/quay/quay/commit/1634f8176b6fe3e7115eaef280aad11817d530e8): Fixing Teams search in Create Robot Wizard (PROJQUAY-5403) ([#1859](https://github.com/quay/quay/issues/1859))
- [b95a4f6a](https://github.com/quay/quay/commit/b95a4f6aaae9fc9c7ad9ac68dfe4779de13a01f2): Replacing FilterInput with SearchInput in repo search for create robot account wizard (PROJQUAY-5403) ([#1851](https://github.com/quay/quay/issues/1851))
- [155165d6](https://github.com/quay/quay/commit/155165d6dae4332fd653611dcef22985ffb5e3ef): Replacing FilterInput with SearchInput in Robot accounts page (PROJQUAY-5404) ([#1849](https://github.com/quay/quay/issues/1849))
- [2616bf9b](https://github.com/quay/quay/commit/2616bf9b9a2ca4075c471c72372f97c4b27c548d): Replacing useRecoil with useState for robot account search (PROJQUAY-5404) ([#1848](https://github.com/quay/quay/issues/1848))
- [d9b9f60c](https://github.com/quay/quay/commit/d9b9f60c59e741bca7316bf3228c88375d5d553f): Check if org is user for robot creation (PROJQUAY-5398) ([#1847](https://github.com/quay/quay/issues/1847))
- [71cfdca0](https://github.com/quay/quay/commit/71cfdca0879cacbf9affe036b1724776ddf0b406): Fixing repoDetails not defined error ([#1837](https://github.com/quay/quay/issues/1837))
- [60181dae](https://github.com/quay/quay/commit/60181dae0313ca4023bfe7e4076acf551a3b1ca4): Fix redirection to user/org page (PROJQUAY-4667) ([#1623](https://github.com/quay/quay/issues/1623))
### Ui
- [74d6d827](https://github.com/quay/quay/commit/74d6d82748df7fc9b5dcb5f1e712fd3be1b7b38f): updating quota size format (PROJQUAY-5471) ([#1886](https://github.com/quay/quay/issues/1886))
- [a681a0b7](https://github.com/quay/quay/commit/a681a0b71da9c1147caa146af8b94d48e63fb909): Fix search in bulk delete of robot accounts (PROJQUAY-5355) ([#1868](https://github.com/quay/quay/issues/1868))
- [0029b8b4](https://github.com/quay/quay/commit/0029b8b4ae2c44c01ca58b6df2022262dba1cedf): update survey link to new survey (PROJQUAY-5432) ([#1865](https://github.com/quay/quay/issues/1865))
- [93de6539](https://github.com/quay/quay/commit/93de653973c8463eabe8dbeb8ca463a6801dfbbd): Hide organization settings when user is not admin (PROJQUAY-4053) ([#1829](https://github.com/quay/quay/issues/1829))
- [be1424ca](https://github.com/quay/quay/commit/be1424ca3a1150ec10b5940ffc369ac9abdf10db): Adding option to permanently delete tags past time machine window (PROJQUAY-5303) ([#1853](https://github.com/quay/quay/issues/1853))
- [64e4e327](https://github.com/quay/quay/commit/64e4e32704181b398129f318b555b1dd0840e6b9): fix last modified date on repo list (PROJQUAY-5408) ([#1854](https://github.com/quay/quay/issues/1854))
- [f22da92e](https://github.com/quay/quay/commit/f22da92e6b773125f0dbfd5b08bdb9f13886ede9): use route location instead of window.location (PROJQUAY-5392) ([#1844](https://github.com/quay/quay/issues/1844))
- [19259c1c](https://github.com/quay/quay/commit/19259c1cb0cf9ca0ceb0397b842f4d37089b3266): Refresh auth token for plugin flow on 401 (PROJQUAY-5390) ([#1843](https://github.com/quay/quay/issues/1843))
- [717db76c](https://github.com/quay/quay/commit/717db76ca20907f74e4eac04c8692c55960f6102): Use the correct endpoint for plugin (PROJQUAY-3203) ([#1842](https://github.com/quay/quay/issues/1842))
- [2db3b186](https://github.com/quay/quay/commit/2db3b186f9e2bb60251d15fd5b3b7cba90851045): add support for exposing quay UI as a dynamic plugin (PROJQUAY-3203) ([#1799](https://github.com/quay/quay/issues/1799))
- [0e3221e4](https://github.com/quay/quay/commit/0e3221e4f3c7d9d3c5d86d25ac072b89f52faa3d): Merge quay-ui into quay (PROJQUAY-5315) ([#1827](https://github.com/quay/quay/issues/1827))
- [85218f11](https://github.com/quay/quay/commit/85218f1112677a0af59810859950353465e72456): Hot fix billing information (PROJQUAY-0000) ([#1679](https://github.com/quay/quay/issues/1679))
- [b8cf8932](https://github.com/quay/quay/commit/b8cf8932cf34c738160a290a9b337018d9daf26b): Repository settings feature flag (PROJQUAY-4565) ([#1677](https://github.com/quay/quay/issues/1677))
- [1a2bb4a4](https://github.com/quay/quay/commit/1a2bb4a4e918c032bb16a61c4045fcabef886494): Remove add_analytics script from Dockerfile (PROJQUAY-4582) ([#1669](https://github.com/quay/quay/issues/1669))
- [74d8a515](https://github.com/quay/quay/commit/74d8a515f882db7b5a5ac59c8f4e0399a60f4e34): Remove FEATURE_UI_V2 from analytics scripts (PROJQUAY-4582) ([#1658](https://github.com/quay/quay/issues/1658))
- [c71fd10b](https://github.com/quay/quay/commit/c71fd10bc2e3a96a41d518fa2e9b8d1b38e8d882): Add script for adobe analytics for quay.io in angular UI (PROJQUAY-4582) ([#1654](https://github.com/quay/quay/issues/1654))
- [8211b774](https://github.com/quay/quay/commit/8211b774bc8cebd36d923b3710ad7b70711a889f): Show UI toggle on quay.io only to redhat users (PROJQUAY-4804) ([#1653](https://github.com/quay/quay/issues/1653))
- [bc5bc22b](https://github.com/quay/quay/commit/bc5bc22b1d8bbdeaa841d956661dd4d58073911d): Add script for adobe analytics for quay.io (PROJQUAY-4582) ([#1648](https://github.com/quay/quay/issues/1648))
- [96372019](https://github.com/quay/quay/commit/963720190386460b073782c090319894b3b3936b): Fix font size in superuser page (PROJQUAY-4407) ([#1553](https://github.com/quay/quay/issues/1553))
### Users
- [dba302b5](https://github.com/quay/quay/commit/dba302b5f162b7800f676cf4789cc4e40898f240): default to true if LDAP_RESTRICTED_USER_FILTER is not set (PROJQUAY-4776) ([#1645](https://github.com/quay/quay/issues/1645))
- [b128936b](https://github.com/quay/quay/commit/b128936b504dbe0f2083d1784d884cb877db9c97): fix behavior when using ldap and restricted user whitelist is set (PROJQUAY-4767) ([#1640](https://github.com/quay/quay/issues/1640))
- [7cd55ea0](https://github.com/quay/quay/commit/7cd55ea0cd4a3fc7a995a26be51e8709bc1785be): fix create repo on push on orgs for restricted users (PROJQUAY-4732) ([#1634](https://github.com/quay/quay/issues/1634))
- [0caa4203](https://github.com/quay/quay/commit/0caa4203eccc21895a5e84322e68db18d5ad959f): prevent CREATE_NAMESPACE_ON_PUSH is restricted (PROJQUAY-4702) ([#1621](https://github.com/quay/quay/issues/1621))
- [8fc03857](https://github.com/quay/quay/commit/8fc03857cbd3cde85217138389fc08dbecfc2b53): when set, grant superusers repository permissions. ([#1620](https://github.com/quay/quay/issues/1620))
- [ef8ad2c3](https://github.com/quay/quay/commit/ef8ad2c3e1efec3719ed6ceb249acf9b7b617fd9): prevent creating repo on push for restricted users (PROJQUAY-4706) ([#1614](https://github.com/quay/quay/issues/1614))
- [c84067a4](https://github.com/quay/quay/commit/c84067a4d6a1a4442c13f841aab9cd448857db37): add restricted users' filter (PROJQUAY-1245) ([#1551](https://github.com/quay/quay/issues/1551))
### Util
- [230fd24f](https://github.com/quay/quay/commit/230fd24f3d3bb6b899442dfc6be1ffde8e30bc2c): Reading new UI feedback form url from config parameter (PROJQUAY-5463) ([#1902](https://github.com/quay/quay/issues/1902))
- [3035f46f](https://github.com/quay/quay/commit/3035f46f569bc46cd59ec1c7b63fe2cba35d0e04): Clean up and adding make target to install pre-commit hooks(PROJQUAY-000) ([#1587](https://github.com/quay/quay/issues/1587))
- [e8e5d5d9](https://github.com/quay/quay/commit/e8e5d5d90461cca38a4367be603ecdbb2fce956c): Adding git pre-commit checks (PROJQUAY-4658) ([#1585](https://github.com/quay/quay/issues/1585))
### [Redhat-3.9] Api
- [1239477f](https://github.com/quay/quay/commit/1239477f546e2be0ccebbc10712701d2d207dd4f): Adding ignore timezone flag when parsing datetime (PROJQUAY-5360) ([#2079](https://github.com/quay/quay/issues/2079))
- [2afab1c6](https://github.com/quay/quay/commit/2afab1c67473cfa7cfa16878705b55c905b20625): add permanently delete tag usage log (PROJQUAY-5496) ([#1926](https://github.com/quay/quay/issues/1926))
### [Redhat-3.9] Authentication(LDAP)
- [6be4d052](https://github.com/quay/quay/commit/6be4d052ff8a841d35dbfd69fe7bfdf674302ace): allow LDAP referrals to not be followed (PROJQUAY-5291)  ([#1922](https://github.com/quay/quay/issues/1922))
### [Redhat-3.9] Build(Deps)
- [648f9571](https://github.com/quay/quay/commit/648f9571e3a241be638929c66b2012f78a2ee201): bump golang.org/x/net (PROJQUAY-5339) ([#2093](https://github.com/quay/quay/issues/2093))
### [Redhat-3.9] Oci
- [0f8fd65d](https://github.com/quay/quay/commit/0f8fd65d2ccd0c1a4248aab20a25bbdb5c92367a): Allow optional components in the image config to be set to "null" (PROJQUAY-5634) ([#1964](https://github.com/quay/quay/issues/1964))
### [Redhat-3.9] Pagination
- [81dc7966](https://github.com/quay/quay/commit/81dc79668c5223deb9edeaf5710cc9ef30bd5b78): Fixing paginate for /api/v1/superuser/logs API (PROJQUAY-5360) ([#2011](https://github.com/quay/quay/issues/2011))
### [Redhat-3.9] Storage
- [313a9544](https://github.com/quay/quay/commit/313a95444b010159ddef3ce7446279852b177441): make cloudfront_distribution_org_overrides optional (PROJQUAY-5788) ([#2009](https://github.com/quay/quay/issues/2009))
### [Redhat-3.9] UI
- [b1bab0b9](https://github.com/quay/quay/commit/b1bab0b93dc734d5fd7b537030289540c7ed9bf3): Replace time to wait with event waits in cypress tests ([#2078](https://github.com/quay/quay/issues/2078))
### [Redhat-3.9] Ui
- [fcdb292a](https://github.com/quay/quay/commit/fcdb292a47653c97291f703da3c24ad756c5628e): display sizes as base 2  (PROJQUAY-5524) ([#1970](https://github.com/quay/quay/issues/1970))
### Pull Requests
- Merge pull request [#2069](https://github.com/quay/quay/issues/2069) from dmage/merge-config-tool-3.9


<a name="v3.8.15"></a>
## [v3.8.15] - 2024-01-24
### Reconfigure
- [2d351213](https://github.com/quay/quay/commit/2d35121397f1b369fc2dde79f7631f79527cbfaa): Add auth to comit to operator endpoint (PROJQUAY-6598) ([#2631](https://github.com/quay/quay/issues/2631))

<a name="v3.8.14"></a>
## [v3.8.14] - 2023-11-02
### [Redhat-3.8] Build(Deps)
- [d4df6b53](https://github.com/quay/quay/commit/d4df6b532238371107f2a05e34adb6c39e078cb2): bump golang.org/x/net from 0.13.0 to 0.17.0 (PROJQUAY-6208) ([#2447](https://github.com/quay/quay/issues/2447))

<a name="v3.8.13"></a>
## [v3.8.13] - 2023-10-10

<a name="v3.8.12"></a>
## [v3.8.12] - 2023-09-06
### Build(Deps)
- [8340f707](https://github.com/quay/quay/commit/8340f707143c3f59df83a49560668ff08df88df9): bump pypdf2 from 1.27.6 to 1.27.9 ([#2055](https://github.com/quay/quay/issues/2055))
### Chore
- [1302e11a](https://github.com/quay/quay/commit/1302e11ab32d88280cb05e473b0871db42a32f70): fix build of PyYAML on linux/ppc64le ([#2113](https://github.com/quay/quay/issues/2113))
### [Redhat-3.8] Chore
- [44fce9e9](https://github.com/quay/quay/commit/44fce9e9a0b2310504b19385a0cd93fb497f1433): pull changes for s390x from master ([#2112](https://github.com/quay/quay/issues/2112))

<a name="v3.8.11"></a>
## [v3.8.11] - 2023-08-07
### Azure
- [63ed3d95](https://github.com/quay/quay/commit/63ed3d95399a32d511001b71042b74b469b6cf63): Remove parsing of error response (PROJQUAY-3718) ([#167](https://github.com/quay/quay/issues/167))
### Build(Deps)
- [3791ff6a](https://github.com/quay/quay/commit/3791ff6a559389eec5c26584c4a82e44a10029af): bump decode-uri-component in /pkg/lib/editor ([#192](https://github.com/quay/quay/issues/192))
- [3b1c7dba](https://github.com/quay/quay/commit/3b1c7dba22de00226fc07801625ff0f718fa1a59): bump socket.io-parser in /pkg/lib/editor ([#213](https://github.com/quay/quay/issues/213))
- [7c252e50](https://github.com/quay/quay/commit/7c252e50c34d2865461771932712f886199c3f69): bump minimist and karma in /pkg/lib/editor ([#210](https://github.com/quay/quay/issues/210))
### Builders
- [72307569](https://github.com/quay/quay/commit/72307569e76cf89bcef4d5d3b154e1311981754d): Log errors for Github and Bitbucket trigger validation (PROJQUAY-3125) ([#144](https://github.com/quay/quay/issues/144))
### Certs
- [0cb8bde0](https://github.com/quay/quay/commit/0cb8bde0f8b63f807d18f0a9f584d476cac73f12): Load certs with both extra_ca_cert_ and extra_ca_certs/ prefix (PROJQUAY-3593)
### Chore
- [e43ee92a](https://github.com/quay/quay/commit/e43ee92aa09b8f1988e3da9964d65e00e1332493): Use latest go-toolset for config-tool
- [0befa36a](https://github.com/quay/quay/commit/0befa36a0486b2d6320179bbadfd8aed43919640): Reformat python scripts in config-tool
- [78f27f81](https://github.com/quay/quay/commit/78f27f816b196a972edd1d1dc5502db38e3290e8): Merge config-tool/.github into .github
- [a785405e](https://github.com/quay/quay/commit/a785405e8959adfdf0893f7b7cd180f58eb0b849): Rename github.com/quay/config-tool to github.com/quay/quay/config-tool
- [b57d88c0](https://github.com/quay/quay/commit/b57d88c0fc96ea00290a921efa115889a9ec7cd9): Use config-tool from this repo
- [29e28da6](https://github.com/quay/quay/commit/29e28da617e38b03e147155b0eedb8ad7a068529): Move config-tool into its own directory
- [65ea29ad](https://github.com/quay/quay/commit/65ea29ad58e7e63233e4f72cffd0b13d33ae1146): use isinstance to check instance type ([#2084](https://github.com/quay/quay/issues/2084))
- [5fb07695](https://github.com/quay/quay/commit/5fb076952e16b1bd5f97421a4d8eb5502699d996): Fix regexp in pull_request_linting.yaml ([#2083](https://github.com/quay/quay/issues/2083))
- [aea7ba03](https://github.com/quay/quay/commit/aea7ba03089a775edd06620cf8f7913069cfe992): Use conventional-commit-checker-action for Jira check (PROJQUAY-5672) ([#2082](https://github.com/quay/quay/issues/2082))
- [2fae683a](https://github.com/quay/quay/commit/2fae683a533659558080e8952be22fa28701e024): v3.8.11 changelog bump (PROJQUAY-5869) ([#2038](https://github.com/quay/quay/issues/2038))
- [cb82a468](https://github.com/quay/quay/commit/cb82a4681b62e706596ab8a3c01b7c08207dce7a): Bump dependencies (PROJQUAY-5630) ([#211](https://github.com/quay/quay/issues/211))
- [9a562abe](https://github.com/quay/quay/commit/9a562abeca116f5c38a7d343b84bc3eac44779f3): Use buildx v0.11.0-rc2 ([#1960](https://github.com/quay/quay/issues/1960)) ([#2013](https://github.com/quay/quay/issues/2013))
- [290ebbe2](https://github.com/quay/quay/commit/290ebbe2c04f338dca04b29b533d17e50449624e): Create Quay PR from the same push event
- [11cc5961](https://github.com/quay/quay/commit/11cc596145b5732c7704bda2bb88bca3c98f0233): Use DEPLOY_PAT so that GitHub reacts on new tags
- [4b95f4dd](https://github.com/quay/quay/commit/4b95f4dddee665d870fe1b5fdf25221725d28cbd): Create PR against Quay for new tags ([#212](https://github.com/quay/quay/issues/212))
- [77b91045](https://github.com/quay/quay/commit/77b91045cc58716cdb47cd8f17c67110a4b6be9f): Bump http-swagger (PROJQUAY-3643) ([#198](https://github.com/quay/quay/issues/198))
### Ci
- [202973a1](https://github.com/quay/quay/commit/202973a1b1bf516ae46792ee50775dadf21b713c): Update golang version in CI (PROJQUAY-1605)
### Config
- [509884f6](https://github.com/quay/quay/commit/509884f6e01b3175b09515188dce7eb2e6ddb68e): Allow download of unvalidated config (PROJQUAY-1925)
### Configtool
- [a1c33a95](https://github.com/quay/quay/commit/a1c33a95b2c9f495fde520b50307b3f1efc33e25): Add option to override Azure endpoint (PROJQUAY-891) ([#164](https://github.com/quay/quay/issues/164))
### Configvalidation
- [e7fef0e8](https://github.com/quay/quay/commit/e7fef0e80385a6a06a32d3d009e37311936320fa): load only certificates (PROJQUAY-2416) ([#118](https://github.com/quay/quay/issues/118))
### Defaults
- [250e355a](https://github.com/quay/quay/commit/250e355a3004fefaf5136e4a46280d5f9c1902dc): Add defaults for nested repos and init users (PROJQUAY-2425) ([#130](https://github.com/quay/quay/issues/130))
### Deploy
- [5f9333ce](https://github.com/quay/quay/commit/5f9333ce08793c186bc1adeee34e8ea3806538fb): use PAT for creating PR on quay repo (PROJQUAY-5048) ([#207](https://github.com/quay/quay/issues/207))
- [11481cd2](https://github.com/quay/quay/commit/11481cd2f208ff17d14e31c71d10bb63bc6eea89): fix release.yaml quote (PROJQUAY-5048) ([#206](https://github.com/quay/quay/issues/206))
- [28b4036c](https://github.com/quay/quay/commit/28b4036cae86184ff079fb1c8823f6e400809d74): Create a PR against quay for every release (PROJQUAY-5048) ([#204](https://github.com/quay/quay/issues/204))
- [58f85e46](https://github.com/quay/quay/commit/58f85e46d95c2e87938c6d1f43c48f32f38d392c): Add workflow to auto release on push (PROJQUAY-5048) ([#200](https://github.com/quay/quay/issues/200))
### Docs
- [589a932b](https://github.com/quay/quay/commit/589a932b50791df416329fe65d456bf2897eda00): Add documentation for TLS usage (PROJQUAY-4558) ([#188](https://github.com/quay/quay/issues/188))
- [31de43f6](https://github.com/quay/quay/commit/31de43f6ccc005e6d5009aefdf935f98fe1834fe): Remove link from example .env file
### Editor
- [408c0535](https://github.com/quay/quay/commit/408c05355202e5e325190614c76d65421992cdf5): Remove BITTORRENT_FILENAME_PEPPER from generated config
- [fd0a2762](https://github.com/quay/quay/commit/fd0a2762c9d6dfe07877d0d152d9ed378034351b): Remove certs from ui scope on select external-tls (PROJQUAY-2528) ([#127](https://github.com/quay/quay/issues/127))
- [0f77b0b4](https://github.com/quay/quay/commit/0f77b0b41c07c860991f196c0b3cfb525a0894dc): Add logic to allow managing/unmanaging of RepoMirror from ui ([#126](https://github.com/quay/quay/issues/126))
- [ef304b75](https://github.com/quay/quay/commit/ef304b75d280dead30aac42edbe025d6e5aee32b): Add sslmode=verify-full when Postgres cert uploaded (PROJQUAY-2200) ([#111](https://github.com/quay/quay/issues/111))
### Fix
- [6ea08094](https://github.com/quay/quay/commit/6ea08094fc436f01ddafa2ef9d7680069eb425b9): Pass CONTAINER_RUNTIME to quay-builder (PROJQUAY-5910) ([#2106](https://github.com/quay/quay/issues/2106))
### Frontend
- [a24d8708](https://github.com/quay/quay/commit/a24d870839f27e6138dfdc1703ea36b49226db2e): Set default USERFILES_LOCATION to a valid storage
### Go
- [372289ad](https://github.com/quay/quay/commit/372289ada43db9cf3e2fd10eca3f482b14677c3a): Update golang to version 1.16 (PROJQUAY-1605) ([#176](https://github.com/quay/quay/issues/176))
### Href
- [0d37fb03](https://github.com/quay/quay/commit/0d37fb03055ba891dc89ede742c9fd5becb49c7f): Fix broken link (PROJQUAY-2449) ([#114](https://github.com/quay/quay/issues/114))
### Ldap
- [acc37482](https://github.com/quay/quay/commit/acc3748236b3123fa3ab55faf1d5061eb5d4293c): Remove validation check for users (PROJQUAY-2343) ([#142](https://github.com/quay/quay/issues/142))
### Merge Branch 'FileUploads' Of Https
- [d9dbde22](https://github.com/quay/quay/commit/d9dbde226d12736bcd8b97cf5724bd7f993a60ee): //github.com/quay/config-tool into fileUploads
- [3680dc27](https://github.com/quay/quay/commit/3680dc2798139f03ba205f524d0f81b078706b94): //github.com/quay/config-tool into fileUploads
- [98671957](https://github.com/quay/quay/commit/986719579ccd98710c0c282d26185d88ec4a0e6c): //github.com/quay/config-tool into fileUploads
- [c0e31276](https://github.com/quay/quay/commit/c0e312760248a6adf570b1774d1bbd8276635807): //github.com/quay/config-tool into fileUploads
### Merge Branch 'Master' Of Github.Com
- [0b3e2402](https://github.com/quay/quay/commit/0b3e240243d47db799a00fb0428e50bf83357c92): quay/config-tool
### Merge Branch 'Master' Of Https
- [276308dd](https://github.com/quay/quay/commit/276308ddcfe4f516db1013c137a7cc3ae1911ece): //github.com/quay/config-tool
- [dce89b56](https://github.com/quay/quay/commit/dce89b5642172325e39bbe3c225949906975aafd): //github.com/quay/config-tool
- [adedb28a](https://github.com/quay/quay/commit/adedb28ab7fc0e3da59cc25c87413c32dc63f3dd): //github.com/quay/config-tool
### Redis
- [ac69360b](https://github.com/quay/quay/commit/ac69360b84422c2f9830df11033ad39df42ded0a): Increase Redis timeout from 3 seconds to 10 seconds
### S3validation
- [b40c62ce](https://github.com/quay/quay/commit/b40c62ce7dd4715f77a074a5affe3dc0ab3b58ff): Pass token during ec2 role auth (PROJQUAY-2983) ([#153](https://github.com/quay/quay/issues/153))
### Securityscanner
- [1a4e817b](https://github.com/quay/quay/commit/1a4e817bf3f8cbbc2baeb8aa69cf84be7dabcba3): validate introspection endpoint (PROJQUAY-1610)
### Setup
- [92c96876](https://github.com/quay/quay/commit/92c9687656cdf9fcf878ff0553665c89918ef61b): Add ALLOWED_OCI_ARFICAT_TYPES to generated config (PROJQUAY-1032) ([#110](https://github.com/quay/quay/issues/110))
### Smtp
- [764673d2](https://github.com/quay/quay/commit/764673d2d2152aab600480a07b672bb3d7041e9f): Use TLS certs when connecting to smpt (PROJQUAY-1605) ([#175](https://github.com/quay/quay/issues/175))
### Ssl
- [89755418](https://github.com/quay/quay/commit/89755418fd08b06682a45bc1d3530e1552fbee94): re-enable .key file loading (PROJQUAY-2511) ([#123](https://github.com/quay/quay/issues/123))
### Storage
- [bbdefcb8](https://github.com/quay/quay/commit/bbdefcb8eace5dfaf9c5c9f891d47268c4740700): Add CloudFlare and MultiCDN config validation (PROJQUAY-5048) ([#199](https://github.com/quay/quay/issues/199))
- [c5a1a7c0](https://github.com/quay/quay/commit/c5a1a7c0ccb56c4b432c63d947a1a37a7bde3205): Do not require a storage_path in Distributed Storage Configuration ([#133](https://github.com/quay/quay/issues/133))
### Tls
- [ca5a4280](https://github.com/quay/quay/commit/ca5a4280493c5ee9d99d97f3095fa399b2f98fc1): Set external tls termination flag to false when internal (PROJQUAY-2428) ([#124](https://github.com/quay/quay/issues/124))
### Tlscomponent
- [ddc1b3de](https://github.com/quay/quay/commit/ddc1b3de8124fc4f922663a949d8dd2c2e10fdc5): changing option message for custom tls (PROJQUAY-2428) ([#117](https://github.com/quay/quay/issues/117))
### Ui
- [76146760](https://github.com/quay/quay/commit/76146760493870bfc8b9860ad901e91ddcf3ad78): Show extra_ca_cert_ prefix (PROJQUAY-3318) ([#158](https://github.com/quay/quay/issues/158))
### Validation
- [4c0a37a4](https://github.com/quay/quay/commit/4c0a37a4a2c44723ac5fd07d9e1f44577e2c9d66): calls to gcs should always be secure (PROJQUAY-2722) ([#131](https://github.com/quay/quay/issues/131))
- [04973cc1](https://github.com/quay/quay/commit/04973cc13ba89142100898fb4ed827a9452189e5): fix postgres root cert validation (PROJQUAY-2414) ([#113](https://github.com/quay/quay/issues/113))
### Validator
- [c4a3b5db](https://github.com/quay/quay/commit/c4a3b5db3771b0f32b5ad0c3a6e19723ed028124): Fix database.pem path in config.yaml (PROJQIUAY-4222) ([#181](https://github.com/quay/quay/issues/181))
- [75c713c7](https://github.com/quay/quay/commit/75c713c7ef7b08f59c7dff649e5c87efba580452): Use user provided endpoint for Gitlab and Github OAuth validations (PROJQUAY-2560) ([#168](https://github.com/quay/quay/issues/168))
- [3bfe148b](https://github.com/quay/quay/commit/3bfe148b909e59132be99b9b329e07561d730720): Check for IAM role when aws keys missing. (PROJQUAY-1626) ([#109](https://github.com/quay/quay/issues/109))
### Validators
- [f4fd536f](https://github.com/quay/quay/commit/f4fd536fc38dae19bd1baac6eb32d24f7ca5af4a): Remove cloudfront API calls that may not be included in policy (PROJQUAY-0000)
### [PROJQUAY-1149] Fix: Use Mysql+Pymysql
- [8cac4e77](https://github.com/quay/quay/commit/8cac4e7702a26c2d74b919a27db606c3398bfdc9): // for MySQL DB_URI
### [Redhat-3.8] Api
- [177ac5da](https://github.com/quay/quay/commit/177ac5da64c763177d85d4a84ae78947741ab5a0): Adding ignore timezone flag when parsing datetime (PROJQUAY-5360) ([#2080](https://github.com/quay/quay/issues/2080))
### [Redhat-3.8] Build(Deps)
- [aa8996f1](https://github.com/quay/quay/commit/aa8996f147a44eb63eb14a6868a165a0cbe0632b): bump golang.org/x/net (PROJQUAY-5339) ([#2095](https://github.com/quay/quay/issues/2095))
### [Redhat-3.8] Pagination
- [7abedb68](https://github.com/quay/quay/commit/7abedb68a4e46d773085d32938e3fac7e340f9e6): Fixing paginate for /api/v1/superuser/logs API (PROJQUAY-5360) ([#2010](https://github.com/quay/quay/issues/2010))
### [Redhat-3.8] Secscan_model
- [0f134d35](https://github.com/quay/quay/commit/0f134d35b0e3a67ee6a1175d2fd0cd46ce935dac): attempt urldecoding fixed_in_version (PROJQUAY-5886) ([#2066](https://github.com/quay/quay/issues/2066))
### Pull Requests
- Merge pull request [#2092](https://github.com/quay/quay/issues/2092) from dmage/merge-config-tool-3.8
- Merge pull request [#108](https://github.com/quay/quay/issues/108) from quay/PROJQUAY-1998
- Merge pull request [#107](https://github.com/quay/quay/issues/107) from quay/PROJQUAY-1815
- Merge pull request [#104](https://github.com/quay/quay/issues/104) from syed/add-redis-ssl
- Merge pull request [#106](https://github.com/quay/quay/issues/106) from quay/loggin_refactor
- Merge pull request [#105](https://github.com/quay/quay/issues/105) from quay/scram_fix
- Merge pull request [#100](https://github.com/quay/quay/issues/100) from alecmerdler/PROJQUAY-1610
- Merge pull request [#99](https://github.com/quay/quay/issues/99) from quay/PROJQUAY-1963
- Merge pull request [#98](https://github.com/quay/quay/issues/98) from quay/PROJQUAY-1964
- Merge pull request [#97](https://github.com/quay/quay/issues/97) from quay/ensure_mail_tls_fips
- Merge pull request [#95](https://github.com/quay/quay/issues/95) from thomasmckay/1925-config-download
- Merge pull request [#93](https://github.com/quay/quay/issues/93) from alecmerdler/oidc-tls-client
- Merge pull request [#90](https://github.com/quay/quay/issues/90) from kleesc/set-correct-userfiles-location-default
- Merge pull request [#87](https://github.com/quay/quay/issues/87) from thomasmckay/1633-secret-key
- Merge pull request [#83](https://github.com/quay/quay/issues/83) from alecmerdler/PROJQUAY-1577
- Merge pull request [#80](https://github.com/quay/quay/issues/80) from quay/aioi_gen
- Merge pull request [#82](https://github.com/quay/quay/issues/82) from quay/PROJQUAY-1561
- Merge pull request [#78](https://github.com/quay/quay/issues/78) from quay/PROJQUAY-1270
- Merge pull request [#77](https://github.com/quay/quay/issues/77) from quay/PROJQUAY-1262
- Merge pull request [#76](https://github.com/quay/quay/issues/76) from quay/PROJQUAY-541
- Merge pull request [#74](https://github.com/quay/quay/issues/74) from quay/vendor
- Merge pull request [#72](https://github.com/quay/quay/issues/72) from alecmerdler/PROJQUAY-1306
- Merge pull request [#70](https://github.com/quay/quay/issues/70) from quay/oidc
- Merge pull request [#69](https://github.com/quay/quay/issues/69) from quay/mail_validate
- Merge pull request [#68](https://github.com/quay/quay/issues/68) from quay/swiftV3
- Merge pull request [#67](https://github.com/quay/quay/issues/67) from quay/fix_file_input
- Merge pull request [#66](https://github.com/quay/quay/issues/66) from quay/remove_boolean_omitempty
- Merge pull request [#65](https://github.com/quay/quay/issues/65) from quay/fix_modals
- Merge pull request [#64](https://github.com/quay/quay/issues/64) from quay/swift_validation
- Merge pull request [#63](https://github.com/quay/quay/issues/63) from quay/ldap_query
- Merge pull request [#62](https://github.com/quay/quay/issues/62) from quay/feature_sign
- Merge pull request [#61](https://github.com/quay/quay/issues/61) from quay/cert_port
- Merge pull request [#60](https://github.com/quay/quay/issues/60) from quay/cloudfront
- Merge pull request [#59](https://github.com/quay/quay/issues/59) from quay/dbssl
- Merge pull request [#58](https://github.com/quay/quay/issues/58) from quay/fixjs
- Merge pull request [#56](https://github.com/quay/quay/issues/56) from quay/ldap
- Merge pull request [#55](https://github.com/quay/quay/issues/55) from quay/checkBucket
- Merge pull request [#54](https://github.com/quay/quay/issues/54) from alecmerdler/PROJQUAY-1156
- Merge pull request [#53](https://github.com/quay/quay/issues/53) from BillDett/PROJQUAY-1202
- Merge pull request [#52](https://github.com/quay/quay/issues/52) from quay/switchTLS
- Merge pull request [#51](https://github.com/quay/quay/issues/51) from quay/tls_timeout
- Merge pull request [#50](https://github.com/quay/quay/issues/50) from quay/azure
- Merge pull request [#49](https://github.com/quay/quay/issues/49) from quay/time_machine
- Merge pull request [#48](https://github.com/quay/quay/issues/48) from thomasmckay/1198-deprecated
- Merge pull request [#47](https://github.com/quay/quay/issues/47) from quay/storage_fix
- Merge pull request [#46](https://github.com/quay/quay/issues/46) from quay/cert_fix
- Merge pull request [#45](https://github.com/quay/quay/issues/45) from quay/fix_mail
- Merge pull request [#41](https://github.com/quay/quay/issues/41) from kurtismullins/PROJQUAY-1149
- Merge pull request [#44](https://github.com/quay/quay/issues/44) from quay/gitlab_endpoint
- Merge pull request [#43](https://github.com/quay/quay/issues/43) from quay/tar2
- Merge pull request [#42](https://github.com/quay/quay/issues/42) from quay/clean_dev_env
- Merge pull request [#40](https://github.com/quay/quay/issues/40) from quay/storage_fix
- Merge pull request [#39](https://github.com/quay/quay/issues/39) from quay/debug
- Merge pull request [#38](https://github.com/quay/quay/issues/38) from quay/super_users
- Merge pull request [#37](https://github.com/quay/quay/issues/37) from quay/setup_add_vars
- Merge pull request [#36](https://github.com/quay/quay/issues/36) from quay/clair_setup
- Merge pull request [#29](https://github.com/quay/quay/issues/29) from quay/security_scanner_psk
- Merge pull request [#34](https://github.com/quay/quay/issues/34) from quay/omitempty
- Merge pull request [#35](https://github.com/quay/quay/issues/35) from quay/warn_no_mount
- Merge pull request [#33](https://github.com/quay/quay/issues/33) from quay/cert_load_cli
- Merge pull request [#30](https://github.com/quay/quay/issues/30) from quay/add_nullfix_to_api
- Merge pull request [#31](https://github.com/quay/quay/issues/31) from quay/postgres_pg_check
- Merge pull request [#32](https://github.com/quay/quay/issues/32) from alecmerdler/PROJQUAY-1107
- Merge pull request [#28](https://github.com/quay/quay/issues/28) from quay/tls
- Merge pull request [#27](https://github.com/quay/quay/issues/27) from quay/localstorage_fix
- Merge pull request [#26](https://github.com/quay/quay/issues/26) from quay/chi_migration
- Merge pull request [#24](https://github.com/quay/quay/issues/24) from alecmerdler/distributedstorage-proxy
- Merge pull request [#23](https://github.com/quay/quay/issues/23) from alecmerdler/PROJQUAY-909
- Merge pull request [#14](https://github.com/quay/quay/issues/14) from thomasmckay/npm
- Merge pull request [#21](https://github.com/quay/quay/issues/21) from alecmerdler/distributedstorage-unmarshal
- Merge pull request [#19](https://github.com/quay/quay/issues/19) from alecmerdler/PROJQUAY-1064
- Merge pull request [#18](https://github.com/quay/quay/issues/18) from quay/repo_mirror
- Merge pull request [#16](https://github.com/quay/quay/issues/16) from alecmerdler/PROJQUAY-909
- Merge pull request [#17](https://github.com/quay/quay/issues/17) from alecmerdler/PROJQUAY-1029
- Merge pull request [#15](https://github.com/quay/quay/issues/15) from quay/remove-hardcoded-conf-path
- Merge pull request [#13](https://github.com/quay/quay/issues/13) from quay/fileUploads
- Merge pull request [#11](https://github.com/quay/quay/issues/11) from josephschorr/config-editor
- Merge pull request [#10](https://github.com/quay/quay/issues/10) from alecmerdler/pull-request-template
- Merge pull request [#9](https://github.com/quay/quay/issues/9) from alecmerdler/fix-json-tags-hostsettings
- Merge pull request [#8](https://github.com/quay/quay/issues/8) from alecmerdler/distributedstorage-omitempty
- Merge pull request [#7](https://github.com/quay/quay/issues/7) from alecmerdler/dbconnectionargs-omitempty
- Merge pull request [#6](https://github.com/quay/quay/issues/6) from alecmerdler/json-tags
- Merge pull request [#5](https://github.com/quay/quay/issues/5) from alecmerdler/distributedstorage-fieldgroup
- Merge pull request [#4](https://github.com/quay/quay/issues/4) from alecmerdler/securityscanner-typefix
- Merge pull request [#3](https://github.com/quay/quay/issues/3) from quay/remove_validate_dep
- Merge pull request [#2](https://github.com/quay/quay/issues/2) from quay/remove_validate_dep
- Merge pull request [#1](https://github.com/quay/quay/issues/1) from quay/new_schema


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

<a name="v3.7.14"></a>
## [v3.7.14] - 2023-09-06

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

[Unreleased]: https://github.com/quay/quay/compare/v3.11.0...HEAD
[v3.11.0]: https://github.com/quay/quay/compare/v3.10.4...v3.11.0
[v3.10.4]: https://github.com/quay/quay/compare/v3.10.3...v3.10.4
[v3.10.3]: https://github.com/quay/quay/compare/v3.10.2...v3.10.3
[v3.10.2]: https://github.com/quay/quay/compare/v3.10.1...v3.10.2
[v3.10.1]: https://github.com/quay/quay/compare/v3.10.0...v3.10.1
[v3.10.0]: https://github.com/quay/quay/compare/v3.9.6...v3.10.0
[v3.9.6]: https://github.com/quay/quay/compare/v3.9.5...v3.9.6
[v3.9.5]: https://github.com/quay/quay/compare/v3.9.4...v3.9.5
[v3.9.4]: https://github.com/quay/quay/compare/v3.9.3...v3.9.4
[v3.9.3]: https://github.com/quay/quay/compare/v3.9.2...v3.9.3
[v3.9.2]: https://github.com/quay/quay/compare/v3.9.1...v3.9.2
[v3.9.1]: https://github.com/quay/quay/compare/v3.9.0...v3.9.1
[v3.9.0]: https://github.com/quay/quay/compare/v3.8.15...v3.9.0
[v3.8.15]: https://github.com/quay/quay/compare/v3.8.14...v3.8.15
[v3.8.14]: https://github.com/quay/quay/compare/v3.8.13...v3.8.14
[v3.8.13]: https://github.com/quay/quay/compare/v3.8.12...v3.8.13
[v3.8.12]: https://github.com/quay/quay/compare/v3.8.11...v3.8.12
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
[v3.8.0]: https://github.com/quay/quay/compare/v3.7.14...v3.8.0
[v3.7.14]: https://github.com/quay/quay/compare/v3.7.13...v3.7.14
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
