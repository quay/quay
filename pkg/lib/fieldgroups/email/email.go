package email

import (
	"errors"

	"github.com/creasty/defaults"
)

// EmailFieldGroup represents the EmailFieldGroup config fields
type EmailFieldGroup struct {
	BlacklistedEmailDomains  []interface{} `default:"[]" validate:"" yaml:"BLACKLISTED_EMAIL_DOMAINS,omitempty" json:"BLACKLISTED_EMAIL_DOMAINS,omitempty"`
	FeatureBlacklistedEmails bool          `default:"false" validate:"" yaml:"FEATURE_BLACKLISTED_EMAILS,omitempty" json:"FEATURE_BLACKLISTED_EMAILS,omitempty"`
	FeatureMailing           bool          `default:"false" validate:"" yaml:"FEATURE_MAILING,omitempty" json:"FEATURE_MAILING,omitempty"`
	MailDefaultSender        string        `default:"support@quay.io" validate:"" yaml:"MAIL_DEFAULT_SENDER,omitempty" json:"MAIL_DEFAULT_SENDER,omitempty"`
	MailPassword             string        `default:"" validate:"" yaml:"MAIL_PASSWORD,omitempty" json:"MAIL_PASSWORD,omitempty"`
	MailPort                 int           `default:"587" validate:"" yaml:"MAIL_PORT,omitempty" json:"MAIL_PORT,omitempty"`
	MailServer               string        `default:"" validate:"" yaml:"MAIL_SERVER,omitempty" json:"MAIL_SERVER,omitempty"`
	MailUseAuth              bool          `default:"false" validate:"" yaml:"MAIL_USE_AUTH,omitempty" json:"MAIL_USE_AUTH,omitempty"`
	MailUsername             string        `default:"" validate:"" yaml:"MAIL_USERNAME,omitempty" json:"MAIL_USERNAME,omitempty"`
	MailUseTls               bool          `default:"false" validate:"" yaml:"MAIL_USE_TLS,omitempty" json:"MAIL_USE_TLS,omitempty"`
}

// NewEmailFieldGroup creates a new EmailFieldGroup
func NewEmailFieldGroup(fullConfig map[string]interface{}) (*EmailFieldGroup, error) {
	newEmailFieldGroup := &EmailFieldGroup{}
	defaults.Set(newEmailFieldGroup)

	if value, ok := fullConfig["BLACKLISTED_EMAIL_DOMAINS"]; ok {
		newEmailFieldGroup.BlacklistedEmailDomains, ok = value.([]interface{})
		if !ok {
			return newEmailFieldGroup, errors.New("BLACKLISTED_EMAIL_DOMAINS must be of type []interface{}")
		}
	}
	if value, ok := fullConfig["FEATURE_BLACKLISTED_EMAILS"]; ok {
		newEmailFieldGroup.FeatureBlacklistedEmails, ok = value.(bool)
		if !ok {
			return newEmailFieldGroup, errors.New("FEATURE_BLACKLISTED_EMAILS must be of type bool")
		}
	}
	if value, ok := fullConfig["FEATURE_MAILING"]; ok {
		newEmailFieldGroup.FeatureMailing, ok = value.(bool)
		if !ok {
			return newEmailFieldGroup, errors.New("FEATURE_MAILING must be of type bool")
		}
	}
	if value, ok := fullConfig["MAIL_DEFAULT_SENDER"]; ok {
		newEmailFieldGroup.MailDefaultSender, ok = value.(string)
		if !ok {
			return newEmailFieldGroup, errors.New("MAIL_DEFAULT_SENDER must be of type string")
		}
	}
	if value, ok := fullConfig["MAIL_PASSWORD"]; ok {
		newEmailFieldGroup.MailPassword, ok = value.(string)
		if !ok {
			return newEmailFieldGroup, errors.New("MAIL_PASSWORD must be of type string")
		}
	}
	if value, ok := fullConfig["MAIL_PORT"]; ok {
		newEmailFieldGroup.MailPort, ok = value.(int)
		if !ok {
			return newEmailFieldGroup, errors.New("MAIL_PORT must be of type int")
		}
	}
	if value, ok := fullConfig["MAIL_SERVER"]; ok {
		newEmailFieldGroup.MailServer, ok = value.(string)
		if !ok {
			return newEmailFieldGroup, errors.New("MAIL_SERVER must be of type string")
		}
	}
	if value, ok := fullConfig["MAIL_USERNAME"]; ok {
		newEmailFieldGroup.MailUsername, ok = value.(string)
		if !ok {
			return newEmailFieldGroup, errors.New("MAIL_USERNAME must be of type string")
		}
	}
	if value, ok := fullConfig["MAIL_USE_TLS"]; ok {
		newEmailFieldGroup.MailUseTls, ok = value.(bool)
		if !ok {
			return newEmailFieldGroup, errors.New("MAIL_USE_TLS must be of type bool")
		}
	}

	return newEmailFieldGroup, nil
}
