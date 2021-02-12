package generate

import (
	"testing"

	"github.com/jojomi/go-spew/spew"
)

// TestValidateSchema tests the ValidateSchema function
func TestGenerateBaseConfig(t *testing.T) {

	options := AioiInputOptions{
		ServerHostname: "myHostname",
		DatabaseURI:    "postgres://user:pass@192.168.250.159/quay",
		RedisHostname:  "192.168.250.159",
		RedisPassword:  "strongpassword",
	}

	baseConfig, err := GenerateBaseConfig(options)
	if err != nil {
		t.Errorf(err.Error())
	}

	spew.Dump(baseConfig)
}
