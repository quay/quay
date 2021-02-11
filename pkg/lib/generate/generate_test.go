package generate

import (
	"testing"

	"github.com/jojomi/go-spew/spew"
)

// TestValidateSchema tests the ValidateSchema function
func TestGenerateBaseConfig(t *testing.T) {

	options := AioiInputOptions{
		serverHostname: "myHostname",
		databaseURI:    "postgres://user:pass@192.168.250.159/quay",
		redisHostname:  "192.168.250.159",
		redisPassword:  "strongpassword",
	}

	baseConfig, err := GenerateBaseConfig(options)
	if err != nil {
		t.Errorf(err.Error())
	}

	spew.Dump(baseConfig)
}
