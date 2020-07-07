# Config Tool

The Quay Config Tool implements several features to capture and validate configuration data based on a predefined schema.

This tool includes the following features:

- Validate Quay configuration using CLI tool
- Generate code for custom field group definitions (includes structs, constructors, defaults)
- Validation tag support from [Validator](https://github.com/go-playground/validator)
- Built-in validator tags for OAuth and JWT structs

## Installation

Install using the Go tool:

```
go get -u github.com/quay/config-tool/...
```

This will generate files for the Quay validator executable and install the `config-tool` CLI tool.

#### Note: By default, this tool will generate an executable from a pre-built Config definition. For usage on writing a custom Config definition see [here](https://github.com/quay/config-tool/tree/master/utils/generate)

## Usage

The CLI tool contains two main commands:

#### The `print` command is used to output the entire configuration with defaults specified

```
{
        "AccessSettings": (*accesssettings.AccessSettingsFieldGroup)({
                AuthenticationType: "InvalidType",
                FeatureAnonymousAccess: true,
                FeatureDirectLogin: false,
                FeatureGithubLogin: false,
                FeatureGoogleLogin: true,
                FeatureInviteOnlyUserCreation: false,
                FeaturePartialUserAutocomplete: true,
                FeatureUsernameConfirmation: true,
                FeatureUserCreation: true,
                FeatureUserLastAccessed: true,
                FeatureUserLogAccess: false,
                FeatureUserMetadata: false,
                FeatureUserRename: false,
                FreshLoginTimeout: "10m",
                UserRecoveryTokenLifetime: "30m"
        }),
        "ActionLogArchiving": (*actionlogarchiving.ActionLogArchivingFieldGroup)({
                ActionLogArchiveLocation: "aws_bucket",
                ActionLogArchivePath: "path/to/path",
                DistributedStorageConfig: (*actionlogarchiving.DistributedStorageConfigStruct)({
                        "LocalStorage": {
                                ["aws", "path/to/storage"
                        },

                }),
                FeatureActionLogRotation: true
        }),
        "AppTokenAuthentication": (*apptokenauthentication.AppTokenAuthenticationFieldGroup)({
                AuthenticationType: "InvalidType",
                FeatureAppSpecificTokens: true,
                FeatureDirectLogin: false
        }),
        "BitbucketBuildTrigger": (*bitbucketbuildtrigger.BitbucketBuildTriggerFieldGroup)({
                BitbucketTriggerConfig: (*bitbucketbuildtrigger.BitbucketTriggerConfigStruct)({
                        ConsumerSecret: "client_seccret",
                        ConsumerKey: "client_id"
                }),
                FeatureBitbucketBuild: true,
                FeatureBuildSupport: true
        }),
        "Database": (*database.DatabaseFieldGroup)({
                DbConnectionArgs: (*database.DbConnectionArgsStruct)(<nil>),
                DbUri: "mysql://user:pass@host:port/db_name"
        }),
        "ElasticSearch": (*elasticsearch.ElasticSearchFieldGroup)({
                LogsModel: "elasticsearch",
                LogsModelConfig: (*elasticsearch.LogsModelConfigStruct)({
                        ElasticsearchConfig: (*elasticsearch.ElasticsearchConfigStruct)({
                                AwsRegion: "",
                                Port: 9243,
                                AccessKey: "elastic",
                                Host: "bfd70499058e4485854f8bacf06af627.us-central1.gcp.cloud.es.io",
                                IndexPrefix: "logentry_",
                                IndexSettings: (*elasticsearch.IndexSettingsStruct)(<nil>),
                                UseSsl: true,
                                SecretKey: "client_secret"
                        }),
                        KinesisStreamConfig: (*elasticsearch.KinesisStreamConfigStruct)(<nil>),
                        Producer: "",
                        KafkaConfig: (*elasticsearch.KafkaConfigStruct)(<nil>)
                })
        }),
        "GitHubBuildTrigger": (*githubbuildtrigger.GitHubBuildTriggerFieldGroup)({
                FeatureBuildSupport: true,
                FeatureGithubBuild: true,
                GithubTriggerConfig: (*githubbuildtrigger.GithubTriggerConfigStruct)({
                        OrgRestrict: false,
                        ApiEndpoint: "",
                        ClientSecret: "client_secret",
                        GithubEndpoint: "https://www.google.com",
                        ClientId: "client_id",
                        AllowedOrganizations: {
                        }
                })
        }),
        "GitHubLogin": (*githublogin.GitHubLoginFieldGroup)({
                FeatureGithubLogin: false,
                GithubLoginConfig: (*githublogin.GithubLoginConfigStruct)(<nil>)
        }),
        "GitLabBuildTrigger": (*gitlabbuildtrigger.GitLabBuildTriggerFieldGroup)({
                FeatureBuildSupport: true,
                FeatureGitlabBuild: true,
                GitlabTriggerConfig: (*gitlabbuildtrigger.GitlabTriggerConfigStruct)({
                        ClientSecret: "client_secret",
                        GitlabEndpoint: "https://google.com",
                        ClientId: "client_id"
                })
        }),
        "GoogleLogin": (*googlelogin.GoogleLoginFieldGroup)({
                FeatureGoogleLogin: true,
                GoogleLoginConfig: (*googlelogin.GoogleLoginConfigStruct)({
                        ClientSecret: "client_secret",
                        ClientId: "client_id"
                })
        }),
        "JWTAuthentication": (*jwtauthentication.JWTAuthenticationFieldGroup)({
                AuthenticationType: "green",
                FeatureMailing: true,
                JwtAuthIssuer: "",
                JwtGetuserEndpoint: "",
                JwtQueryEndpoint: "",
                JwtVerifyEndpoint: ""
        }),
        "QuayDocumentation": (*quaydocumentation.QuayDocumentationFieldGroup)({
                DocumentationRoot: "/documentation"
        }),
        "Redis": (*redis.RedisFieldGroup)({
                BuildlogsRedis: (*redis.BuildlogsRedisStruct)(<nil>),
                UserEventsRedis: (*redis.UserEventsRedisStruct)(<nil>)
        }),
        "SecurityScanner": (*securityscanner.SecurityScannerFieldGroup)({
                FeatureSecurityScanner: true,
                SecurityScannerEndpoint: "htp://google.com",
                SecurityScannerIndexingInterval: 30,
                SecurityScannerNotifications: false,
                SecurityScannerV4Endpoint: "https://this-is-a-fake-website.com/",
                SecurityScannerV4NamespaceWhitelist: {
                }
        }),
        "SigningEngine": (*signingengine.SigningEngineFieldGroup)({
                Gpg2PrivateKeyFilename: "",
                Gpg2PrivateKeyName: "",
                Gpg2PublicKeyFilename: "",
                SigningEngine: ""
        }),
        "TeamSyncing": (*teamsyncing.TeamSyncingFieldGroup)({
                FeatureNonsuperuserTeamSyncingSetup: false,
                FeatureTeamSyncing: false,
                TeamResyncStaleTime: "30m"
        }),
        "UserVisibleSettings": (*uservisiblesettings.UserVisibleSettingsFieldGroup)({
                AvatarKind: "local",
                Branding: (*uservisiblesettings.BrandingStruct)({
                        Logo: "logo.svg",
                        FooterImg: "footer.svg",
                        FooterUrl: "footer_url.svg"
                }),
                ContactInfo: {
                        "mailto:joking@redhat.com"
                },
                RegistryTitle: "Project Quay",
                RegistryTitleShort: "Project Quay",
                SearchMaxResultPageCount: 10,
                SearchResultsPerPage: 10
        })
}
```

#### The `validate` command is used to show while field groups have been validated succesully

```
$ config-tool validate -c <path-to-config.yaml>
-----------------------------------------------------------------------------+--------+
| BitbucketBuildTrigger  | -                                                                            | 🟢     |
+------------------------+------------------------------------------------------------------------------+--------+
| Database               | -                                                                            | 🟢     |
+------------------------+------------------------------------------------------------------------------+--------+
| ElasticSearch          | -                                                                            | 🟢     |
+------------------------+------------------------------------------------------------------------------+--------+
| GitHubBuildTrigger     | -                                                                            | 🟢     |
+------------------------+------------------------------------------------------------------------------+--------+
| GitHubLogin            | -                                                                            | 🟢     |
+------------------------+------------------------------------------------------------------------------+--------+
| GitLabBuildTrigger     | -                                                                            | 🟢     |
+------------------------+------------------------------------------------------------------------------+--------+
| GoogleLogin            | -                                                                            | 🟢     |
+------------------------+------------------------------------------------------------------------------+--------+
| JWTAuthentication      | -                                                                            | 🟢     |
+------------------------+------------------------------------------------------------------------------+--------+
| QuayDocumentation      | -                                                                            | 🟢     |
+------------------------+------------------------------------------------------------------------------+--------+
| Redis                  | BUILD_LOGS_REDIS is required                                                 | 🔴     |
+------------------------+------------------------------------------------------------------------------+--------+
| SecurityScanner        | Cannot reach htp://google.com                                                | 🔴     |
+                        +------------------------------------------------------------------------------+--------+
|                        | Cannot reach https://this-is-a-fake-website.com/                             | 🔴     |
+------------------------+------------------------------------------------------------------------------+--------+
| SigningEngine          | -                                                                            | 🟢     |
+------------------------+------------------------------------------------------------------------------+--------+
| TeamSyncing            | -                                                                            | 🟢     |
+------------------------+------------------------------------------------------------------------------+--------+
| UserVisibleSettings    | -                                                                            | 🟢     |
+------------------------+------------------------------------------------------------------------------+--------+
```
