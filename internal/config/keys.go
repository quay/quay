package config

// Keys holds secret key material.
type Keys struct {
	SecretKey         string `yaml:"SECRET_KEY"`
	DatabaseSecretKey string `yaml:"DATABASE_SECRET_KEY"`
}
