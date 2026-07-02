# Route Inventory (Exhaustive Static Parse)

## Flask-RESTful Resources (`@resource`)

| File | Class | Path expr | Full path expr | Methods | Feature gates |
|---|---|---|---|---|---|
| `endpoints/api/appspecifictokens.py` | `AppTokens` | `"/v1/user/apptoken"` | `/api/"/v1/user/apptoken"` | `GET,POST` | `features.APP_SPECIFIC_TOKENS` |
| `endpoints/api/appspecifictokens.py` | `AppToken` | `"/v1/user/apptoken/<token_uuid>"` | `/api/"/v1/user/apptoken/<token_uuid>"` | `DELETE,GET` | `features.APP_SPECIFIC_TOKENS` |
| `endpoints/api/billing.py` | `ListPlans` | `"/v1/plans/"` | `/api/"/v1/plans/"` | `GET` | `features.BILLING` |
| `endpoints/api/billing.py` | `UserCard` | `"/v1/user/card"` | `/api/"/v1/user/card"` | `GET,POST` | `features.BILLING` |
| `endpoints/api/billing.py` | `OrganizationCard` | `"/v1/organization/<orgname>/card"` | `/api/"/v1/organization/<orgname>/card"` | `GET,POST` | `features.BILLING` |
| `endpoints/api/billing.py` | `UserPlan` | `"/v1/user/plan"` | `/api/"/v1/user/plan"` | `GET,POST,PUT` | `features.BILLING` |
| `endpoints/api/billing.py` | `OrganizationPlan` | `"/v1/organization/<orgname>/plan"` | `/api/"/v1/organization/<orgname>/plan"` | `GET,POST,PUT` | `features.BILLING` |
| `endpoints/api/billing.py` | `UserInvoiceList` | `"/v1/user/invoices"` | `/api/"/v1/user/invoices"` | `GET` | `features.BILLING` |
| `endpoints/api/billing.py` | `OrganizationInvoiceList` | `"/v1/organization/<orgname>/invoices"` | `/api/"/v1/organization/<orgname>/invoices"` | `GET` | `features.BILLING` |
| `endpoints/api/billing.py` | `UserInvoiceFieldList` | `"/v1/user/invoice/fields"` | `/api/"/v1/user/invoice/fields"` | `GET,POST` | `features.BILLING` |
| `endpoints/api/billing.py` | `UserInvoiceField` | `"/v1/user/invoice/field/<field_uuid>"` | `/api/"/v1/user/invoice/field/<field_uuid>"` | `DELETE` | `features.BILLING` |
| `endpoints/api/billing.py` | `OrganizationInvoiceFieldList` | `"/v1/organization/<orgname>/invoice/fields"` | `/api/"/v1/organization/<orgname>/invoice/fields"` | `GET,POST` | `features.BILLING` |
| `endpoints/api/billing.py` | `OrganizationInvoiceField` | `"/v1/organization/<orgname>/invoice/field/<field_uuid>"` | `/api/"/v1/organization/<orgname>/invoice/field/<field_uuid>"` | `DELETE` | `features.BILLING` |
| `endpoints/api/billing.py` | `OrganizationRhSku` | `"/v1/organization/<orgname>/marketplace"` | `/api/"/v1/organization/<orgname>/marketplace"` | `GET,POST` | `features.BILLING` |
| `endpoints/api/billing.py` | `OrganizationRhSkuBatchRemoval` | `"/v1/organization/<orgname>/marketplace/batchremove"` | `/api/"/v1/organization/<orgname>/marketplace/batchremove"` | `POST` | `features.BILLING` |
| `endpoints/api/billing.py` | `OrganizationRhSkuSubscriptionField` | `"/v1/organization/<orgname>/marketplace/<subscription_id>"` | `/api/"/v1/organization/<orgname>/marketplace/<subscription_id>"` | `DELETE` | `features.BILLING` |
| `endpoints/api/billing.py` | `UserSkuList` | `"/v1/user/marketplace"` | `/api/"/v1/user/marketplace"` | `GET` | `features.RH_MARKETPLACE` |
| `endpoints/api/build.py` | `RepositoryBuildList` | `"/v1/repository/<apirepopath:repository>/build/"` | `/api/"/v1/repository/<apirepopath:repository>/build/"` | `GET,POST` | `` |
| `endpoints/api/build.py` | `RepositoryBuildResource` | `"/v1/repository/<apirepopath:repository>/build/<build_uuid>"` | `/api/"/v1/repository/<apirepopath:repository>/build/<build_uuid>"` | `DELETE,GET` | `` |
| `endpoints/api/build.py` | `RepositoryBuildStatus` | `"/v1/repository/<apirepopath:repository>/build/<build_uuid>/status"` | `/api/"/v1/repository/<apirepopath:repository>/build/<build_uuid>/status"` | `GET` | `` |
| `endpoints/api/build.py` | `RepositoryBuildLogs` | `"/v1/repository/<apirepopath:repository>/build/<build_uuid>/logs"` | `/api/"/v1/repository/<apirepopath:repository>/build/<build_uuid>/logs"` | `GET` | `` |
| `endpoints/api/build.py` | `FileDropResource` | `"/v1/filedrop/"` | `/api/"/v1/filedrop/"` | `POST` | `` |
| `endpoints/api/capabilities.py` | `RegistryCapabilities` | `"/v1/registry/capabilities"` | `/api/"/v1/registry/capabilities"` | `GET` | `` |
| `endpoints/api/discovery.py` | `DiscoveryResource` | `"/v1/discovery"` | `/api/"/v1/discovery"` | `GET` | `` |
| `endpoints/api/error.py` | `Error` | `"/v1/error/<error_type>"` | `/api/"/v1/error/<error_type>"` | `GET` | `` |
| `endpoints/api/globalmessages.py` | `GlobalUserMessages` | `"/v1/messages"` | `/api/"/v1/messages"` | `GET,POST` | `` |
| `endpoints/api/globalmessages.py` | `GlobalUserMessage` | `"/v1/message/<uuid>"` | `/api/"/v1/message/<uuid>"` | `DELETE` | `features.SUPER_USERS` |
| `endpoints/api/immutability_policy.py` | `OrgImmutabilityPolicies` | `"/v1/organization/<orgname>/immutabilitypolicy/"` | `/api/"/v1/organization/<orgname>/immutabilitypolicy/"` | `GET,POST` | `features.IMMUTABLE_TAGS` |
| `endpoints/api/immutability_policy.py` | `OrgImmutabilityPolicy` | `"/v1/organization/<orgname>/immutabilitypolicy/<policy_uuid>"` | `/api/"/v1/organization/<orgname>/immutabilitypolicy/<policy_uuid>"` | `DELETE,GET,PUT` | `features.IMMUTABLE_TAGS` |
| `endpoints/api/immutability_policy.py` | `RepositoryImmutabilityPolicies` | `"/v1/repository/<apirepopath:repository>/immutabilitypolicy/"` | `/api/"/v1/repository/<apirepopath:repository>/immutabilitypolicy/"` | `GET,POST` | `features.IMMUTABLE_TAGS` |
| `endpoints/api/immutability_policy.py` | `RepositoryImmutabilityPolicy` | `"/v1/repository/<apirepopath:repository>/immutabilitypolicy/<policy_uuid>"` | `/api/"/v1/repository/<apirepopath:repository>/immutabilitypolicy/<policy_uuid>"` | `DELETE,GET,PUT` | `features.IMMUTABLE_TAGS` |
| `endpoints/api/logs.py` | `RepositoryLogs` | `"/v1/repository/<apirepopath:repository>/logs"` | `/api/"/v1/repository/<apirepopath:repository>/logs"` | `GET` | `` |
| `endpoints/api/logs.py` | `UserLogs` | `"/v1/user/logs"` | `/api/"/v1/user/logs"` | `GET` | `` |
| `endpoints/api/logs.py` | `OrgLogs` | `"/v1/organization/<orgname>/logs"` | `/api/"/v1/organization/<orgname>/logs"` | `GET` | `` |
| `endpoints/api/logs.py` | `RepositoryAggregateLogs` | `"/v1/repository/<apirepopath:repository>/aggregatelogs"` | `/api/"/v1/repository/<apirepopath:repository>/aggregatelogs"` | `GET` | `features.AGGREGATED_LOG_COUNT_RETRIEVAL` |
| `endpoints/api/logs.py` | `UserAggregateLogs` | `"/v1/user/aggregatelogs"` | `/api/"/v1/user/aggregatelogs"` | `GET` | `features.AGGREGATED_LOG_COUNT_RETRIEVAL` |
| `endpoints/api/logs.py` | `OrgAggregateLogs` | `"/v1/organization/<orgname>/aggregatelogs"` | `/api/"/v1/organization/<orgname>/aggregatelogs"` | `GET` | `features.AGGREGATED_LOG_COUNT_RETRIEVAL` |
| `endpoints/api/logs.py` | `ExportRepositoryLogs` | `"/v1/repository/<apirepopath:repository>/exportlogs"` | `/api/"/v1/repository/<apirepopath:repository>/exportlogs"` | `POST` | `features.LOG_EXPORT` |
| `endpoints/api/logs.py` | `ExportUserLogs` | `"/v1/user/exportlogs"` | `/api/"/v1/user/exportlogs"` | `POST` | `features.LOG_EXPORT` |
| `endpoints/api/logs.py` | `ExportOrgLogs` | `"/v1/organization/<orgname>/exportlogs"` | `/api/"/v1/organization/<orgname>/exportlogs"` | `POST` | `features.LOG_EXPORT` |
| `endpoints/api/manifest.py` | `RepositoryManifest` | `MANIFEST_DIGEST_ROUTE` | `/api/MANIFEST_DIGEST_ROUTE` | `GET` | `` |
| `endpoints/api/manifest.py` | `RepositoryManifestLabels` | `MANIFEST_DIGEST_ROUTE + "/labels"` | `/api/MANIFEST_DIGEST_ROUTE + "/labels"` | `GET,POST` | `` |
| `endpoints/api/manifest.py` | `ManageRepositoryManifestLabel` | `MANIFEST_DIGEST_ROUTE + "/labels/<labelid>"` | `/api/MANIFEST_DIGEST_ROUTE + "/labels/<labelid>"` | `DELETE,GET` | `` |
| `endpoints/api/manifest.py` | `RepositoryManifestPullStatistics` | `'/v1/repository/<apirepopath:repository>/manifest/<regex("{0}"):manifestref>/pull_statistics'.format( digest_tools.DIGEST_PATTERN )` | `/api/'/v1/repository/<apirepopath:repository>/manifest/<regex("{0}"):manifestref>/pull_statistics'.format( digest_tools.DIGEST_PATTERN )` | `GET` | `features.IMAGE_PULL_STATS` |
| `endpoints/api/mirror.py` | `RepoMirrorSyncNowResource` | `"/v1/repository/<apirepopath:repository>/mirror/sync-now"` | `/api/"/v1/repository/<apirepopath:repository>/mirror/sync-now"` | `POST` | `features.REPO_MIRROR` |
| `endpoints/api/mirror.py` | `RepoMirrorSyncCancelResource` | `"/v1/repository/<apirepopath:repository>/mirror/sync-cancel"` | `/api/"/v1/repository/<apirepopath:repository>/mirror/sync-cancel"` | `POST` | `features.REPO_MIRROR` |
| `endpoints/api/mirror.py` | `RepoMirrorResource` | `"/v1/repository/<apirepopath:repository>/mirror"` | `/api/"/v1/repository/<apirepopath:repository>/mirror"` | `GET,POST,PUT` | `features.REPO_MIRROR` |
| `endpoints/api/namespacequota.py` | `OrganizationQuotaList` | `"/v1/organization/<orgname>/quota"` | `/api/"/v1/organization/<orgname>/quota"` | `GET,POST` | `features.SUPER_USERS; features.QUOTA_MANAGEMENT and features.EDIT_QUOTA` |
| `endpoints/api/namespacequota.py` | `OrganizationQuota` | `"/v1/organization/<orgname>/quota/<quota_id>"` | `/api/"/v1/organization/<orgname>/quota/<quota_id>"` | `DELETE,GET,PUT` | `features.SUPER_USERS; features.QUOTA_MANAGEMENT and features.EDIT_QUOTA` |
| `endpoints/api/namespacequota.py` | `OrganizationQuotaLimitList` | `"/v1/organization/<orgname>/quota/<quota_id>/limit"` | `/api/"/v1/organization/<orgname>/quota/<quota_id>/limit"` | `GET,POST` | `features.SUPER_USERS; features.QUOTA_MANAGEMENT and features.EDIT_QUOTA` |
| `endpoints/api/namespacequota.py` | `OrganizationQuotaLimit` | `"/v1/organization/<orgname>/quota/<quota_id>/limit/<limit_id>"` | `/api/"/v1/organization/<orgname>/quota/<quota_id>/limit/<limit_id>"` | `DELETE,GET,PUT` | `features.SUPER_USERS; features.QUOTA_MANAGEMENT and features.EDIT_QUOTA` |
| `endpoints/api/namespacequota.py` | `UserQuotaList` | `"/v1/user/quota"` | `/api/"/v1/user/quota"` | `GET` | `features.SUPER_USERS; features.QUOTA_MANAGEMENT and features.EDIT_QUOTA` |
| `endpoints/api/namespacequota.py` | `UserQuota` | `"/v1/user/quota/<quota_id>"` | `/api/"/v1/user/quota/<quota_id>"` | `GET` | `features.SUPER_USERS; features.QUOTA_MANAGEMENT and features.EDIT_QUOTA` |
| `endpoints/api/namespacequota.py` | `UserQuotaLimitList` | `"/v1/user/quota/<quota_id>/limit"` | `/api/"/v1/user/quota/<quota_id>/limit"` | `GET` | `features.SUPER_USERS; features.QUOTA_MANAGEMENT and features.EDIT_QUOTA` |
| `endpoints/api/namespacequota.py` | `UserQuotaLimit` | `"/v1/user/quota/<quota_id>/limit/<limit_id>"` | `/api/"/v1/user/quota/<quota_id>/limit/<limit_id>"` | `GET` | `features.SUPER_USERS; features.QUOTA_MANAGEMENT and features.EDIT_QUOTA` |
| `endpoints/api/org_mirror.py` | `OrgMirrorConfig` | `"/v1/organization/<orgname>/mirror"` | `/api/"/v1/organization/<orgname>/mirror"` | `DELETE,GET,POST,PUT` | `features.ORG_MIRROR` |
| `endpoints/api/org_mirror.py` | `OrgMirrorSyncNow` | `"/v1/organization/<orgname>/mirror/sync-now"` | `/api/"/v1/organization/<orgname>/mirror/sync-now"` | `POST` | `features.ORG_MIRROR` |
| `endpoints/api/org_mirror.py` | `OrgMirrorSyncCancel` | `"/v1/organization/<orgname>/mirror/sync-cancel"` | `/api/"/v1/organization/<orgname>/mirror/sync-cancel"` | `POST` | `features.ORG_MIRROR` |
| `endpoints/api/org_mirror.py` | `OrgMirrorVerify` | `"/v1/organization/<orgname>/mirror/verify"` | `/api/"/v1/organization/<orgname>/mirror/verify"` | `POST` | `features.ORG_MIRROR` |
| `endpoints/api/org_mirror.py` | `OrgMirrorRepositories` | `"/v1/organization/<orgname>/mirror/repositories"` | `/api/"/v1/organization/<orgname>/mirror/repositories"` | `GET` | `features.ORG_MIRROR` |
| `endpoints/api/organization.py` | `OrganizationList` | `"/v1/organization/"` | `/api/"/v1/organization/"` | `POST` | `` |
| `endpoints/api/organization.py` | `Organization` | `"/v1/organization/<orgname>"` | `/api/"/v1/organization/<orgname>"` | `DELETE,GET,PUT` | `` |
| `endpoints/api/organization.py` | `OrgPrivateRepositories` | `"/v1/organization/<orgname>/private"` | `/api/"/v1/organization/<orgname>/private"` | `GET` | `features.BILLING` |
| `endpoints/api/organization.py` | `OrganizationCollaboratorList` | `"/v1/organization/<orgname>/collaborators"` | `/api/"/v1/organization/<orgname>/collaborators"` | `GET` | `` |
| `endpoints/api/organization.py` | `OrganizationMemberList` | `"/v1/organization/<orgname>/members"` | `/api/"/v1/organization/<orgname>/members"` | `GET` | `` |
| `endpoints/api/organization.py` | `OrganizationMember` | `"/v1/organization/<orgname>/members/<membername>"` | `/api/"/v1/organization/<orgname>/members/<membername>"` | `DELETE,GET` | `` |
| `endpoints/api/organization.py` | `ApplicationInformation` | `"/v1/app/<client_id>"` | `/api/"/v1/app/<client_id>"` | `GET` | `` |
| `endpoints/api/organization.py` | `OrganizationApplications` | `"/v1/organization/<orgname>/applications"` | `/api/"/v1/organization/<orgname>/applications"` | `GET,POST` | `` |
| `endpoints/api/organization.py` | `OrganizationApplicationResource` | `"/v1/organization/<orgname>/applications/<client_id>"` | `/api/"/v1/organization/<orgname>/applications/<client_id>"` | `DELETE,GET,PUT` | `` |
| `endpoints/api/organization.py` | `OrganizationApplicationResetClientSecret` | `"/v1/organization/<orgname>/applications/<client_id>/resetclientsecret"` | `/api/"/v1/organization/<orgname>/applications/<client_id>/resetclientsecret"` | `POST` | `` |
| `endpoints/api/organization.py` | `OrganizationProxyCacheConfig` | `"/v1/organization/<orgname>/proxycache"` | `/api/"/v1/organization/<orgname>/proxycache"` | `DELETE,GET,POST` | `features.PROXY_CACHE` |
| `endpoints/api/organization.py` | `ProxyCacheConfigValidation` | `"/v1/organization/<orgname>/validateproxycache"` | `/api/"/v1/organization/<orgname>/validateproxycache"` | `POST` | `features.PROXY_CACHE` |
| `endpoints/api/permission.py` | `RepositoryTeamPermissionList` | `"/v1/repository/<apirepopath:repository>/permissions/team/"` | `/api/"/v1/repository/<apirepopath:repository>/permissions/team/"` | `GET` | `` |
| `endpoints/api/permission.py` | `RepositoryUserPermissionList` | `"/v1/repository/<apirepopath:repository>/permissions/user/"` | `/api/"/v1/repository/<apirepopath:repository>/permissions/user/"` | `GET` | `` |
| `endpoints/api/permission.py` | `RepositoryUserTransitivePermission` | `"/v1/repository/<apirepopath:repository>/permissions/user/<username>/transitive"` | `/api/"/v1/repository/<apirepopath:repository>/permissions/user/<username>/transitive"` | `GET` | `` |
| `endpoints/api/permission.py` | `RepositoryUserPermission` | `"/v1/repository/<apirepopath:repository>/permissions/user/<username>"` | `/api/"/v1/repository/<apirepopath:repository>/permissions/user/<username>"` | `DELETE,GET,PUT` | `` |
| `endpoints/api/permission.py` | `RepositoryTeamPermission` | `"/v1/repository/<apirepopath:repository>/permissions/team/<teamname>"` | `/api/"/v1/repository/<apirepopath:repository>/permissions/team/<teamname>"` | `DELETE,GET,PUT` | `` |
| `endpoints/api/policy.py` | `OrgAutoPrunePolicies` | `"/v1/organization/<orgname>/autoprunepolicy/"` | `/api/"/v1/organization/<orgname>/autoprunepolicy/"` | `GET,POST` | `features.AUTO_PRUNE` |
| `endpoints/api/policy.py` | `OrgAutoPrunePolicy` | `"/v1/organization/<orgname>/autoprunepolicy/<policy_uuid>"` | `/api/"/v1/organization/<orgname>/autoprunepolicy/<policy_uuid>"` | `DELETE,GET,PUT` | `features.AUTO_PRUNE` |
| `endpoints/api/policy.py` | `RepositoryAutoPrunePolicies` | `"/v1/repository/<apirepopath:repository>/autoprunepolicy/"` | `/api/"/v1/repository/<apirepopath:repository>/autoprunepolicy/"` | `GET,POST` | `features.AUTO_PRUNE` |
| `endpoints/api/policy.py` | `RepositoryAutoPrunePolicy` | `"/v1/repository/<apirepopath:repository>/autoprunepolicy/<policy_uuid>"` | `/api/"/v1/repository/<apirepopath:repository>/autoprunepolicy/<policy_uuid>"` | `DELETE,GET,PUT` | `features.AUTO_PRUNE` |
| `endpoints/api/policy.py` | `UserAutoPrunePolicies` | `"/v1/user/autoprunepolicy/"` | `/api/"/v1/user/autoprunepolicy/"` | `GET,POST` | `features.AUTO_PRUNE` |
| `endpoints/api/policy.py` | `UserAutoPrunePolicy` | `"/v1/user/autoprunepolicy/<policy_uuid>"` | `/api/"/v1/user/autoprunepolicy/<policy_uuid>"` | `DELETE,GET,PUT` | `features.AUTO_PRUNE` |
| `endpoints/api/prototype.py` | `PermissionPrototypeList` | `"/v1/organization/<orgname>/prototypes"` | `/api/"/v1/organization/<orgname>/prototypes"` | `GET,POST` | `` |
| `endpoints/api/prototype.py` | `PermissionPrototype` | `"/v1/organization/<orgname>/prototypes/<prototypeid>"` | `/api/"/v1/organization/<orgname>/prototypes/<prototypeid>"` | `DELETE,PUT` | `` |
| `endpoints/api/repoemail.py` | `RepositoryAuthorizedEmail` | `"/v1/repository/<apirepopath:repository>/authorizedemail/<email>"` | `/api/"/v1/repository/<apirepopath:repository>/authorizedemail/<email>"` | `GET,POST` | `features.MAILING` |
| `endpoints/api/repository.py` | `RepositoryList` | `"/v1/repository"` | `/api/"/v1/repository"` | `GET,POST` | `` |
| `endpoints/api/repository.py` | `Repository` | `"/v1/repository/<apirepopath:repository>"` | `/api/"/v1/repository/<apirepopath:repository>"` | `DELETE,GET,PUT` | `` |
| `endpoints/api/repository.py` | `RepositoryVisibility` | `"/v1/repository/<apirepopath:repository>/changevisibility"` | `/api/"/v1/repository/<apirepopath:repository>/changevisibility"` | `POST` | `` |
| `endpoints/api/repository.py` | `RepositoryTrust` | `"/v1/repository/<apirepopath:repository>/changetrust"` | `/api/"/v1/repository/<apirepopath:repository>/changetrust"` | `POST` | `` |
| `endpoints/api/repository.py` | `RepositoryStateResource` | `"/v1/repository/<apirepopath:repository>/changestate"` | `/api/"/v1/repository/<apirepopath:repository>/changestate"` | `PUT` | `features.REPO_MIRROR` |
| `endpoints/api/repositorynotification.py` | `RepositoryNotificationList` | `"/v1/repository/<apirepopath:repository>/notification/"` | `/api/"/v1/repository/<apirepopath:repository>/notification/"` | `GET,POST` | `` |
| `endpoints/api/repositorynotification.py` | `RepositoryNotification` | `"/v1/repository/<apirepopath:repository>/notification/<uuid>"` | `/api/"/v1/repository/<apirepopath:repository>/notification/<uuid>"` | `DELETE,GET,POST` | `` |
| `endpoints/api/repositorynotification.py` | `TestRepositoryNotification` | `"/v1/repository/<apirepopath:repository>/notification/<uuid>/test"` | `/api/"/v1/repository/<apirepopath:repository>/notification/<uuid>/test"` | `POST` | `` |
| `endpoints/api/repotoken.py` | `RepositoryTokenList` | `"/v1/repository/<apirepopath:repository>/tokens/"` | `/api/"/v1/repository/<apirepopath:repository>/tokens/"` | `GET,POST` | `` |
| `endpoints/api/repotoken.py` | `RepositoryToken` | `"/v1/repository/<apirepopath:repository>/tokens/<code>"` | `/api/"/v1/repository/<apirepopath:repository>/tokens/<code>"` | `DELETE,GET,PUT` | `` |
| `endpoints/api/robot.py` | `UserRobotList` | `"/v1/user/robots"` | `/api/"/v1/user/robots"` | `GET` | `` |
| `endpoints/api/robot.py` | `UserRobot` | `"/v1/user/robots/<robot_shortname>"` | `/api/"/v1/user/robots/<robot_shortname>"` | `DELETE,GET,PUT` | `` |
| `endpoints/api/robot.py` | `OrgRobotList` | `"/v1/organization/<orgname>/robots"` | `/api/"/v1/organization/<orgname>/robots"` | `GET` | `` |
| `endpoints/api/robot.py` | `OrgRobot` | `"/v1/organization/<orgname>/robots/<robot_shortname>"` | `/api/"/v1/organization/<orgname>/robots/<robot_shortname>"` | `DELETE,GET,PUT` | `` |
| `endpoints/api/robot.py` | `UserRobotPermissions` | `"/v1/user/robots/<robot_shortname>/permissions"` | `/api/"/v1/user/robots/<robot_shortname>/permissions"` | `GET` | `` |
| `endpoints/api/robot.py` | `OrgRobotPermissions` | `"/v1/organization/<orgname>/robots/<robot_shortname>/permissions"` | `/api/"/v1/organization/<orgname>/robots/<robot_shortname>/permissions"` | `GET` | `` |
| `endpoints/api/robot.py` | `RegenerateUserRobot` | `"/v1/user/robots/<robot_shortname>/regenerate"` | `/api/"/v1/user/robots/<robot_shortname>/regenerate"` | `POST` | `` |
| `endpoints/api/robot.py` | `RegenerateOrgRobot` | `"/v1/organization/<orgname>/robots/<robot_shortname>/regenerate"` | `/api/"/v1/organization/<orgname>/robots/<robot_shortname>/regenerate"` | `POST` | `` |
| `endpoints/api/robot.py` | `OrgRobotFederation` | `"/v1/organization/<orgname>/robots/<robot_shortname>/federation"` | `/api/"/v1/organization/<orgname>/robots/<robot_shortname>/federation"` | `DELETE,GET,POST` | `` |
| `endpoints/api/search.py` | `LinkExternalEntity` | `"/v1/entities/link/<username>"` | `/api/"/v1/entities/link/<username>"` | `POST` | `` |
| `endpoints/api/search.py` | `EntitySearch` | `"/v1/entities/<prefix>"` | `/api/"/v1/entities/<prefix>"` | `GET` | `` |
| `endpoints/api/search.py` | `ConductSearch` | `"/v1/find/all"` | `/api/"/v1/find/all"` | `GET` | `` |
| `endpoints/api/search.py` | `ConductRepositorySearch` | `"/v1/find/repositories"` | `/api/"/v1/find/repositories"` | `GET` | `` |
| `endpoints/api/secscan.py` | `RepositoryManifestSecurity` | `MANIFEST_DIGEST_ROUTE + "/security"` | `/api/MANIFEST_DIGEST_ROUTE + "/security"` | `GET` | `features.SECURITY_SCANNER` |
| `endpoints/api/signing.py` | `RepositorySignatures` | `"/v1/repository/<apirepopath:repository>/signatures"` | `/api/"/v1/repository/<apirepopath:repository>/signatures"` | `GET` | `features.SIGNING` |
| `endpoints/api/suconfig.py` | `SuperUserRegistryStatus` | `"/v1/superuser/registrystatus"` | `/api/"/v1/superuser/registrystatus"` | `GET` | `features.SUPER_USERS` |
| `endpoints/api/suconfig.py` | `SuperUserShutdown` | `"/v1/superuser/shutdown"` | `/api/"/v1/superuser/shutdown"` | `POST` | `features.SUPER_USERS` |
| `endpoints/api/superuser.py` | `SuperUserAggregateLogs` | `"/v1/superuser/aggregatelogs"` | `/api/"/v1/superuser/aggregatelogs"` | `GET` | `features.SUPER_USERS` |
| `endpoints/api/superuser.py` | `SuperUserLogs` | `"/v1/superuser/logs"` | `/api/"/v1/superuser/logs"` | `GET` | `features.SUPER_USERS` |
| `endpoints/api/superuser.py` | `ChangeLog` | `"/v1/superuser/changelog/"` | `/api/"/v1/superuser/changelog/"` | `GET` | `features.SUPER_USERS` |
| `endpoints/api/superuser.py` | `SuperUserOrganizationList` | `"/v1/superuser/organizations/"` | `/api/"/v1/superuser/organizations/"` | `GET` | `features.SUPER_USERS` |
| `endpoints/api/superuser.py` | `SuperUserRegistrySize` | `"/v1/superuser/registrysize/"` | `/api/"/v1/superuser/registrysize/"` | `GET,POST` | `features.SUPER_USERS` |
| `endpoints/api/superuser.py` | `SuperUserUserQuotaList` | `"/v1/superuser/users/<namespace>/quota"` | `/api/"/v1/superuser/users/<namespace>/quota"` | `GET,POST` | `features.SUPER_USERS; features.QUOTA_MANAGEMENT and features.EDIT_QUOTA` |
| `endpoints/api/superuser.py` | `SuperUserUserQuotaList` | `"/v1/superuser/organization/<namespace>/quota"` | `/api/"/v1/superuser/organization/<namespace>/quota"` | `GET,POST` | `features.SUPER_USERS; features.QUOTA_MANAGEMENT and features.EDIT_QUOTA` |
| `endpoints/api/superuser.py` | `SuperUserUserQuota` | `"/v1/superuser/users/<namespace>/quota/<quota_id>"` | `/api/"/v1/superuser/users/<namespace>/quota/<quota_id>"` | `DELETE,PUT` | `features.SUPER_USERS; features.QUOTA_MANAGEMENT and features.EDIT_QUOTA` |
| `endpoints/api/superuser.py` | `SuperUserUserQuota` | `"/v1/superuser/organization/<namespace>/quota/<quota_id>"` | `/api/"/v1/superuser/organization/<namespace>/quota/<quota_id>"` | `DELETE,PUT` | `features.SUPER_USERS; features.QUOTA_MANAGEMENT and features.EDIT_QUOTA` |
| `endpoints/api/superuser.py` | `SuperUserList` | `"/v1/superuser/users/"` | `/api/"/v1/superuser/users/"` | `GET,POST` | `features.SUPER_USERS` |
| `endpoints/api/superuser.py` | `SuperUserSendRecoveryEmail` | `"/v1/superusers/users/<username>/sendrecovery"` | `/api/"/v1/superusers/users/<username>/sendrecovery"` | `POST` | `features.SUPER_USERS; features.MAILING` |
| `endpoints/api/superuser.py` | `SuperUserManagement` | `"/v1/superuser/users/<username>"` | `/api/"/v1/superuser/users/<username>"` | `DELETE,GET,PUT` | `features.SUPER_USERS` |
| `endpoints/api/superuser.py` | `SuperUserTakeOwnership` | `"/v1/superuser/takeownership/<namespace>"` | `/api/"/v1/superuser/takeownership/<namespace>"` | `POST` | `features.SUPER_USERS` |
| `endpoints/api/superuser.py` | `SuperUserOrganizationManagement` | `"/v1/superuser/organizations/<name>"` | `/api/"/v1/superuser/organizations/<name>"` | `DELETE,PUT` | `features.SUPER_USERS` |
| `endpoints/api/superuser.py` | `SuperUserServiceKeyManagement` | `"/v1/superuser/keys"` | `/api/"/v1/superuser/keys"` | `GET,POST` | `features.SUPER_USERS` |
| `endpoints/api/superuser.py` | `SuperUserServiceKey` | `"/v1/superuser/keys/<kid>"` | `/api/"/v1/superuser/keys/<kid>"` | `DELETE,GET,PUT` | `features.SUPER_USERS` |
| `endpoints/api/superuser.py` | `SuperUserServiceKeyApproval` | `"/v1/superuser/approvedkeys/<kid>"` | `/api/"/v1/superuser/approvedkeys/<kid>"` | `POST` | `features.SUPER_USERS` |
| `endpoints/api/superuser.py` | `SuperUserAppTokens` | `"/v1/superuser/apptokens"` | `/api/"/v1/superuser/apptokens"` | `GET` | `features.APP_SPECIFIC_TOKENS; features.SUPER_USERS` |
| `endpoints/api/superuser.py` | `SuperUserRepositoryBuildLogs` | `"/v1/superuser/<build_uuid>/logs"` | `/api/"/v1/superuser/<build_uuid>/logs"` | `GET` | `features.SUPER_USERS` |
| `endpoints/api/superuser.py` | `SuperUserRepositoryBuildStatus` | `"/v1/superuser/<build_uuid>/status"` | `/api/"/v1/superuser/<build_uuid>/status"` | `GET` | `features.SUPER_USERS` |
| `endpoints/api/superuser.py` | `SuperUserRepositoryBuildResource` | `"/v1/superuser/<build_uuid>/build"` | `/api/"/v1/superuser/<build_uuid>/build"` | `GET` | `features.SUPER_USERS` |
| `endpoints/api/superuser.py` | `SuperUserDumpConfig` | `"/v1/superuser/config"` | `/api/"/v1/superuser/config"` | `GET` | `features.SUPER_USERS` |
| `endpoints/api/tag.py` | `ListRepositoryTags` | `"/v1/repository/<apirepopath:repository>/tag/"` | `/api/"/v1/repository/<apirepopath:repository>/tag/"` | `GET` | `` |
| `endpoints/api/tag.py` | `RepositoryTag` | `"/v1/repository/<apirepopath:repository>/tag/<tag>"` | `/api/"/v1/repository/<apirepopath:repository>/tag/<tag>"` | `DELETE,PUT` | `` |
| `endpoints/api/tag.py` | `RestoreTag` | `"/v1/repository/<apirepopath:repository>/tag/<tag>/restore"` | `/api/"/v1/repository/<apirepopath:repository>/tag/<tag>/restore"` | `POST` | `` |
| `endpoints/api/tag.py` | `TagTimeMachineDelete` | `"/v1/repository/<apirepopath:repository>/tag/<tag>/expire"` | `/api/"/v1/repository/<apirepopath:repository>/tag/<tag>/expire"` | `POST` | `app.config.get("PERMANENTLY_DELETE_TAGS", True)` |
| `endpoints/api/tag.py` | `RepositoryTagPullStatistics` | `"/v1/repository/<apirepopath:repository>/tag/<tag>/pull_statistics"` | `/api/"/v1/repository/<apirepopath:repository>/tag/<tag>/pull_statistics"` | `GET` | `features.IMAGE_PULL_STATS` |
| `endpoints/api/team.py` | `OrganizationTeam` | `"/v1/organization/<orgname>/team/<teamname>"` | `/api/"/v1/organization/<orgname>/team/<teamname>"` | `DELETE,PUT` | `` |
| `endpoints/api/team.py` | `OrganizationTeamSyncing` | `"/v1/organization/<orgname>/team/<teamname>/syncing"` | `/api/"/v1/organization/<orgname>/team/<teamname>/syncing"` | `DELETE,POST` | `features.TEAM_SYNCING` |
| `endpoints/api/team.py` | `TeamMemberList` | `"/v1/organization/<orgname>/team/<teamname>/members"` | `/api/"/v1/organization/<orgname>/team/<teamname>/members"` | `GET` | `` |
| `endpoints/api/team.py` | `TeamMember` | `"/v1/organization/<orgname>/team/<teamname>/members/<membername>"` | `/api/"/v1/organization/<orgname>/team/<teamname>/members/<membername>"` | `DELETE,PUT` | `` |
| `endpoints/api/team.py` | `InviteTeamMember` | `"/v1/organization/<orgname>/team/<teamname>/invite/<email>"` | `/api/"/v1/organization/<orgname>/team/<teamname>/invite/<email>"` | `DELETE,PUT` | `features.MAILING` |
| `endpoints/api/team.py` | `TeamPermissions` | `"/v1/organization/<orgname>/team/<teamname>/permissions"` | `/api/"/v1/organization/<orgname>/team/<teamname>/permissions"` | `GET` | `` |
| `endpoints/api/team.py` | `TeamMemberInvite` | `"/v1/teaminvite/<code>"` | `/api/"/v1/teaminvite/<code>"` | `DELETE,PUT` | `features.MAILING` |
| `endpoints/api/trigger.py` | `BuildTriggerList` | `"/v1/repository/<apirepopath:repository>/trigger/"` | `/api/"/v1/repository/<apirepopath:repository>/trigger/"` | `GET` | `` |
| `endpoints/api/trigger.py` | `BuildTrigger` | `"/v1/repository/<apirepopath:repository>/trigger/<trigger_uuid>"` | `/api/"/v1/repository/<apirepopath:repository>/trigger/<trigger_uuid>"` | `DELETE,GET,PUT` | `` |
| `endpoints/api/trigger.py` | `BuildTriggerSubdirs` | `"/v1/repository/<apirepopath:repository>/trigger/<trigger_uuid>/subdir"` | `/api/"/v1/repository/<apirepopath:repository>/trigger/<trigger_uuid>/subdir"` | `POST` | `` |
| `endpoints/api/trigger.py` | `BuildTriggerActivate` | `"/v1/repository/<apirepopath:repository>/trigger/<trigger_uuid>/activate"` | `/api/"/v1/repository/<apirepopath:repository>/trigger/<trigger_uuid>/activate"` | `POST` | `` |
| `endpoints/api/trigger.py` | `BuildTriggerAnalyze` | `"/v1/repository/<apirepopath:repository>/trigger/<trigger_uuid>/analyze"` | `/api/"/v1/repository/<apirepopath:repository>/trigger/<trigger_uuid>/analyze"` | `POST` | `` |
| `endpoints/api/trigger.py` | `ActivateBuildTrigger` | `"/v1/repository/<apirepopath:repository>/trigger/<trigger_uuid>/start"` | `/api/"/v1/repository/<apirepopath:repository>/trigger/<trigger_uuid>/start"` | `POST` | `` |
| `endpoints/api/trigger.py` | `TriggerBuildList` | `"/v1/repository/<apirepopath:repository>/trigger/<trigger_uuid>/builds"` | `/api/"/v1/repository/<apirepopath:repository>/trigger/<trigger_uuid>/builds"` | `GET` | `` |
| `endpoints/api/trigger.py` | `BuildTriggerFieldValues` | `"/v1/repository/<apirepopath:repository>/trigger/<trigger_uuid>/fields/<field_name>"` | `/api/"/v1/repository/<apirepopath:repository>/trigger/<trigger_uuid>/fields/<field_name>"` | `POST` | `` |
| `endpoints/api/trigger.py` | `BuildTriggerSources` | `"/v1/repository/<apirepopath:repository>/trigger/<trigger_uuid>/sources"` | `/api/"/v1/repository/<apirepopath:repository>/trigger/<trigger_uuid>/sources"` | `POST` | `` |
| `endpoints/api/trigger.py` | `BuildTriggerSourceNamespaces` | `"/v1/repository/<apirepopath:repository>/trigger/<trigger_uuid>/namespaces"` | `/api/"/v1/repository/<apirepopath:repository>/trigger/<trigger_uuid>/namespaces"` | `GET` | `` |
| `endpoints/api/user.py` | `User` | `"/v1/user/"` | `/api/"/v1/user/"` | `DELETE,GET,POST,PUT` | `` |
| `endpoints/api/user.py` | `PrivateRepositories` | `"/v1/user/private"` | `/api/"/v1/user/private"` | `GET` | `features.BILLING` |
| `endpoints/api/user.py` | `ClientKey` | `"/v1/user/clientkey"` | `/api/"/v1/user/clientkey"` | `POST` | `` |
| `endpoints/api/user.py` | `ConvertToOrganization` | `"/v1/user/convert"` | `/api/"/v1/user/convert"` | `POST` | `app.config["AUTHENTICATION_TYPE"] == "Database"` |
| `endpoints/api/user.py` | `Signin` | `"/v1/signin"` | `/api/"/v1/signin"` | `POST` | `features.DIRECT_LOGIN` |
| `endpoints/api/user.py` | `VerifyUser` | `"/v1/signin/verify"` | `/api/"/v1/signin/verify"` | `POST` | `` |
| `endpoints/api/user.py` | `Signout` | `"/v1/signout"` | `/api/"/v1/signout"` | `POST` | `` |
| `endpoints/api/user.py` | `ExternalLoginInformation` | `"/v1/externallogin/<service_id>"` | `/api/"/v1/externallogin/<service_id>"` | `POST` | `` |
| `endpoints/api/user.py` | `DetachExternal` | `"/v1/detachexternal/<service_id>"` | `/api/"/v1/detachexternal/<service_id>"` | `POST` | `features.DIRECT_LOGIN` |
| `endpoints/api/user.py` | `Recovery` | `"/v1/recovery"` | `/api/"/v1/recovery"` | `POST` | `features.MAILING` |
| `endpoints/api/user.py` | `UserNotificationList` | `"/v1/user/notifications"` | `/api/"/v1/user/notifications"` | `GET` | `` |
| `endpoints/api/user.py` | `UserNotification` | `"/v1/user/notifications/<uuid>"` | `/api/"/v1/user/notifications/<uuid>"` | `GET,PUT` | `` |
| `endpoints/api/user.py` | `UserAuthorizationList` | `"/v1/user/authorizations"` | `/api/"/v1/user/authorizations"` | `GET` | `` |
| `endpoints/api/user.py` | `UserAuthorization` | `"/v1/user/authorizations/<access_token_uuid>"` | `/api/"/v1/user/authorizations/<access_token_uuid>"` | `DELETE,GET` | `` |
| `endpoints/api/user.py` | `UserAssignedAuthorizations` | `"/v1/user/assignedauthorization"` | `/api/"/v1/user/assignedauthorization"` | `GET` | `features.ASSIGN_OAUTH_TOKEN` |
| `endpoints/api/user.py` | `UserAssignedAuthorization` | `"/v1/user/assignedauthorization/<assigned_authorization_uuid>"` | `/api/"/v1/user/assignedauthorization/<assigned_authorization_uuid>"` | `DELETE` | `features.ASSIGN_OAUTH_TOKEN` |
| `endpoints/api/user.py` | `StarredRepositoryList` | `"/v1/user/starred"` | `/api/"/v1/user/starred"` | `GET,POST` | `` |
| `endpoints/api/user.py` | `StarredRepository` | `"/v1/user/starred/<apirepopath:repository>"` | `/api/"/v1/user/starred/<apirepopath:repository>"` | `DELETE` | `` |
| `endpoints/api/user.py` | `Users` | `"/v1/users/<username>"` | `/api/"/v1/users/<username>"` | `GET` | `` |

## Blueprint Routes (`@<bp>.route`)

| File | Function | Blueprint | Prefix | Path expr | Full path expr | Methods | Feature gates |
|---|---|---|---|---|---|---|---|
| `endpoints/bitbuckettrigger.py` | `attach_bitbucket_build_trigger` | `bitbuckettrigger` | `/oauth1` | `"/bitbucket/callback/trigger/<trigger_uuid>"` | `/oauth1"/bitbucket/callback/trigger/<trigger_uuid>"` | `GET` | `features.BITBUCKET_BUILD` |
| `endpoints/githubtrigger.py` | `attach_github_build_trigger` | `githubtrigger` | `/oauth2` | `"/github/callback/trigger/<repopath:repository>"` | `/oauth2"/github/callback/trigger/<repopath:repository>"` | `GET` | `features.GITHUB_BUILD` |
| `endpoints/gitlabtrigger.py` | `attach_gitlab_build_trigger` | `gitlabtrigger` | `/oauth2` | `"/gitlab/callback/trigger"` | `/oauth2"/gitlab/callback/trigger"` | `GET` | `features.GITLAB_BUILD` |
| `endpoints/keyserver/__init__.py` | `list_service_keys` | `key_server` | `/keys` | `"/services/<service>/keys"` | `/keys"/services/<service>/keys"` | `GET` | `` |
| `endpoints/keyserver/__init__.py` | `get_service_key` | `key_server` | `/keys` | `"/services/<service>/keys/<kid>"` | `/keys"/services/<service>/keys/<kid>"` | `GET` | `` |
| `endpoints/keyserver/__init__.py` | `put_service_key` | `key_server` | `/keys` | `"/services/<service>/keys/<kid>"` | `/keys"/services/<service>/keys/<kid>"` | `PUT` | `` |
| `endpoints/keyserver/__init__.py` | `delete_service_key` | `key_server` | `/keys` | `"/services/<service>/keys/<kid>"` | `/keys"/services/<service>/keys/<kid>"` | `DELETE` | `` |
| `endpoints/oauth/robot_identity_federation.py` | `auth_federated_robot_identity` | `federation_bp` | `/oauth2` | `"/federation/robot/token"` | `/oauth2"/federation/robot/token"` | `GET` | `` |
| `endpoints/realtime.py` | `user_test` | `realtime` | `/realtime` | `"/user/test"` | `/realtime"/user/test"` | `GET` | `` |
| `endpoints/realtime.py` | `user_subscribe` | `realtime` | `/realtime` | `"/user/subscribe"` | `/realtime"/user/subscribe"` | `GET` | `` |
| `endpoints/secscan.py` | `internal_ping` | `secscan` | `/secscan` | `"/_internal_ping"` | `/secscan"/_internal_ping"` | `GET` | `` |
| `endpoints/secscan.py` | `secscan_notification` | `secscan` | `/secscan` | `"/notification"` | `/secscan"/notification"` | `POST` | `features.SECURITY_SCANNER; features.SECURITY_NOTIFICATIONS` |
| `endpoints/secscan.py` | `manifest_security_backfill_status` | `secscan` | `/secscan` | `"/_backfill_status"` | `/secscan"/_backfill_status"` | `GET` | `` |
| `endpoints/v1/__init__.py` | `internal_ping` | `v1_bp` | `/v1` | `"/_internal_ping"` | `/v1"/_internal_ping"` | `GET` | `` |
| `endpoints/v1/__init__.py` | `ping` | `v1_bp` | `/v1` | `"/_ping"` | `/v1"/_ping"` | `GET` | `` |
| `endpoints/v1/index.py` | `create_user` | `v1_bp` | `/v1` | `"/users"` | `/v1"/users"` | `POST` | `` |
| `endpoints/v1/index.py` | `create_user` | `v1_bp` | `/v1` | `"/users/"` | `/v1"/users/"` | `POST` | `` |
| `endpoints/v1/index.py` | `get_user` | `v1_bp` | `/v1` | `"/users"` | `/v1"/users"` | `GET` | `` |
| `endpoints/v1/index.py` | `get_user` | `v1_bp` | `/v1` | `"/users/"` | `/v1"/users/"` | `GET` | `` |
| `endpoints/v1/index.py` | `update_user` | `v1_bp` | `/v1` | `"/users/<username>/"` | `/v1"/users/<username>/"` | `PUT` | `` |
| `endpoints/v1/index.py` | `create_repository` | `v1_bp` | `/v1` | `"/repositories/<v1createrepopath:repository>/"` | `/v1"/repositories/<v1createrepopath:repository>/"` | `PUT` | `` |
| `endpoints/v1/index.py` | `update_images` | `v1_bp` | `/v1` | `"/repositories/<repopath:repository>/images"` | `/v1"/repositories/<repopath:repository>/images"` | `PUT` | `` |
| `endpoints/v1/index.py` | `get_repository_images` | `v1_bp` | `/v1` | `"/repositories/<repopath:repository>/images"` | `/v1"/repositories/<repopath:repository>/images"` | `GET` | `` |
| `endpoints/v1/index.py` | `delete_repository_images` | `v1_bp` | `/v1` | `"/repositories/<repopath:repository>/images"` | `/v1"/repositories/<repopath:repository>/images"` | `DELETE` | `` |
| `endpoints/v1/index.py` | `put_repository_auth` | `v1_bp` | `/v1` | `"/repositories/<repopath:repository>/auth"` | `/v1"/repositories/<repopath:repository>/auth"` | `PUT` | `` |
| `endpoints/v1/index.py` | `get_search` | `v1_bp` | `/v1` | `"/search"` | `/v1"/search"` | `GET` | `` |
| `endpoints/v1/registry.py` | `head_image_layer` | `v1_bp` | `/v1` | `"/images/<image_id>/layer"` | `/v1"/images/<image_id>/layer"` | `HEAD` | `` |
| `endpoints/v1/registry.py` | `get_image_layer` | `v1_bp` | `/v1` | `"/images/<image_id>/layer"` | `/v1"/images/<image_id>/layer"` | `GET` | `` |
| `endpoints/v1/registry.py` | `put_image_layer` | `v1_bp` | `/v1` | `"/images/<image_id>/layer"` | `/v1"/images/<image_id>/layer"` | `PUT` | `` |
| `endpoints/v1/registry.py` | `put_image_checksum` | `v1_bp` | `/v1` | `"/images/<image_id>/checksum"` | `/v1"/images/<image_id>/checksum"` | `PUT` | `` |
| `endpoints/v1/registry.py` | `get_image_json` | `v1_bp` | `/v1` | `"/images/<image_id>/json"` | `/v1"/images/<image_id>/json"` | `GET` | `` |
| `endpoints/v1/registry.py` | `get_image_ancestry` | `v1_bp` | `/v1` | `"/images/<image_id>/ancestry"` | `/v1"/images/<image_id>/ancestry"` | `GET` | `` |
| `endpoints/v1/registry.py` | `put_image_json` | `v1_bp` | `/v1` | `"/images/<image_id>/json"` | `/v1"/images/<image_id>/json"` | `PUT` | `` |
| `endpoints/v1/tag.py` | `get_tags` | `v1_bp` | `/v1` | `"/repositories/<repopath:repository>/tags"` | `/v1"/repositories/<repopath:repository>/tags"` | `GET` | `` |
| `endpoints/v1/tag.py` | `get_tag` | `v1_bp` | `/v1` | `"/repositories/<repopath:repository>/tags/<tag>"` | `/v1"/repositories/<repopath:repository>/tags/<tag>"` | `GET` | `` |
| `endpoints/v1/tag.py` | `put_tag` | `v1_bp` | `/v1` | `"/repositories/<repopath:repository>/tags/<tag>"` | `/v1"/repositories/<repopath:repository>/tags/<tag>"` | `PUT` | `` |
| `endpoints/v1/tag.py` | `delete_tag` | `v1_bp` | `/v1` | `"/repositories/<repopath:repository>/tags/<tag>"` | `/v1"/repositories/<repopath:repository>/tags/<tag>"` | `DELETE` | `` |
| `endpoints/v2/__init__.py` | `v2_support_enabled` | `v2_bp` | `/v2` | `"/"` | `/v2"/"` | `GET` | `features.ADVERTISE_V2` |
| `endpoints/v2/blob.py` | `check_blob_exists` | `v2_bp` | `/v2` | `BLOB_DIGEST_ROUTE` | `/v2/BLOB_DIGEST_ROUTE` | `HEAD` | `` |
| `endpoints/v2/blob.py` | `download_blob` | `v2_bp` | `/v2` | `BLOB_DIGEST_ROUTE` | `/v2/BLOB_DIGEST_ROUTE` | `GET` | `` |
| `endpoints/v2/blob.py` | `start_blob_upload` | `v2_bp` | `/v2` | `"/<repopath:repository>/blobs/uploads/"` | `/v2"/<repopath:repository>/blobs/uploads/"` | `POST` | `` |
| `endpoints/v2/blob.py` | `fetch_existing_upload` | `v2_bp` | `/v2` | `"/<repopath:repository>/blobs/uploads/<upload_uuid>"` | `/v2"/<repopath:repository>/blobs/uploads/<upload_uuid>"` | `GET` | `` |
| `endpoints/v2/blob.py` | `upload_chunk` | `v2_bp` | `/v2` | `"/<repopath:repository>/blobs/uploads/<upload_uuid>"` | `/v2"/<repopath:repository>/blobs/uploads/<upload_uuid>"` | `PATCH` | `` |
| `endpoints/v2/blob.py` | `monolithic_upload_or_last_chunk` | `v2_bp` | `/v2` | `"/<repopath:repository>/blobs/uploads/<upload_uuid>"` | `/v2"/<repopath:repository>/blobs/uploads/<upload_uuid>"` | `PUT` | `` |
| `endpoints/v2/blob.py` | `cancel_upload` | `v2_bp` | `/v2` | `"/<repopath:repository>/blobs/uploads/<upload_uuid>"` | `/v2"/<repopath:repository>/blobs/uploads/<upload_uuid>"` | `DELETE` | `` |
| `endpoints/v2/blob.py` | `delete_digest` | `v2_bp` | `/v2` | `"/<repopath:repository>/blobs/<digest>"` | `/v2"/<repopath:repository>/blobs/<digest>"` | `DELETE` | `` |
| `endpoints/v2/catalog.py` | `catalog_search` | `v2_bp` | `/v2` | `"/_catalog"` | `/v2"/_catalog"` | `GET` | `` |
| `endpoints/v2/manifest.py` | `fetch_manifest_by_tagname` | `v2_bp` | `/v2` | `MANIFEST_TAGNAME_ROUTE` | `/v2/MANIFEST_TAGNAME_ROUTE` | `GET` | `` |
| `endpoints/v2/manifest.py` | `fetch_manifest_by_digest` | `v2_bp` | `/v2` | `MANIFEST_DIGEST_ROUTE` | `/v2/MANIFEST_DIGEST_ROUTE` | `GET` | `` |
| `endpoints/v2/manifest.py` | `write_manifest_by_tagname` | `v2_bp` | `/v2` | `MANIFEST_TAGNAME_ROUTE` | `/v2/MANIFEST_TAGNAME_ROUTE` | `PUT` | `` |
| `endpoints/v2/manifest.py` | `write_manifest_by_digest` | `v2_bp` | `/v2` | `MANIFEST_DIGEST_ROUTE` | `/v2/MANIFEST_DIGEST_ROUTE` | `PUT` | `` |
| `endpoints/v2/manifest.py` | `delete_manifest_by_digest` | `v2_bp` | `/v2` | `MANIFEST_DIGEST_ROUTE` | `/v2/MANIFEST_DIGEST_ROUTE` | `DELETE` | `` |
| `endpoints/v2/manifest.py` | `delete_manifest_by_tag` | `v2_bp` | `/v2` | `MANIFEST_TAGNAME_ROUTE` | `/v2/MANIFEST_TAGNAME_ROUTE` | `DELETE` | `` |
| `endpoints/v2/referrers.py` | `list_manifest_referrers` | `v2_bp` | `/v2` | `MANIFEST_REFERRERS_ROUTE` | `/v2/MANIFEST_REFERRERS_ROUTE` | `GET` | `features.REFERRERS_API` |
| `endpoints/v2/tag.py` | `list_all_tags` | `v2_bp` | `/v2` | `"/<repopath:repository>/tags/list"` | `/v2"/<repopath:repository>/tags/list"` | `GET` | `` |
| `endpoints/v2/v2auth.py` | `generate_registry_jwt` | `v2_bp` | `/v2` | `"/auth"` | `/v2"/auth"` | `GET` | `` |
| `endpoints/web.py` | `index` | `web` | `` | `"/"` | `"/"` | `GET` | `` |
| `endpoints/web.py` | `internal_ping` | `web` | `` | `"/_internal_ping"` | `"/_internal_ping"` | `GET` | `` |
| `endpoints/web.py` | `internal_error_display` | `web` | `` | `"/500"` | `"/500"` | `GET` | `` |
| `endpoints/web.py` | `not_found_error_display` | `web` | `` | `"/404"` | `"/404"` | `GET` | `` |
| `endpoints/web.py` | `opensearch` | `web` | `` | `"/opensearch.xml"` | `"/opensearch.xml"` | `GET` | `` |
| `endpoints/web.py` | `org_view` | `web` | `` | `"/organization/<path:path>"` | `"/organization/<path:path>"` | `GET` | `` |
| `endpoints/web.py` | `org_view` | `web` | `` | `"/organization/<path:path>/"` | `"/organization/<path:path>/"` | `GET` | `` |
| `endpoints/web.py` | `user_view` | `web` | `` | `"/user/<path:path>"` | `"/user/<path:path>"` | `GET` | `` |
| `endpoints/web.py` | `user_view` | `web` | `` | `"/user/<path:path>/"` | `"/user/<path:path>/"` | `GET` | `` |
| `endpoints/web.py` | `plans` | `web` | `` | `"/plans/"` | `"/plans/"` | `GET` | `features.BILLING` |
| `endpoints/web.py` | `search` | `web` | `` | `"/search"` | `"/search"` | `GET` | `` |
| `endpoints/web.py` | `guide` | `web` | `` | `"/guide/"` | `"/guide/"` | `GET` | `` |
| `endpoints/web.py` | `tour` | `web` | `` | `"/tour/"` | `"/tour/"` | `GET` | `` |
| `endpoints/web.py` | `tour` | `web` | `` | `"/tour/<path:path>"` | `"/tour/<path:path>"` | `GET` | `` |
| `endpoints/web.py` | `tutorial` | `web` | `` | `"/tutorial/"` | `"/tutorial/"` | `GET` | `` |
| `endpoints/web.py` | `organizations` | `web` | `` | `"/organizations/"` | `"/organizations/"` | `GET` | `` |
| `endpoints/web.py` | `organizations` | `web` | `` | `"/organizations/new/"` | `"/organizations/new/"` | `GET` | `` |
| `endpoints/web.py` | `superuser` | `web` | `` | `"/superuser/"` | `"/superuser/"` | `GET` | `features.SUPER_USERS` |
| `endpoints/web.py` | `setup` | `web` | `` | `"/setup/"` | `"/setup/"` | `GET` | `features.SUPER_USERS` |
| `endpoints/web.py` | `signin` | `web` | `` | `"/signin/"` | `"/signin/"` | `GET` | `` |
| `endpoints/web.py` | `contact` | `web` | `` | `"/contact/"` | `"/contact/"` | `GET` | `` |
| `endpoints/web.py` | `about` | `web` | `` | `"/about/"` | `"/about/"` | `GET` | `` |
| `endpoints/web.py` | `new` | `web` | `` | `"/new/"` | `"/new/"` | `GET` | `` |
| `endpoints/web.py` | `updateuser` | `web` | `` | `"/updateuser"` | `"/updateuser"` | `GET` | `` |
| `endpoints/web.py` | `confirm_invite` | `web` | `` | `"/confirminvite"` | `"/confirminvite"` | `GET` | `` |
| `endpoints/web.py` | `repository` | `web` | `` | `"/repository/"` | `"/repository/"` | `GET` | `` |
| `endpoints/web.py` | `repository` | `web` | `` | `"/repository/<path:path>"` | `"/repository/<path:path>"` | `GET` | `` |
| `endpoints/web.py` | `buildtrigger` | `web` | `` | `"/repository/<path:path>/trigger/<trigger>"` | `"/repository/<path:path>/trigger/<trigger>"` | `GET` | `` |
| `endpoints/web.py` | `security` | `web` | `` | `"/security/"` | `"/security/"` | `GET` | `` |
| `endpoints/web.py` | `enterprise` | `web` | `` | `"/enterprise/"` | `"/enterprise/"` | `GET` | `features.BILLING` |
| `endpoints/web.py` | `exp` | `web` | `` | `"/__exp/<expname>"` | `"/__exp/<expname>"` | `GET` | `` |
| `endpoints/web.py` | `v1` | `web` | `` | `"/v1"` | `"/v1"` | `GET` | `` |
| `endpoints/web.py` | `v1` | `web` | `` | `"/v1/"` | `"/v1/"` | `GET` | `` |
| `endpoints/web.py` | `tos` | `web` | `` | `"/tos"` | `"/tos"` | `GET` | `` |
| `endpoints/web.py` | `privacy` | `web` | `` | `"/privacy"` | `"/privacy"` | `GET` | `` |
| `endpoints/web.py` | `instance_health` | `web` | `` | `"/health"` | `"/health"` | `GET` | `` |
| `endpoints/web.py` | `instance_health` | `web` | `` | `"/health/instance"` | `"/health/instance"` | `GET` | `` |
| `endpoints/web.py` | `endtoend_health` | `web` | `` | `"/status"` | `"/status"` | `GET` | `` |
| `endpoints/web.py` | `endtoend_health` | `web` | `` | `"/health/endtoend"` | `"/health/endtoend"` | `GET` | `` |
| `endpoints/web.py` | `warning_health` | `web` | `` | `"/health/warning"` | `"/health/warning"` | `GET` | `` |
| `endpoints/web.py` | `dbrevision_health` | `web` | `` | `"/health/dbrevision"` | `"/health/dbrevision"` | `GET` | `features.BILLING` |
| `endpoints/web.py` | `enable_health_debug` | `web` | `` | `"/health/enabledebug/<secret>"` | `"/health/enabledebug/<secret>"` | `GET` | `` |
| `endpoints/web.py` | `robots` | `web` | `` | `"/robots.txt"` | `"/robots.txt"` | `GET` | `` |
| `endpoints/web.py` | `buildlogs` | `web` | `` | `"/buildlogs/<build_uuid>"` | `"/buildlogs/<build_uuid>"` | `GET` | `features.BUILD_SUPPORT` |
| `endpoints/web.py` | `exportedlogs` | `web` | `` | `"/exportedlogs/<file_id>"` | `"/exportedlogs/<file_id>"` | `GET` | `` |
| `endpoints/web.py` | `logarchive` | `web` | `` | `"/logarchive/<file_id>"` | `"/logarchive/<file_id>"` | `GET` | `features.BUILD_SUPPORT` |
| `endpoints/web.py` | `receipt` | `web` | `` | `"/receipt"` | `"/receipt"` | `GET` | `features.BILLING` |
| `endpoints/web.py` | `confirm_repo_email` | `web` | `` | `"/authrepoemail"` | `"/authrepoemail"` | `GET` | `features.MAILING` |
| `endpoints/web.py` | `confirm_email` | `web` | `` | `"/confirm"` | `"/confirm"` | `GET` | `features.MAILING` |
| `endpoints/web.py` | `confirm_recovery` | `web` | `` | `"/recovery"` | `"/recovery"` | `GET` | `features.MAILING` |
| `endpoints/web.py` | `build_status_badge` | `web` | `` | `"/repository/<repopath:repository>/status"` | `"/repository/<repopath:repository>/status"` | `GET` | `` |
| `endpoints/web.py` | `authorize_application` | `web` | `` | `"/oauth/authorizeapp"` | `"/oauth/authorizeapp"` | `POST` | `` |
| `endpoints/web.py` | `oauth_local_handler` | `web` | `` | `app.config["LOCAL_OAUTH_HANDLER"]` | `/app.config["LOCAL_OAUTH_HANDLER"]` | `GET` | `` |
| `endpoints/web.py` | `deny_application` | `web` | `` | `"/oauth/denyapp"` | `"/oauth/denyapp"` | `POST` | `` |
| `endpoints/web.py` | `request_authorization_code` | `web` | `` | `"/oauth/authorize"` | `"/oauth/authorize"` | `GET` | `` |
| `endpoints/web.py` | `assign_user_to_app` | `web` | `` | `"/oauth/authorize/assignuser"` | `"/oauth/authorize/assignuser"` | `POST` | `` |
| `endpoints/web.py` | `exchange_code_for_token` | `web` | `` | `"/oauth/access_token"` | `"/oauth/access_token"` | `POST` | `` |
| `endpoints/web.py` | `attach_bitbucket_trigger` | `web` | `` | `"/bitbucket/setup/<repopath:repository>"` | `"/bitbucket/setup/<repopath:repository>"` | `GET` | `features.BITBUCKET_BUILD` |
| `endpoints/web.py` | `attach_custom_build_trigger` | `web` | `` | `"/customtrigger/setup/<repopath:repository>"` | `"/customtrigger/setup/<repopath:repository>"` | `GET` | `` |
| `endpoints/web.py` | `redirect_to_repository` | `web` | `` | `"/<repopathredirect:repository>"` | `"/<repopathredirect:repository>"` | `GET` | `` |
| `endpoints/web.py` | `redirect_to_repository` | `web` | `` | `"/<repopathredirect:repository>/"` | `"/<repopathredirect:repository>/"` | `GET` | `` |
| `endpoints/web.py` | `redirect_to_namespace` | `web` | `` | `"/<namespace>"` | `"/<namespace>"` | `GET` | `` |
| `endpoints/web.py` | `redirect_to_namespace` | `web` | `` | `"/<namespace>/"` | `"/<namespace>/"` | `GET` | `` |
| `endpoints/web.py` | `user_initialize` | `web` | `` | `"/api/v1/user/initialize"` | `"/api/v1/user/initialize"` | `POST` | `features.USER_INITIALIZE` |
| `endpoints/web.py` | `config` | `web` | `` | `"/config"` | `"/config"` | `GET,OPTIONS` | `` |
| `endpoints/web.py` | `csrf_token` | `web` | `` | `"/csrf_token"` | `"/csrf_token"` | `GET,OPTIONS` | `` |
| `endpoints/webhooks.py` | `stripe_webhook` | `webhooks` | `/webhooks` | `"/stripe"` | `/webhooks"/stripe"` | `POST` | `` |
| `endpoints/webhooks.py` | `build_trigger_webhook` | `webhooks` | `/webhooks` | `"/push/<repopath:repository>/trigger/<trigger_uuid>"` | `/webhooks"/push/<repopath:repository>/trigger/<trigger_uuid>"` | `POST` | `` |
| `endpoints/webhooks.py` | `build_trigger_webhook` | `webhooks` | `/webhooks` | `"/push/trigger/<trigger_uuid>"` | `/webhooks"/push/trigger/<trigger_uuid>"` | `POST` | `` |
| `endpoints/wellknown.py` | `app_capabilities` | `wellknown` | `/.well-known` | `"/app-capabilities"` | `/.well-known"/app-capabilities"` | `GET` | `` |
| `endpoints/wellknown.py` | `change_password` | `wellknown` | `/.well-known` | `"/change-password"` | `/.well-known"/change-password"` | `GET` | `` |
| `web.py` | `register_blueprint` | `web` | `` | `` | `` | `N/A` | `` |
| `web.py` | `register_blueprint` | `githubtrigger` | `` | `"/oauth2"` | `"/oauth2"` | `N/A` | `` |
| `web.py` | `register_blueprint` | `gitlabtrigger` | `` | `"/oauth2"` | `"/oauth2"` | `N/A` | `` |
| `web.py` | `register_blueprint` | `oauthlogin` | `` | `"/oauth2"` | `"/oauth2"` | `N/A` | `` |
| `web.py` | `register_blueprint` | `federation_bp` | `` | `"/oauth2"` | `"/oauth2"` | `N/A` | `` |
| `web.py` | `register_blueprint` | `bitbuckettrigger` | `` | `"/oauth1"` | `"/oauth1"` | `N/A` | `` |
| `web.py` | `register_blueprint` | `api_bp` | `` | `"/api"` | `"/api"` | `N/A` | `` |
| `web.py` | `register_blueprint` | `webhooks` | `` | `"/webhooks"` | `"/webhooks"` | `N/A` | `` |
| `web.py` | `register_blueprint` | `realtime` | `` | `"/realtime"` | `"/realtime"` | `N/A` | `` |
| `web.py` | `register_blueprint` | `key_server` | `` | `"/keys"` | `"/keys"` | `N/A` | `` |
| `web.py` | `register_blueprint` | `wellknown` | `` | `"/.well-known"` | `"/.well-known"` | `N/A` | `` |
| `registry.py` | `register_blueprint` | `v1_bp` | `` | `"/v1"` | `"/v1"` | `N/A` | `` |
| `registry.py` | `register_blueprint` | `v2_bp` | `` | `"/v2"` | `"/v2"` | `N/A` | `` |
| `secscan.py` | `register_blueprint` | `secscan` | `` | `"/secscan"` | `"/secscan"` | `N/A` | `` |

## Dynamic Routes (`add_url_rule`)

| File | Target | Prefix | Path expr | Full path expr | Methods | Endpoint expr | View expr | Notes |
|---|---|---|---|---|---|---|---|---|
| `endpoints/oauth/login.py` | `oauthlogin` | `/oauth2` | `"/%s/callback/captcha" % login_service.service_id()` | `/oauth2"/%s/callback/captcha" % login_service.service_id()` | `POST` | `"%s_oauth_captcha" % login_service.service_id()` | `captcha_func` | `Dynamic registration via add_url_rule` |
| `endpoints/oauth/login.py` | `oauthlogin` | `/oauth2` | `"/%s/callback" % login_service.service_id()` | `/oauth2"/%s/callback" % login_service.service_id()` | `GET,POST` | `"%s_oauth_callback" % login_service.service_id()` | `callback_func` | `Dynamic registration via add_url_rule` |
| `endpoints/oauth/login.py` | `oauthlogin` | `/oauth2` | `"/%s/callback/attach" % login_service.service_id()` | `/oauth2"/%s/callback/attach" % login_service.service_id()` | `GET,POST` | `"%s_oauth_attach" % login_service.service_id()` | `attach_func` | `Dynamic registration via add_url_rule` |
| `endpoints/oauth/login.py` | `oauthlogin` | `/oauth2` | `"/%s/callback/cli" % login_service.service_id()` | `/oauth2"/%s/callback/cli" % login_service.service_id()` | `GET,POST` | `"%s_oauth_cli" % login_service.service_id()` | `cli_token_func` | `Dynamic registration via add_url_rule` |
