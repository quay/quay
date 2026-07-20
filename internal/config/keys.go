package config

// Keys holds secret key material.
type Keys struct {
	SecretKey                     string `yaml:"SECRET_KEY"`
	DatabaseSecretKey             string `yaml:"DATABASE_SECRET_KEY"`
	InstanceServiceKeyLocation    string `yaml:"INSTANCE_SERVICE_KEY_LOCATION"`
	InstanceServiceKeyKIDLocation string `yaml:"INSTANCE_SERVICE_KEY_KID_LOCATION"`
	InstanceServiceKeyService     string `yaml:"INSTANCE_SERVICE_KEY_SERVICE"`
	RegistryJWTAuthMaxFreshS      int    `yaml:"REGISTRY_JWT_AUTH_MAX_FRESH_S"`
}
