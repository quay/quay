package distribution

const (
	defaultLibraryNamespace = "library"
	repositoryResourceType  = "repository"
	repositoryPullAction    = "pull"

	repositoryPushAction           = "push"
	repositoryDeleteAction         = "delete"
	registryResourceType           = "registry"
	registryCatalogName            = "catalog"
	registryCatalogAction          = "*"
	quayDBAuthBackend              = "quaydb"
	authOptionRealm                = "realm"
	authOptionService              = "service"
	authOptionDB                   = "db"
	authOptionLibraryNamespace     = "libraryNamespace"
	authOptionAnonAccess           = "anonymousAccess"
	authOptionJWTService           = "jwtService"
	authOptionController           = "controller"
	authOptionDatabaseKey          = "databaseSecretKey"
	authOptionRobotsDisallow       = "robotsDisallow"
	authOptionRobotsWhitelist      = "robotsWhitelist"
	authOptionLastAccess           = "featureUserLastAccessed"
	authOptionLastAccessS          = "lastAccessedUpdateThresholdSeconds"
	authOptionSuperUsers           = "superUsers"
	authOptionSuperUsersFullAccess = "superUsersFullAccess"
)
