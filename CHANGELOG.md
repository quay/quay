### v3.4.7

**Release Notes**
(Red Hat Customer Portal)[https://access.redhat.com/documentation/en-us/red_hat_quay/3.4/html/red_hat_quay_release_notes/index]

### v3.4.6

**Release Notes**
(Red Hat Customer Portal)[https://access.redhat.com/documentation/en-us/red_hat_quay/3.4/html/red_hat_quay_release_notes/index]


### v3.4.5

**Release Notes**
(Red Hat Customer Portal)[https://access.redhat.com/documentation/en-us/red_hat_quay/3.4/html/red_hat_quay_release_notes/index]


### v3.4.4

**Fixed**
- Fix Clair not recognizing python language vulnerabilities (PROJQUAY-1775)[https://issues.redhat.com/browse/PROJQUAY-1775]
- Fix Clair not honoring DisableUpdaters config option (PROJQUAY-1759)[https://issues.redhat.com/browse/PROJQUAY-1759]

**Release Notes**
(Red Hat Customer Portal)[https://access.redhat.com/documentation/en-us/red_hat_quay/3.4/html/red_hat_quay_release_notes/index]


### v3.4.3

**Fixed**
- Fix Quay security scanning backfill API (PROJQUAY-1613)[https://issues.redhat.com/browse/PROJQUAY-1613]
- Fix Quay Operator handling of provided certificates related to BUILDMAN_HOSTNAME (PROJQUAY-1577)[https://issues.redhat.com/browse/PROJQUAY-1577]
- Fix Clair python language matching (PROJQUAY-1692)[https://issues.redhat.com/browse/PROJQUAY-1692]

**Release Notes**
(Red Hat Customer Portal)[https://access.redhat.com/documentation/en-us/red_hat_quay/3.4/html/red_hat_quay_release_notes/index]


### v3.4.2

**Fixed**
- Fix clair crash downloading RHEL content mapping
- Quay config-tool validates SMTP
- Fix Quay Operator reconciler loop resulting in failed mirror configurations
- Quay config-tool generates default SECRET_KEY in config bundle if not specified

**Release Notes**
(Red Hat Customer Portal)[https://access.redhat.com/documentation/en-us/red_hat_quay/3.4/html/red_hat_quay_release_notes/index]


### v3.4.1

**Fixed**
- Quay Bridge Operator and Quay Container Security Operator upgrade to 3.4.0
- Quay Operator generates correct cert for build manager
- Quay config editor validates OIDC provider
- Quay config editor correctly validates MySQL database with SSL
- Quay Operator documentation link corrected to 3.4
- Quay config editor no longer requires Time Machine expiration when feature not enabled

**Release Notes**
(Red Hat Customer Portal)[https://access.redhat.com/documentation/en-us/red_hat_quay/3.4/html/red_hat_quay_release_notes/index]

### v3.4.0

**Release Notes**
(Red Hat Customer Portal)[https://access.redhat.com/documentation/en-us/red_hat_quay/3.4/html/red_hat_quay_release_notes/index]

### v3.3.1

**Fixed**
- Config app installs supplied TLS certs at startup
- Tech preview clair-v4 correctly reindexes manifests
- Build triggers may disclose robot account names (CVE-2020-14313)

### v3.3.0

**Added**
- New clair available as tech preview (see docs) 
- Quay now runs as the default user inside the container instead of as root.
- New configurable tagging options for builds, including tagging templates and ability to disable default “latest” and tag/branch behavior
- Configuration UI editing after validating through the “Save Configuration” button.
- Configuration app now supports configuring Elasticsearch for usage logs (and optionally via Kinesis - Docs should mention logstash or something similar is needed in this case). 
- Ability to configure how long between “fresh login” checks
- Ability to add an additional filter for LDAP users on lookup
- Labels with links in them are now clickable to go to the URL
- The environment variable CONFIG_READ_ONLY_FIELDS can be specified to mark redis or the hostname configuration as read-only in the Quay Configuration Application’s UI. #310
- (Tech Preview) Support for OCI indexes and manifests
- (Tech Preview) Support for pushing and pulling charts via Helm V3’s experimental system

**Fixed**
- Repository mirror tag patterns handle whitespace between comma separated values.
- Fresh login checks were being used when unnecessary
- Georeplication from one Azure region to the other now uses the correct bucket and credentials
- Auth token handling to match recent GitHub API change
- Repository and namespace deletion now occurs in the background, ensuring they don’t fail
- No longer return “down converted” manifests on pull-by-digest
- Tags expiring in the future are now marked correctly as such in the tag history panel
- A number of performance improvements around various database queries
- Status codes of various Docker V2 APIs to conform with the spec
- Repository names now conform to the standard. Only lowercase letters, numbers, underscores, and hyphens are valid.
- Certificates can now be uploaded in the Quay Configuration Application correctly and used to validate connections to external services (such as LDAP, Persistent Storage) during the configuration process.

**Deprecated**
- "rkt" conversion: This feature is now marked as deprecated in the Red Hat Quay UI. Expect the feature to be removed completely in the near future.
- Bittorrent: This feature is deprecated and will not appear in the Red Hat Quay UI unless it is already configured in an existing Red Hat Quay config.yaml. This feature will be removed in the next version of Quay.
- V1 Push Support: Docker V1 protocol support has been officially deprecated. Expect this feature to be removed in the next near future.
- Squashed image support: This feature is deprecated. This feature will be removed in the next version of Quay.
- images API: This API is deprecated and replaced by the manifest APIs. Expect this API to be removed completely in the near future.

**Reminder**
- Do not use "Locally mounted directory" Storage Engine for any production configurations. Mounted NFS volumes are not supported. Local storage is meant for test-only installations.

**Known Issues**
- Containers running as repository mirrors may lock under certain conditions; restart the containers as needed.

### v3.2.0

**NOTE** A new required config.yaml entry “DATABASE_SECRET_KEY” must be manually added to existing installs. See documentation.
- Added: All tokens in the database are now encrypted (CVE-2019-10205).
- Added: Support for OpenShift Container Storage 4 leveraging NooBaa Multi-Cloud Gateway.
- Added: Improved repository mirror logging.
- Added: Notifications enabled for repository mirror start, finish, and error.
- Fixed: Remove validation from repository mirror proxy config.
- Fixed: Broken scrollbars in UI on pages such as repository tags.
- Fixed: Inability to star a repository

### v3.1.2

- Fixed: Repository mirroring properly updates status
- Fixed: Application repositories in public namespaces shown in UI
- Fixed: Description of log operations in UI
- Fixed: Quay V3 upgrade fails with "id field missing from v1Compatibility JSON"
- Fixed: Security token for storage proxy properly URL encoded

### v3.1.1

- Fixed: Quoting of username/password for repository mirror
- Fixed: Changing next sync date in repository mirror UI
- Fixed: Enable cancel button in repository mirror UI

### v3.1.0

- Added: New Repository Mirror functionality to continously synchronize repositories from external source registries into Quay
- Added: New Repository Mode setting (Normal, Mirrored, Read-Only) to indicate how a repository is updated
- Added: New Quay Setup Operator (Dev Preview) to automate configuring Quay on OpenShift
- Added: Support for using Red Hat OpenShift Container Storage 3 as a Quay storage backend
- Added: Support for using the Crunchy Data Operator to deploy Postgresql as Quay database
- Added: Ability to use build ARGS as first line in Dockerfiles in Quay builds
- Added: New Red Hat color scheme in Quay web UI
- Fixed: Display of repo_verb logs in logs panel
- Fixed: Ensure robot accounts being granted access actually belongs in same namespace
- Fixed: Numerous documentation improvements

### v3.0.5

- Fixed: LDAP config error when user search results exceeds 1000 objects (#1736)[https://jira.coreos.com/browse/QUAY-1736]
- Fixed: Remove obsolete 01_copy_syslog_config.sh (#1768)[https://jira.coreos.com/browse/QUAY-1768)
- Fixed: Config tool fails to set up database when password string contains "$" (#1510)[https://jira.coreos.com/browse/QUAY-1510)
- Added: Config flag to disable TLSv1.0 support (#1726)[https://jira.coreos.com/browse/QUAY-1726]

### v3.0.4

- Fixed: Package vulnerability notifications now shown in UI
- Fixed: Error deleting manifest after pushing new tag
- Fixed: Manifest now shown in UI for all types
- Fixed: CSRF rotation corrected
- Fixed: nginx access and error logs now to stdout

### v3.0.3

- Fixed: Security scan notifications endpoint not working (part #2) (#3472)
- Fixed: Exception raised during parallel pushes of same manifest on Postgres (#3478)
- Fixed: Connection pooling was ignoring environment variable (#3480)
- Fixed: Exception when in OAuth approval flow (#3491)

### v3.0.2

- Fixed: Configuration tool now operates in disconnected environments (#3468)
- Fixed: Security scan notifications endpoint not working (#3472)

### v3.0.1

- Fixed: Instance health endpoint (`/health/instance`) (#3467)

### v3.0.0

**IMPORTANT NOTE:** This release is a **major** release and has special upgrade instructions. Please see the upgrade instructions documentation.

- Added: Full support for Docker Manifest Version 2, Schema 2, including support for manifest lists and Windows images
- Added: New, distinct configuration tool for Quay that can be run outside of Quay itself and perform in-place configuration changes
- Added: Disabling of V1 push support by default and support for whitelist-enabling specific namespaces for this legacy protocol (#3398)
- Added: Full support for blob mounting via the Docker protocol (#3057)
- Added: Have all registry operations be disabled if a namespace is disabled (#3091)
- Added: Allow syncing of team members from LDAP/Keystone groups, even if user creation is disabled (#3089)
- Added: Add a feature flag to allow username confirmation to be disabled (#3099)
- Added: New indexes which should result in significant database performance when accessing lists of tags
- Added: Add support for POST on OIDC endpoints, to support those providers that POST back (#3246)
- Added: Add support for configuration of the claims required for OIDC authentication (#3246)
- Added: Have the instance health check verify the disk space available to ensure it doesn’t run out and cause problems for nginx (#3241)
- Added: Support for basic auth on security scanner API endpoints (#3255)
- Added: Support for geo-blocking pulls in a namespace from a country (#3300)

- Fixed: Ensure that starred public repositories appear in the starred repositories list (#3098)
- Fixed: Add rate limiting to the catalog endpoint (#3106)
- Fixed: Have the catalog endpoint return empty for a namespace if it is disabled (#3106)
- Fixed: Have user logs start writing to a new LogEntry3 table, which has a BigInteger ID column, to ensure no overflow
- Fixed: Improve loading of action logs to be less jumpy (#3299)
- Fixed: Ensure that all upload segments are deleted in Swift storage engine once no longer necessary (#3260)
- Fixed: Handling of unicode in manifests (#3325)
- Fixed: Unauthorized request handling under podman for public repositories when anonymous access is disabled (#3365)

### v2.9.2

**IMPORTANT NOTE:** This release fixes a bug in which the deletion of namespaces did not result in the deletion of robot accounts under that namespace. While this is not a security issue (no permissions or credentials are leaked), it can appear unusual to users, so an upgrade is highly recommended. This change also includes a migration that cleans up the aforementioned robot accounts, so the migration step can take **several minutes**. Please plan accordingly.

- Added: Support for custom query parameters on OIDC endpoints (#3050)
- Added: Configurable options for search page length and maximum number of pages (#3060) 
- Added: Better messaging for when the maximum search page is reached (#3060)
- Added: Support for browser notifications (#3068)

- Fixed: Robot accounts were not being immediately deleted under namespaces (#3071)
- Fixed: Setup under latest versions of Kubernetes (#3051)
- Fixed: Viewing of logs in repositories with many, many logs (#3082)
- Fixed: Filtering of deleting users and organizations in superuser panel (#3080)
- Fixed: Incorrect information displayed for builds triggered by deleted build triggers (#3078)
- Fixed: Robots could not be created with empty descriptions (#3073)
- Fixed: Inability to find Dockerfile in certain archives (#3072)
- Fixed: Display of empty tab in credentials dialog under certain circumstances (#3061)
- Fixed: Overflow of robot names when extremely long (#3062)
- Fixed: Respect CPU affinity when determining number of workers to run (#3064)
- Fixed: Breakage in RECATPCHA support (#3065)

### v2.9.1

**IMPORTANT NOTE:** This release fixes the 2.9.0 migration. If you experienced an error during the 2.9.0 migration, manually rollback and then upgrade your quay instance to 2.9.1.

- Fixed: Specify default server value for new integer fields added (#3052)
- Fixed: Overflow of repository grid UI (#3049)

### v2.9.0

- Added: Automatic cleanup of expired external application tokens (#3002)
- Added: Make deletions of namespaces occur in the background (#3014) 
- Added: Ability to disable build triggers (#2892) 
- Added: Have repeatedly failing build triggers be automatically disabled (#2892)
- Added: Automatic caching of registry Blob data for faster pull operations (#3022)
- Added: Creation date/time, last usage date/time and other metadata for robot accounts (#3024)
- Added: Collaborators view under organizations, for viewing non-members (#3025)

- Fixed: Make superusers APIs for users and organizations visible in the API browser (#3017)
- Fixed: Better messaging when attempting to create a team that already exists (#3006)
- Fixed: Prevent possible reflected text attacks by limiting API access (#2987)
- Fixed: Have checkable menus in UI respect filters (#3013)
- Fixed: Users being invited to a new organization must always be invited (#3029)
- Fixed: Removed all license requirements in Quay (#3031)	
- Fixed: Squashed images with hard links pointing to deleted files no longer fail (#3032)
- Fixed: 500 error when trying to pull certain images via torrent (#3036)

### v2.8.0

- Added: Support for Azure Blob Storage (#2902)
- Added: Ability to filter out disabled users in users list API (#2954)
- Added: Image ID in expanded tags view (#2965)
- Added: Processes auto-scale based on CPU count (#2971, 2978)
- Added: Health checks for all workers (#2977)
- Added: Health checks and auto-rotation for service keys (#2909)
- Added: Ability to back GitHub or Google login with LDAP/Keystone (#2983)
- Added: Configurable page size for Docker Registry V2 API pagination (#2993)

- Fixed: Anonymous calls to API discovery endpoint (#2953)
- Fixed: Optimized creation of repositories
- Fixed: Optimized manifest pushing
- Fixed: LDAP password input is now password field (#2970)
- Fixed: 500 raised when sending an invalid release name for app repos (#2979)
- Fixed: Deletion of expired external app tokens (#2981)
- Fixed: Sizing of OIDC login buttons (#2990)
- Fixed: Hide build-related UI when builds are not enabled (#2991)
- Fixed: Incorrect caching of external application token expiration (#2996)
- Fixed: Warning bar should not be displayed for already expired application tokens (#3003)

### v2.7.0

**NOTE:** This release *removes* support for the OIDC token internal authentication mechanism and replaces it with support for a new app-specific token system. All customers using the old OIDC token auth mechanism must change their configuration after updating manually in `config.yaml`.

- Added: Support for external application tokens to be used on the Docker CLI (#2942)
- Added: Explore tab for browsing visible repositories (#2921)
- Added: Ability to view and copy full manifest SHAs in tags view (#2898)
- Added: Support for robot tokens in App Registry pushes and pulls (#2899)

- Fixed: Failure when attempting to use Skopeo tool to access the registry (#2950)
- Fixed: Ordering of segments in Swift to match spec (#2920)
- Fixed: Squashed image downloading when using Postgres DB (#2930)
- Fixed: Hide "Start Build" button if the action is not allowed (#2916)
- Fixed: Exception when pushing certain labels with JSON-like contents (#2912)
- Fixed: Don't add password required notification for non-database auth (#2910)
- Fixed: Tags UI spacing on small displays (#2904)
- Fixed: Push updated notification now shows correct tags (#2897)
- Fixed: "Restart Container" button in superuser config panel (#2928)
- Fixed: Various small JavaScript security fixes

### v2.6.2
 
- Fixed: Failure to register uploaded TLS certificates (#2946)
 
### v2.6.1

- Added: Optimized overhead for direct downloads from Swift storage (#2889)
- Fixed: Immediately expire image builds that fail to start (#2887)
- Fixed: Failure to list all GitHub Enterprise namespaces (#2894)
- Fixed: Incorrect links to builds in notifications (#2895)
- Fixed: Failure to delete certain app repositories (#2893)
- Fixed: Inability to display Tag Signing status (#2890)
- Fixed: Broken health check for OIDC authentication (#2888)

### v2.6.0

- Added: Ability to use OIDC token for CLI login (#2695)
- Added: Documentation for OIDC callback URLs in setup tool
- Added: Ability for users to change their family and given name and company info (#2870)
- Added: Support for invite-only user sign up (#2867)
- Added: Option to disable partial autocompletion of users (#2864)
- Added: Georeplication support in Swift storage (#2874)
- Fixed: Namespace links ending in slashes (#2871)
- Fixed: Contact info setup in setup tool (#2866)
- Fixed: Lazy loading of teams and robots (#2883)
- Fixed: OIDC auth headers (#2695)

### v2.5.0

- Added: Better TLS caching (#2860)
- Added: Feature flag to allow read-only users to see build logs (#2850)
- Added: Feature flag to enable team sync setup when not a superuser (#2813)
- Added: Preferred public organizations list (#2850)
- Added: OIDC support for OIDC implementations without user info endpoint (#2817)
- Added: Support for tag expiration, in UI and view a special `quay.expires-after` label (#2718)
- Added: Health checks report failure reasons (#2636)
- Added: Enable database connection pooling (#2834)

- Fixed: setting of team resync option
- Fixed: Purge repository on very large repositories

### v2.4.0

- Added: Kubernetes Applications Support
- Added: Full-page search UI (#2529)
- Added: Always generate V2 manifests for tag operations in UI (#2608)
- Added: Option to enable public repositories in v2 catalog API (#2654)
- Added: Disable repository notifications after 3 failures (#2652)
- Added: Remove requirement for flash for copy button in UI (#2667)

- Fixed: Upgrade support for Markdown (#2624)
- Fixed: Kubernetes secret generation with secrets with CAPITAL names (#2640)
- Fixed: Content-Length reporting on HEAD requests (#2616)
- Fixed: Use configured email address as the sender in email notifications (#2635)
- Fixed: Better peformance on permissions lookup (#2628)
- Fixed: Disable federated login for new users if user creation is disabled (#2623)
- Fixed: Show build logs timestamps by default (#2647)
- Fixed: Custom TLS certificates tooling in superuser panel under Kubernetes (#2646, #2663)
- Fixed: Disable debug logs in superuser panel when under multiple instances (#2663)
- Fixed: External Notification Modal UI bug (#2650)
- Fixed: Security worker thrashing when security scanner not available
- Fixed: Torrent validation in superuser config panel (#2694)
- Fixed: Expensive database call in build badges (#2688)

### v2.3.4

- Added: Always show tag expiration options in superuser panel

### v2.3.3

- Added: Prometheus metric for queued builds (#2596)

- Fixed: Allow selection of Gitlab repository when Gitlab sends no permissions (#2601)
- Fixed: Failure when viewing Gitlab repository with unexpected schema (#2599)
- Fixed: LDAP stability fixes (#2598, #2584, #2595)
- Fixed: Viewing of repositories with trust enabled caused a 500 (#2594, #2593)
- Fixed: Failure in setup tool when time machine config is not set (#2589)

### v2.3.2

- Added: Configuration of time machine in UI (#2516)

- Fixed: Auth header in OIDC login UserInfo call (#2585)
- Fixed: Flash of red error box on loading (#2562)
- Fixed: Search under postgres (#2568)
- Fixed: Gitlab namespaces with null avatars (#2570)
- Fixed: Build log archiver race condition which results in missing logs (#2575)
- Fixed: Team synchronization when encountering a user with a shared email address (#2580)
- Fixed: Create New tooltip hiding dropdown menu (#2579)
- Fixed: Ensure build logs archive lookup URL checks build permissions (#2578)

### v2.3.1

**IMPORTANT NOTE:** This release fixes the 2.3.0 migration. If you experienced an error during the 2.3.0 migration, manually rollback and then upgrade your quay instance to 2.3.1.
- Fixed: Specify default server value for new bool field added to the repository table

### v2.3.0

- Added: LDAP Team Sync support (#2387, #2527)
- Added: Improved search performance through pre-computed scores (#2441, #2531, #2533, #2539)
- Added: Ability to allow pulls even if audit logging fails (#2306)
- Added: Full error information for build errors in Superuser panel (#2505)
- Added: Better error messages passed to the Docker client (#2499)
- Added: Custom git triggers can specify separate build context directory  (#2517, #2509)
- Added: Improved performance on repository list API (#2542, #2544, #2546)

- Fixed: Handle undefined case in build message (#2501)
- Fixed: OIDC configuration in Superuser panel (#2520)
- Fixed: Ability to invite team members by email address (#2522)
- Fixed: Avatars for non-owner namespaces in GitLab (#2507, #2532)
- Fixed: Update dependencies and remove warnings (#2518, #2511, #2535, #2545, #2553)
- Fixed: Remove link to blog (#2523)
- Fixed: Better handling for unavailable frontend dependencies (#2503)
- Fixed: Top level redirect logic for missing repositories (#2540)
- Fixed: Remove extra slash from missing base image permissions error in build logs (#2548)
- Fixed: Backfill replication script when adjusting replication destinations (#2555)
- Fixed: Errors when deleting repositories without security scanning enabled (#2554)

### v2.2.0

**IMPORTANT NOTE:** This release contains a migration which adds a new feature to the build system. This requires shutting down the entire cluster _including builders_ and running one instance to migrate the database forward. You _must_ use a v2.2.0 builder with a v2.2.0 Quay cluster.

- Added: Separate build contexts from Dockerfile locations (#2398, #2410, #2438, #2449, #2480, #2481)
- Added: Configuration and enforcement of maximum layer size (#2388)
- Added: OIDC configuration in the Super User Panel (#2393)
- Added: Batching of Security Scanner notifications (#2397)
- Added: Auth Failures now display messages on the docker client (#2428, #2474)
- Added: Redesigned Tags page to include Labels, Image ID Type, and more informative Security Scanner information (#2416)

- Fixed: Parsing new docker client version format (#2378)
- Fixed: Improved repository search performance (#2392, #2440)
- Fixed: Miscellaneous Build Trigger page issues (#2405, #2406, #2407, #2408, #2409, #2414, #2418, #2445)
- Fixed: Remove all actionable CVEs from the docker image (#2422, #2468)
- Fixed: Minor bugs in Repository views (#2423, #2430, #2431)
- Fixed: Improve performance by deleting keys in redis rather than expiring (#2439)
- Fixed: Better error messages when configuring cloud storage (#2444)
- Fixed: Validation and installation of custom TLS certificates (#2473)
- Fixed: Garbage Collection corner case (#2404)

### v2.1.0

**IMPORTANT NOTE FOR POSTGRES USERS:** This release contains a migration which adds full-text searching capabilities to Red Hat Quay. In order to support this feature, the migration will attempt to create the `pg_trgm` extension in the database. This operation requires **superuser access** to run and requires the extension to be installed. See https://coreos.com/quay-enterprise/docs/latest/postgres-additional-modules.html for more information on installing the extension.

If the user given to Red Hat Quay is not a superuser, please temporarily grant superuser access to the Red Hat Quay user in the database (or change the user in config) **before** upgrading.

- Added: Full text search support (#2272)
- Added: OIDC support (#2300, #2348)
- Added: API for lookup of security status of a manifest (#2334)
- Added: More descriptive logs (#2358)

- Fixed: Datetime bug in logs view (#2318)
- Fixed: Display bug in logs view (#2345)
- Fixed: Display of expiration date for licenses with multiple entries (#2354)
- Fixed: V1 search compatibility (#2344)

### v2.0.5

- Added: Build logs viewer in superuser panel

- Fixed: Support for wildcard certs in the superuser config panel

### v2.0.4

- Added: Expand allowed length of namespaces to be between 2 and 255 characters  (#2291)
- Added: Better messaging for namespaces (#2283)
- Added: More customization of Message Of The Day (MOTD) (#2282)
- Added: Configurable and default timeout for LDAP (#2247)
- Added: Custom SSL certificate panel in superuser panel (#2271, #2274)
- Added: User and Organization list pagination on superuser panel (#2250)
- Added: Performance improvements for georeplication queuing (#2254)
- Added: Automatic garbage collection in security scanner (#2257)
- Added: RECAPTCHA support during create account flow (#2245)
- Added: Always display full git error in build logs (#2277)
- Added: Superuser config clarification warnings (#2279)
- Added: Performance improvements around queues (#2276, #2286, #2287)
- Added: Automatic retry for security scanning (#2242)
- Added: Better error messaging on security scanner lookup failure (#2235)
- Added: Ensure robot accounts show at top of entity autocomplete (#2243)

- Fixed: Exception when autocompleting users in teams (#2255)
- Fixed: Port mapping in ACI conversion (#2251, #2273)
- Fixed: Error messaging for attempting to join a team with invalid email (#2240)
- Fixed: Prometheus metrics for scale (#2237)
- Fixed: Security scanner notification pagination (#2233, #2249)

- Regressed: Support for wildcard certs in the superuser config panel

### v2.0.3

- Added: Allow extra_ca_certs to be a folder or a file (#2180)

- Fixed: Cancelling builds (#2203)
- Fixed: Allow license to be set in setup tool (#2200)
- Fixed: Improve queue performance (#2207, #2211)
- Fixed: Improve security scan performance (#2209)
- Fixed: Fix user lookup for external auth engines (#2206)

### v2.0.2

- Added: Ability to cancel builds that are already building. (#2041, #2127, #2186, #2189, #2190)
- Added: Notifications when a build is canceled (#2173, #2184)
- Added: Remove deprecated email flag from generated `docker login` commands (#2146)
- Added: Upgrade nginx to v1.11.5 (#2140)
- Added: Improve performance of robots management UI (#2145)
- Added: Add data about specific manifest or tag pulled in audit logs (#2152)
- Added: Debug nginx logs from non-proxy protocol connection (#2167)
- Added: Accept multiple team invitations simultaneously (#2169)
- Added: Password recovery defaults to resetting password (#2170)
- Added: Gzip javascript and svg assets (#2171)
- Added: Add support for custom ports in RADOS and S3 storage engines (#2185)
- Added: Prometheus metric for number of unscanned images (#2183)

- Fixed: Fix entity search under Postgres (regression in v2.0.0) (#2172)
- Fixed: Error displayed for OAuth if an existing token already matches scopes (#2139)
- Fixed: Reduce timeouts of the build manager when under heavy load (#2143, #2157)
- Fixed: Fix guage metrics on prometheus endpoint (#2153)
- Fixed: Disable CoreOS update-engine on ephemeral Kubernetes builders (#2159)
- Fixed: Fix notifications generated by the build manager (#2163)
- Fixed: JSON encoding for chunk cleanup in Swift storage engine (#2162)
- Fixed: Fix configuration validator when setting up storage engine (#2176)
- Fixed: Multiline message of the day to not cover the search box (#2181)

- Regressed: User lookup for external auth engines broken

### v2.0.1

- Added: A defined timeout on all HTTP calls in notification methods
- Added: Customized Build start timeouts and better debug logs
- Added: A warning bar when the license will become invalid in a week
- Added: Collection of user metadata: name and company
- Added: New Prometheus metrics
- Added: Support for temp usernames and an interstitial to confirm username
- Added: Missing parameter on RADOS storage
- Added: Stagger worker startup
- Added: Make email addresses optional in external auth if email feature is turned off
- Added: External auth emails to entity search
- Added: Banner bar message when license has expired or is invalid

- Fixed: Make sure to check for user before redirecting in update user
- Fixed: 500 on get label endpoint and add a test
- Fixed: KeyError in Github trigger setup
- Fixed: Change LDAP errors into debug statements to reduce log clutter
- Fixed: Bugs due to conflicting operation names in the API
- Fixed: Cannot-use-robot for private base image bug in build dialog
- Fixed: Swift exception reporting on deletion and add async chunk cleanup
- Fixed: Logs view for dates that start in zero
- Fixed: Small JS error fixes
- Fixed: A bug with accessing the su config panel without a license
- Fixed: Buildcomponent: raise heartbeat timeout to 60s
- Fixed: KeyError in config when not present in BitBucket trigger
- Fixed: Namespace lookup in V1 registry search
- Fixed: Build notification ref filtering setup in UI
- Fixed: Entity search API to not IndexError
- Fixed: Remove setup and superuser routes when SUPER_USERS is not enabled
- Fixed: TypeError in Gitlab trigger when user not found

- Regressed: Superuser config panel cannot save

### v2.0.0

This release is a **required release** and must be run before attempting an upgrade to v2.0.0+.

In order to upgrade to this version, your cluster must contain a valid license, which can be found and downloaded at: [tectonic.com](https://account.tectonic.com)

- Added: Require valid license to enable registry actions (#2009, #2018)
- Added: The ability to delete users and organizations (#1698)
- Added: Add option to properly handle TLS terminated outside of the container (#1986)
- Added: Updated run trigger/build dialog (#1895)
- Added: Update dependencies to latest versions (#2012)
- Added: Ability to use dots and dashes in namespaces intended for use with newer Docker clients (#1852)
- Added: Changed dead queue item cleanup from 7 days to 1 day (#2019)
- Added: Add a default database timeout to prevent failed DB connections from hanging registry and API operations (#1764)

- Fixed: Fix error if a vulnerability notification doesn't have a level filter (#1995)
- Fixed: Registry WWW-Authenticate and Link headers are now Registry API compliant (#2004)
- Fixed: Small fixes for Message of the Day feature (#2005, #2006)
- Fixed: Disallow underscores at the beginning of namespaces (#1852)
- Fixed: Installation tool liveness checks during container restarts (#2023)

- Regressed: Entity search broken under Postgres

### v1.18.0

- Added: Add message of the day (#1953)
- Added: Add repository list pagination (#1858)
- Added: Better 404 (and 403) pages (#1857)

- Fixed: Always use absolute URLs in Location headers to fix blob uploads on nonstandard ports (#1957)
- Fixed: Improved reliability of several JS functions (#1959) (#1980) (#1981)
- Fixed: Handle unicode in entity search (#1939)
- Fixed: Fix tags API pagination (#1926)
- Fixed: Add configurable timeout and debug flags to Keystone users (#1867)
- Fixed: Build notifications were failing to fire (#1859)
- Fixed: Add feature flag to turn off requirement for team invitations (#1845)
- Fixed: Don't exception log for expected 404s in Swift storage  (#1851)

### v1.17.1

- Added: Repository admins can now invoke build triggers manually (#1822)
- Added: Improved notifications UI and features (#1839)
- Added: Improved UX for managing teams (#1509)

- Fixed: Timeline's delete-then-tag display bug (#1824)
- Fixed: Add .well-known endpoint for Quay (#1790)
- Fixed: .tar.gz does not work when building from archive via web UI (#1832)
- Fixed: Delete empty Swift chunks (#1844)
- Fixed: Handling of custom LDAP cert (#1846)

### v1.17.0

- Added: Added Labels API (#1631)
- Added: Kubernetes namespace existence check (#1771)
- Added: New UI and permissions handling for robots and teams (#1754, #1815)
- Added: Retry attempts to the S3-like storages (#1748, #1801, #1802)
- Added: Improved messaging when changing email addresses (#1735)
- Added: Emails now include logos (#1691)
- Added: Improved messaging around expired builds (#1681)

- Fixed: Logs inside the container failing to rotate (#1812)
- Fixed: Filtering of repositories only visible to organization admins (#1795)
- Fixed: Invalid HTTP response when creating a duplicate tag (#1780)
- Fixed: Asynchronous Worker robustness (#1778, #1781)
- Fixed: Manual build failure when using Bitbucket triggers (#1767)
- Fixed: Missing "Sign Out" link on mobile UI (#1765)
- Fixed: Miscellaneous changes to title usage (#1763)
- Fixed: Repository star appearing when not logged in (#1758)
- Fixed: Invalid AppC manifests generated when missing an ENV (#1753)
- Fixed: Timezones now incorporated into audit logs (#1747)
- Fixed: Fixed redirection to specific tags using short URLs (#1743)
- Fixed: Broken pagination over only public repositories (#1724, #1726, #1730)
- Fixed: Invisible glyph icons on date selectors (#1717)
- Fixed: Possibility storage of duplicate images (#1706)
- Fixed: Broken "Your Account" links in emails (#1694)
- Fixed: Non-admin users no longer default to organization-wide read (#1685)
- Fixed: Database performance (#1680, #1688, #1690, #1722, #1744, #1772)

### v1.16.6

- Added: Ability to override secure cookie setting when using HTTPS protocol (#1712)

### v1.16.5

- Added: Better logging for delete issues in Swift (#1676)
- Added: Storage validation on /status endpoint (#1660)
- Added: Better logging for upload issues (#1639, #1670)
- Added: Support for Swift retries (#1638)
- Added: Support for Swift timeouts (#1634)
- Fixed: Pagination off-by-one issue in repository tags API (#1672)
- Fixed: Missing requires_cors on archived build logs URL (#1673)
- Fixed: Tutorial disconnect UI (#1657)
- Fixed: Enter key in password dialogs in Firefox (#1655)
- Fixed: Custom trigger links in UI (#1652)
- Fixed: GC database query optimizations (#1645, 1662)
- Fixed: Multipart refs on builds (#1651)
- Fixed: Invalid tags on builds (#1648)
- Fixed: Fresh login check failure (#1646)
- Fixed: Support for empty RDN in LDAP configuration (#1644)
- Fixed: Error raised on duplicate placements when replicating (#1633)

### v1.16.4

- Added: Configuration of multiple RDNs for LDAP login (#1601)
- Added: Key Server health check (#1598)
- Added: Promtheus endpoint (#1596)
- Added: Upgrade to latest upstream PyGitHub (#1592)
- Fixed: Race condition around starting builds (#1621)
- Fixed: Geo-replication for CAS objects (#1608)
- Fixed: Popularity metrics on list repositories API endpoint (#1599)
- Fixed: Removed redundant namespaces from repository listings (#1595)
- Fixed: Internal error when paginating a PostgreSQL-backed Quay (#1593, #1622)
- Fixed: GitHub API URLs are properly stripped of trailing slashes (#1590)
- Fixed: Tutorial fails gracefully without Redis (#1587)

### v1.16.3

- Added: Repository Activity Heatmap (#1569, #1571)
- Added: Restyled Robots View (#1568)
- Added: LDAP certificates specified by name (#1549)
- Added: Multiselect toggles for permissions (#1562)
- Added: Dynamically generated sitemap.txt (#1552)
- Fixed: Fixed URLs missing ports in setup process (#1583)
- Fixed: OAuth key not found error when setting up Dex (#1583)
- Fixed: Timestamps in syslog now display the proper time (#1579)
- Fixed: Added offset for clock skew in JWT expiration (#1578)
- Fixed: Replacement of illegal characters in usernames (#1565)
- Fixed: Differentiate between different tags on generated ACIs (#1523)
- Fixed: Decreased lifetime of various redis keys (#1561)
- Fixed: Build pages now robust to redis outage (#1560)
- Fixed: Validation of build arguments before contacting a build worker (#1557)
- Fixed: Removed hosted Quay.io status from Enterprise 500 page (#1548)
- Fixed: Performance of database queries (#1512)

### v1.16.2

- Added: Ability for admins to "Take Ownership" of a namespace (#1526)
- Fixed: Encrypted Password Dialog can use External Auth Usernames (#1541)
- Fixed: Logging race condition in container startup (#1537)
- Fixed: Improved database performance on various pages (#1511, #1514)
- Fixed: The 'Return' key now works in password dialogs (#1533)
- Fixed: Repository descriptions breaking log page styles (#1532)
- Fixed: Styles on Privacy and Terms of Service pages (#1531)

### v1.16.1

- Added: Registry JWT now uses Quay's Service Keys (#1498, #1527)
- Added: Upgrade to Ubuntu 16.04 LTS base image (#1496)
- Added: Storage Replication for Registry v2 images (#1502)
- Added: Better error messaging for build logs (#1500)
- Added: Granting of OAuth tokens for users via xAuth (#1457)
- Added: Random generation of key configuration values (#1485)
- Added: Upgrade to AngularJS v1.5 (#1473)
- Added: Swift API v3 storage support (#1472)
- Added: Clarification on various tool tip dialogs (#1468)
- Added: Various backend performance increases (#1459, #1493, #1510, #950)
- Added: New Credentials, Team, Robot Dialogs (#1421, #1455)
- Fixed: Pagination keys must be url-safe base64 encoded (#1485)
- Fixed: Sign In to work with more password managers (#1508)
- Fixed: Role deletion UI (#1491)
- Fixed: UI expansion when large HTML "pre" tags are used in markdown (#1489)
- Fixed: Usernames not properly linking with external auth providers (#1483)
- Fixed: Display of dates in action logs UI (#1486)
- Fixed: Selection bug with checkboxes in the setup process (#1458)
- Fixed: Display error with Sign In (#1466)
- Fixed: Race condition in ACI generation (#1463, #1490)
- Fixed: Incorrect calculation of the actions log archiver
- Fixed: Displaying many image tracks on the Repository tags page (#1451)
- Fixed: Handling of admin OAuth Scope (#1447)

### v1.16.0

- Added: Unified dashboard for viewing vulnerabilities and packages (#268)
- Added: Expose createOrganization API endpoint (#1246)
- Added: ACI key setup to the setup tool (#1211)
- Added: JWT Key Server (#1332)
- Added: New Login Screen UI (#1346)
- Added: API errors return application/problem+json format (#1361)
- Added: JWT Proxy for authenticating services (#1380)
- Added: New design for user and org settings (#1409)
- Added: Sescan configuration to setup tool (#1428)
- Added: New credentials dialog (#1421)
- Fixed: Remove uses of target="_blank" anchors (#1411)
- Fixed: Bulk operations don't allow "shift selection" (#1389)
- Fixed: Add tag pushed to usage log (#798)
- Fixed: Increase timeout on V2 (#1377)
- Fixed: Save rotated logs to storage via userfiles (#1356)
- Fixed: Include all possible response codes in Swagger document (#1018)
- Fixed: Improve notification lookup performance (#1329)
- Fixed: Future-proof uncompressed size calculation for blob store (#1325)
- Fixed: Client side chunk paths (#1306)
- Fixed: ACI Volume Names (#1308)
- Fixed: Issue when linking to a parent with a different blob (#1291)
- Fixed: Not all 401s set www-authenticate header (#1254)
- Fixed: Key error when updating V1 Ids (#1240)
- Fixed: Unicode error when calculating new V1 IDs (#1239)
- Fixed: Error when turning on receipt emails (#1209)

### v1.15.5

- Fixed: Docker pushes with v2 sha mismatch was breaking v2 functionality (#1236)

### v1.15.4 (Broken)

- Added: Check that will fail if Quay tries to mislink V1 layers with Docker 1.10 (#1228)
- Fixed: Backfill of V2 checksums (#1229)
- Fixed: 'BlobUpload' Migration (2015-12-14) for MySQL 5.5 (#1227)
- Fixed: Minor UI error in tag specific image view (#1222)
- Fixed: Notification logo (#1223)

### v1.15.3

- Added: 502 page (#1198)
- Added: Token based pagination (#1196, #1095)
- Fixed: Trust upstream QE proxies to specify https scheme in X-Forwarded-Proto (#1201)
- Fixed: Refreshed dependencies to address security issues (#1195, #1192, #1186, #1182)
- Fixed: Tests (#1190, #1184)
- Fixed: Setup tool storage engine validation (#1194)

### v1.15.2

- Fixed Content-Type of V2 manifests to match updated Docker V2 spec (#1169)
- Fixed scope handling for Docker 1.8.3 (#1162)
- Fixed typos in docs (#1163, #1164)
- Added formal support for library repositories (#1160)

### v1.15.1

- Fixed swift path computations

### v1.15.0

- Added migration to backfill V2 checksums and torrent SHAs (#1129)
- Fixed migration query (#1140)

### v1.15.0pre

- Fixed UI toggle bug (#1133)
- Fixed bug that displayed billing info in QE (#1124)
- Added support for torrent pulls (#1119, #1126, #1111, #1133, #1134, #1136, #1138)

### v1.14.1

- Fixed migration of V1 metadata (#1120)
- Added list view of repositories in all displays (#1109)
- Removed image diff feature (#1102, #1116)
- Fixed log bug around month handling (#1114)
- Added better recovery of organizations (#1108)
- Fixed Content-Type on errors with JSON bodies (#1107)
- Added QE version in footer
- Fixed unhandled exceptions in Queue
- Improved database query performance (#1068, #1097)
- Fixed UI for dismissing notifications (#1094)
- Added namespaces in `docker search` results (#1086)

### v1.14.0

- Added Docker Registry v2 support (#885)
- Added the ability to blacklist v2 for specific versions (#1065)
- Added HTTP2 support (#1031)
- Added automatic action logs rotation (#618)
- Made garbage collection frequency configurable (#1074)
- Fixed user, repositories and images under MySQL (#830, #843, #1075)
- Added storage preferences configuration (#725, #807)
- Fixed ACI volumes (#1007)
- Fixed date display in Firefox (#937)
- Fixed page titles (#952)
- Added Gitlab, Bitbucket and Github schema support to custom triggers (#525)
- Fixed numerous builder failures

### v1.13.5

- Fixed 404 page advertising registry v2 protocol support (#790)

### v1.13.4

- Fixed incompatibility with Kubernetes 1.1 (#879)

### v1.13.3

- Fixed backfill for migration (#846)

### v1.13.2

- Fixed 404 API calls redirecting to 404 page (#762)

### v1.13.1

- Fixed broken database migration (#759)
- Added OpenGraph preview image (#750, #758)

### v1.13.0

- Added new Red Hat Quay rebranding (#723, #738, #735, #745, #746, #748, #747, #751)
- Added a styled 404 page (#683)
- Hid the run button from users that haven't created a trigger (#727)
- Added timeouts to calls to GitLab, Bitbucket, GitHub APIs (#636, #633, #631, #722)
- Added more fields to responses from user API (#681)
- Fixed bug where every repository appeared private in repository listings (#680)
- Added an error when geo-replication is enabled with local storage (#667)
- Enabled asynchronous garbage collection for all repositories (#665)
- Improved UX uploading Dockerfiles (#656)
- Improved registry resiliancy to missing image sizes (#643)
- Improved Teams UI (#647)
- Added a limit to logs pagination API (#603)
- Upgrade docker search to use the new search system (#595)
- Fixed database hostname validation to include "." and "\" (#579)
- Improved build system's resiliancy if operating without redis (#571)
- Updated repository name and namespace validation to match new docker behavior (#535, #644)
- Refactored and improved Build Trigger validation (#478, #523, #524, #527, #544, #561, #657, #686, #693, #734)
- Optimized moving tags (#520)
- Optimized database usage (#517, #518, #519, #598, #601, #605, #615, #641, #675)
- Migrated all GitHub triggers to use deploy keys (#503)
- Added ability to 'RUN cat .git/HEAD' to get git SHAs in builds (#504)
- Improved repository count limitations UI (#492, #529)
- Added a releases table to database (#495)
- Made repository deletion more robust (#497)
- Optimized Swift storage to support direct downloads (#484)
- Improved build logs UX (#482, #507)
- Add basic Kubernetes secret-store support (#272)
- Improved internal test suite (#470, #511, #526, #514, #545, #570, #572, #573, #583, #711, #728, #730)
- Improved background worker stability (#471)

### v1.12.0

- Added experimental Dex login support (#447, #468)
- Fixed tag pagination in API (#463)
- Improved performance for archiving build logs (#462, #466)
- Optimized cloud storage copying (#460)
- Fixed bug where LDN directory was given a relative domain not absolute (#458)
- Allow robot account names to have underscores (#453)
- Added missing SuperUser aggregate logs endpoint (#449)
- Made JWT validation more strict (#446, #448)
- Added dialog around restarting the container after setup (#441)
- Added selection of Swift API version (#444)
- Improved UX around organization name validation (#437)
- Stopped relying on undocumented behavior for OAuth redirects (#432)
- Hardened against S3 upload failures (#434)
- Added experimental automatic storage replication (#191)
- Deduplicated logging to syslog (#431, #440)
- Added list org member permissions back to API (#429)
- Fixed bug in parsing unicode Dockerfiles (#426)
- Added CloudWatch metrics for multipart uploads (#419)
- Updated CloudWatch metrics to send the max metrics per API call (#412)
- Limited the items auto-loaded from GitHub in trigger setup to 30 (#382)
- Tweaked build UX (#381, #386, #384, #410, #420, #422)
- Changed webhook notifications to also send client SSL certs (#374)
- Improved internal test suite (#381, #374, #388, #455, #457)

### v1.11.2

- Fixed security bug with LDAP login (#376)

### 1.11.1

- Loosened the check for mounted volumes bug (#353)
- Strengthened HTTPS configuration (#329)
- Disabled password change for non-DB auth (#347)
- Added support for custom favicon (#343)
- Fixed tarfile support for non-unicode pax fields (#328)
- Fixed permissions on tag history API requiring READ instead of WRITE tokens (#316)
- Added public access to time machine (#334)
- Added missing JSON schema for 'refs' and 'branch_name' (#330)
- Always create a new connection to Swift (#336)
- Minor UI Fixes (#356, #341, #338, #337)
- Minor trigger fixes (#357, #349)
- Refactored and fixed internal code (#331)

### 1.11.0

- Changed user pages to display public repositories (#321)
- Changed docs to load via HTTPS instead of HTTP (#314)
- Corrected the defaulting of non-existant app configs to the value False (#312)
- Fixed a visual bug in repositories for Chrome Canary users (#307)
- Fixed Swagger v2 support to be 100% spec compliant (#289)
- Added documentation to search (#303)
- Improved internal development experience (#297, #299, #301, #302, #311)
- Improved UI performance for large repositories and their logs (#296, #294, #318, #319)
- Optimized GC and added experimental async GC (#155)
- Updated ACI support to ACI 0.6.1 (#280, #284)
- Fixed HTTP 500 on logout (#282)
- Prevented storage on a non-mounted container volume (#275)
- Fixed fetching repositories from GitHub Enterprise (#277)
- Increased the size of Quay.io hosted build nodes (#234)
- Refactored and fixed internal code (#270, #285, #290, #295, #300, #283, #317)
- Migrated triggers to use Bitbucket's new API (#255, #256)
- Added a throbber for deleting a repository (#269)
- Tweaked numerous UI elements on Repository listing (#268)
- Increased SQL query performance for numerous interactions (#264, #281, #308, #309)

### 1.10.0

- Fixed GitHub API usage to prevent over-listing users' repos (#260)
- Deleted old landing page (#259)
- Corrected mistakes in internal logic (#247, #254, #257)
- Tweaked UI for List View of Repositories Page (#253, #261)
- Added ability to log in with a team invite code (#250)
- Optimized various SQL queries (#249, #252, #258)
- Refactored internal libraries (#245, #246)
- Fixed missing db cert preventing saving configs in super user panel (#244)
- Fixed database status in status endpoint (#242)
- Added a flash message for various interactions (#226)
- Added Keystone (OpenStack auth) support (#197)
- Fixed Logs View in SuperUser panel (#136)

### 1.9.8

- Implemented file streams for Swift storage engine (#214)
- Made script that sets connection limits optional (#208)
- Added warning to tag fetching dialog to use robots with permission (#207)
- Fixed error when deleting of robot accounts used in builds (#205)
- Added encrypted password output in the Superuser API (#203)
- Removed HEAD section from Changelog (#202)
- Improved error messages on pull failure (#201)
- Added pagination support to tag history API (#200)
- Deleted all vendored art files (#199)
- Deleted all code related to the old UI (#195)
- Added ability to configure database SSL cert (#192)
- Fixed JWT to use UTC timestamps (#190)
- Added delegated Superuser API access (#189)
- Fixed JavaScript null pointers & UI tweaks (#188, #224, #217, #224, #233)
- Added messaging when archived build logs fail to load (#187)
- Replaced Container Usage tab in the Superuser Panel with this Changelog (#186)
- Truncated long commit messages in the UI (#185)

### 1.9.7

- Changed etcd timeouts in the ephemeral build manager to be 30s (#183)

### 1.9.6

- Added fix for etcd-related issues with the ephemeral build manager (#181)

### 1.9.5

- Added changelog (#178)
- Updated dependencies (#171, #172)
- Speed up some queries by using UNION instead of JOIN (#170)
- Improved etcd watch logic for ephemeral build system (#168)
- Fixed CSS inconsistencies (#167, #160)
- Removed dependency on user existance checks for auth implementations (#166)
- Fixed issue where noisy build logs caused builds to timeout (#165)
- Added scope descriptions to generate token page (#163)
- Expose robots API via Swagger (#162)
- Improved loading permissions by adding a short circuit (#154)
- Improved coverage of handling builds with revoked OAuth credentials (#153)
- Added ability to do manual builds of tags (#152)
