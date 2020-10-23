package config

import (
	"github.com/quay/config-tool/pkg/lib/fieldgroups/accesssettings"
	"github.com/quay/config-tool/pkg/lib/fieldgroups/actionlogarchiving"
	"github.com/quay/config-tool/pkg/lib/fieldgroups/apptokenauthentication"
	"github.com/quay/config-tool/pkg/lib/fieldgroups/bitbucketbuildtrigger"
	"github.com/quay/config-tool/pkg/lib/fieldgroups/database"
	"github.com/quay/config-tool/pkg/lib/fieldgroups/distributedstorage"
	"github.com/quay/config-tool/pkg/lib/fieldgroups/elasticsearch"
	"github.com/quay/config-tool/pkg/lib/fieldgroups/email"
	"github.com/quay/config-tool/pkg/lib/fieldgroups/githubbuildtrigger"
	"github.com/quay/config-tool/pkg/lib/fieldgroups/githublogin"
	"github.com/quay/config-tool/pkg/lib/fieldgroups/gitlabbuildtrigger"
	"github.com/quay/config-tool/pkg/lib/fieldgroups/googlelogin"
	"github.com/quay/config-tool/pkg/lib/fieldgroups/hostsettings"
	"github.com/quay/config-tool/pkg/lib/fieldgroups/jwtauthentication"
	"github.com/quay/config-tool/pkg/lib/fieldgroups/quaydocumentation"
	"github.com/quay/config-tool/pkg/lib/fieldgroups/redis"
	"github.com/quay/config-tool/pkg/lib/fieldgroups/repomirror"
	"github.com/quay/config-tool/pkg/lib/fieldgroups/securityscanner"
	"github.com/quay/config-tool/pkg/lib/fieldgroups/signingengine"
	"github.com/quay/config-tool/pkg/lib/fieldgroups/teamsyncing"
	"github.com/quay/config-tool/pkg/lib/fieldgroups/uservisiblesettings"
	"github.com/quay/config-tool/pkg/lib/shared"
)

// Config is a struct that represents a configuration as a mapping of field groups
type Config map[string]shared.FieldGroup

// NewConfig creates a Config struct from a map[string]interface{}
func NewConfig(fullConfig map[string]interface{}) (Config, error) {

	var err error
	newConfig := Config{}
	newBitbucketBuildTriggerFieldGroup, err := bitbucketbuildtrigger.NewBitbucketBuildTriggerFieldGroup(fullConfig)
	if err != nil {
		return newConfig, err
	}
	newConfig["BitbucketBuildTrigger"] = newBitbucketBuildTriggerFieldGroup
	newEmailFieldGroup, err := email.NewEmailFieldGroup(fullConfig)
	if err != nil {
		return newConfig, err
	}
	newConfig["Email"] = newEmailFieldGroup
	newGitHubBuildTriggerFieldGroup, err := githubbuildtrigger.NewGitHubBuildTriggerFieldGroup(fullConfig)
	if err != nil {
		return newConfig, err
	}
	newConfig["GitHubBuildTrigger"] = newGitHubBuildTriggerFieldGroup
	newDistributedStorageFieldGroup, err := distributedstorage.NewDistributedStorageFieldGroup(fullConfig)
	if err != nil {
		return newConfig, err
	}
	newConfig["DistributedStorage"] = newDistributedStorageFieldGroup
	newAccessSettingsFieldGroup, err := accesssettings.NewAccessSettingsFieldGroup(fullConfig)
	if err != nil {
		return newConfig, err
	}
	newConfig["AccessSettings"] = newAccessSettingsFieldGroup
	newRedisFieldGroup, err := redis.NewRedisFieldGroup(fullConfig)
	if err != nil {
		return newConfig, err
	}
	newConfig["Redis"] = newRedisFieldGroup
	newHostSettingsFieldGroup, err := hostsettings.NewHostSettingsFieldGroup(fullConfig)
	if err != nil {
		return newConfig, err
	}
	newConfig["HostSettings"] = newHostSettingsFieldGroup
	newUserVisibleSettingsFieldGroup, err := uservisiblesettings.NewUserVisibleSettingsFieldGroup(fullConfig)
	if err != nil {
		return newConfig, err
	}
	newConfig["UserVisibleSettings"] = newUserVisibleSettingsFieldGroup
	newQuayDocumentationFieldGroup, err := quaydocumentation.NewQuayDocumentationFieldGroup(fullConfig)
	if err != nil {
		return newConfig, err
	}
	newConfig["QuayDocumentation"] = newQuayDocumentationFieldGroup
	newGitHubLoginFieldGroup, err := githublogin.NewGitHubLoginFieldGroup(fullConfig)
	if err != nil {
		return newConfig, err
	}
	newConfig["GitHubLogin"] = newGitHubLoginFieldGroup
	newTeamSyncingFieldGroup, err := teamsyncing.NewTeamSyncingFieldGroup(fullConfig)
	if err != nil {
		return newConfig, err
	}
	newConfig["TeamSyncing"] = newTeamSyncingFieldGroup
	newRepoMirrorFieldGroup, err := repomirror.NewRepoMirrorFieldGroup(fullConfig)
	if err != nil {
		return newConfig, err
	}
	newConfig["RepoMirror"] = newRepoMirrorFieldGroup
	newSecurityScannerFieldGroup, err := securityscanner.NewSecurityScannerFieldGroup(fullConfig)
	if err != nil {
		return newConfig, err
	}
	newConfig["SecurityScanner"] = newSecurityScannerFieldGroup
	newSigningEngineFieldGroup, err := signingengine.NewSigningEngineFieldGroup(fullConfig)
	if err != nil {
		return newConfig, err
	}
	newConfig["SigningEngine"] = newSigningEngineFieldGroup
	newActionLogArchivingFieldGroup, err := actionlogarchiving.NewActionLogArchivingFieldGroup(fullConfig)
	if err != nil {
		return newConfig, err
	}
	newConfig["ActionLogArchiving"] = newActionLogArchivingFieldGroup
	newJWTAuthenticationFieldGroup, err := jwtauthentication.NewJWTAuthenticationFieldGroup(fullConfig)
	if err != nil {
		return newConfig, err
	}
	newConfig["JWTAuthentication"] = newJWTAuthenticationFieldGroup
	newDatabaseFieldGroup, err := database.NewDatabaseFieldGroup(fullConfig)
	if err != nil {
		return newConfig, err
	}
	newConfig["Database"] = newDatabaseFieldGroup
	newGitLabBuildTriggerFieldGroup, err := gitlabbuildtrigger.NewGitLabBuildTriggerFieldGroup(fullConfig)
	if err != nil {
		return newConfig, err
	}
	newConfig["GitLabBuildTrigger"] = newGitLabBuildTriggerFieldGroup
	newGoogleLoginFieldGroup, err := googlelogin.NewGoogleLoginFieldGroup(fullConfig)
	if err != nil {
		return newConfig, err
	}
	newConfig["GoogleLogin"] = newGoogleLoginFieldGroup
	newElasticSearchFieldGroup, err := elasticsearch.NewElasticSearchFieldGroup(fullConfig)
	if err != nil {
		return newConfig, err
	}
	newConfig["ElasticSearch"] = newElasticSearchFieldGroup
	newAppTokenAuthenticationFieldGroup, err := apptokenauthentication.NewAppTokenAuthenticationFieldGroup(fullConfig)
	if err != nil {
		return newConfig, err
	}
	newConfig["AppTokenAuthentication"] = newAppTokenAuthenticationFieldGroup

	return newConfig, nil
}
