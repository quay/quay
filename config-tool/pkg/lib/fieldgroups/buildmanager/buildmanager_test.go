package buildmanager

import (
	"fmt"
	"reflect"
	"testing"

	"github.com/jojomi/go-spew/spew"
	"gopkg.in/yaml.v3"
)

func TestValidateBuildManager(t *testing.T) {

	before := []byte(`
FEATURE_BUILD_SUPPORT: true
BUILD_MANAGER: 
  - ephemeral
  - ALLOWED_WORKER_COUNT: 1
    ORCHESTRATOR_PREFIX: buildman/production/
    ORCHESTRATOR:
      REDIS_HOST: quay-redis-host
      REDIS_PASSWORD: quay-redis-password
      REDIS_SSL: true
      REDIS_SKIP_KEYSPACE_EVENT_SETUP: false
    EXECUTORS:
      - EXECUTOR: kubernetes
        BUILDER_NAMESPACE: builder
        K8S_API_SERVER: api.openshift.somehost.org:6443
        VOLUME_SIZE: 8G
        KUBERNETES_DISTRIBUTION: openshift
        CONTAINER_MEMORY_LIMITS: 5120Mi
        CONTAINER_CPU_LIMITS: 1000m
        CONTAINER_MEMORY_REQUEST: 3968Mi
        CONTAINER_CPU_REQUEST: 500m
        NODE_SELECTOR_LABEL_KEY: beta.kubernetes.io/instance-type
        NODE_SELECTOR_LABEL_VALUE: n1-standard-4
        CONTAINER_RUNTIME: podman
        SERVICE_ACCOUNT_NAME: name
        SERVICE_ACCOUNT_TOKEN: name
        QUAY_USERNAME: brew-username
        QUAY_PASSWORD: brew-password
        WORKER_IMAGE: <registry>/quay-quay-builder
        WORKER_TAG: some_tag
        BUILDER_VM_CONTAINER_IMAGE: '<registry>/quay-quay-builder-qemu-rhcos:v3.4.0'
        SETUP_TIME: 180
        MINIMUM_RETRY_THRESHOLD: 1
        SSH_AUTHORIZED_KEYS:
          - ssh-rsa 12345 someuser@email.com
          - ssh-rsa 67890 someuser2@email.com
`)

	var confMap BuildManagerFieldGroup
	err := yaml.Unmarshal(before, &confMap)
	if err != nil {
		t.Errorf(err.Error())
		return
	}

	after, err := yaml.Marshal(confMap)
	if err != nil {
		t.Errorf(err.Error())
		return
	}

	fmt.Println(string(after))

	var confMap2 BuildManagerFieldGroup
	err = yaml.Unmarshal(after, &confMap2)
	if err != nil {
		t.Errorf("fail" + err.Error())
		return
	}

	if !reflect.DeepEqual(confMap, confMap2) {
		t.Errorf("unequal")
		spew.Dump(confMap)
		spew.Dump(confMap2)
		return
	}

	// // Define test data
	// var tests = []struct {
	// 	name   string
	// 	config map[string]interface{}
	// 	want   string
	// }{{name: "my_test",
	// 	config: confMap,
	// 	want:   "invalid"},
	// }

	// // Iterate through tests
	// for _, tt := range tests {

	// 	// Run specific test
	// 	t.Run(tt.name, func(t *testing.T) {

	// 		// Get validation result
	// 		fg, err := NewBuildManagerFieldGroup(tt.config)
	// 		if err != nil && tt.want != "typeError" {
	// 			t.Errorf("Expected %s. Received %s", tt.want, err.Error())
	// 		}

	// 		opts := shared.Options{
	// 			Mode: "testing",
	// 		}

	// 		validationErrors := fg.Validate(opts)

	// 		// Get result type
	// 		received := ""
	// 		if len(validationErrors) == 0 {
	// 			received = "valid"
	// 		} else {
	// 			received = "invalid"
	// 		}

	// 		// Compare with expected
	// 		if tt.want != received {
	// 			t.Errorf("Expected %s. Received %s", tt.want, received)
	// 			for _, err := range validationErrors {
	// 				t.Errorf(err.Message)
	// 			}
	// 		}

	// 	})
	// }

}
