package config

import (
	"github.com/quay/config-tool/pkg/lib/fieldgroups/accesssettings"
	"github.com/quay/config-tool/pkg/lib/fieldgroups/actionlogarchiving"
	"github.com/quay/config-tool/pkg/lib/fieldgroups/apptokenauthentication"
	"github.com/quay/config-tool/pkg/lib/fieldgroups/bitbucketbuildtrigger"
	"github.com/quay/config-tool/pkg/lib/fieldgroups/database"
	"github.com/quay/config-tool/pkg/lib/fieldgroups/elasticsearch"
	"github.com/quay/config-tool/pkg/lib/fieldgroups/githubbuildtrigger"
	"github.com/quay/config-tool/pkg/lib/fieldgroups/githublogin"
	"github.com/quay/config-tool/pkg/lib/fieldgroups/gitlabbuildtrigger"
	"github.com/quay/config-tool/pkg/lib/fieldgroups/googlelogin"
	"github.com/quay/config-tool/pkg/lib/fieldgroups/jwtauthentication"
	"github.com/quay/config-tool/pkg/lib/fieldgroups/quaydocumentation"
	"github.com/quay/config-tool/pkg/lib/fieldgroups/redis"
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
	newGitHubLoginFieldGroup, err := githublogin.NewGitHubLoginFieldGroup(fullConfig)
	if err != nil {
		return newConfig, err
	}
	newConfig["GitHubLogin"] = newGitHubLoginFieldGroup
	newAppTokenAuthenticationFieldGroup, err := apptokenauthentication.NewAppTokenAuthenticationFieldGroup(fullConfig)
	if err != nil {
		return newConfig, err
	}
	newConfig["AppTokenAuthentication"] = newAppTokenAuthenticationFieldGroup
	newRedisFieldGroup, err := redis.NewRedisFieldGroup(fullConfig)
	if err != nil {
		return newConfig, err
	}
	newConfig["Redis"] = newRedisFieldGroup
	newGitHubBuildTriggerFieldGroup, err := githubbuildtrigger.NewGitHubBuildTriggerFieldGroup(fullConfig)
	if err != nil {
		return newConfig, err
	}
	newConfig["GitHubBuildTrigger"] = newGitHubBuildTriggerFieldGroup
	newGitLabBuildTriggerFieldGroup, err := gitlabbuildtrigger.NewGitLabBuildTriggerFieldGroup(fullConfig)
	if err != nil {
		return newConfig, err
	}
	newConfig["GitLabBuildTrigger"] = newGitLabBuildTriggerFieldGroup
	newTeamSyncingFieldGroup, err := teamsyncing.NewTeamSyncingFieldGroup(fullConfig)
	if err != nil {
		return newConfig, err
	}
	newConfig["TeamSyncing"] = newTeamSyncingFieldGroup
	newSecurityScannerFieldGroup, err := securityscanner.NewSecurityScannerFieldGroup(fullConfig)
	if err != nil {
		return newConfig, err
	}
	newConfig["SecurityScanner"] = newSecurityScannerFieldGroup
	newAccessSettingsFieldGroup, err := accesssettings.NewAccessSettingsFieldGroup(fullConfig)
	if err != nil {
		return newConfig, err
	}
	newConfig["AccessSettings"] = newAccessSettingsFieldGroup
	newQuayDocumentationFieldGroup, err := quaydocumentation.NewQuayDocumentationFieldGroup(fullConfig)
	if err != nil {
		return newConfig, err
	}
	newConfig["QuayDocumentation"] = newQuayDocumentationFieldGroup
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
	newBitbucketBuildTriggerFieldGroup, err := bitbucketbuildtrigger.NewBitbucketBuildTriggerFieldGroup(fullConfig)
	if err != nil {
		return newConfig, err
	}
	newConfig["BitbucketBuildTrigger"] = newBitbucketBuildTriggerFieldGroup
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
	newUserVisibleSettingsFieldGroup, err := uservisiblesettings.NewUserVisibleSettingsFieldGroup(fullConfig)
	if err != nil {
		return newConfig, err
	}
	newConfig["UserVisibleSettings"] = newUserVisibleSettingsFieldGroup

	return newConfig, nil
}
