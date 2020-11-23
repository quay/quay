package signingengine

import "github.com/quay/config-tool/pkg/lib/shared"

// Validate checks the configuration settings for this field group
func (fg *SigningEngineFieldGroup) Validate(opts shared.Options) []shared.ValidationError {

	// Make empty errors
	errors := []shared.ValidationError{}

	// Make sure feature is enabled
	if fg.SigningEngine == "" || fg.FeatureSigning == false {
		return errors
	}

	// Check signing engine is valid
	if ok, err := shared.ValidateIsOneOfString(fg.SigningEngine, []string{"gpg2"}, "SIGNING_ENGINE", "SigningEngine"); !ok {
		errors = append(errors, err)
	}

	// Check required fields
	if ok, err := shared.ValidateRequiredString(fg.Gpg2PublicKeyFilename, "GPG2_PUBLIC_KEY_FILENAME", "SigningEngine"); !ok {
		errors = append(errors, err)
	}
	if ok, err := shared.ValidateRequiredString(fg.Gpg2PrivateKeyFilename, "GPG2_PRIVATE_KEY_FILENAME", "SigningEngine"); !ok {
		errors = append(errors, err)
	}
	if ok, err := shared.ValidateRequiredString(fg.Gpg2PrivateKeyName, "GPG2_PRIVATE_KEY_NAME", "SigningEngine"); !ok {
		errors = append(errors, err)
	}

	// Check public key exists
	if ok, err := shared.ValidateFileExists(fg.Gpg2PublicKeyFilename, "GPG2_PUBLIC_KEY_FILENAME", "SigningEngine"); !ok {
		errors = append(errors, err)
		return errors
	}

	// Check private key exists
	if ok, err := shared.ValidateFileExists(fg.Gpg2PrivateKeyFilename, "GPG2_PRIVATE_KEY_FILENAME", "SigningEngine"); !ok {
		errors = append(errors, err)
		return errors
	}

	return errors
}
