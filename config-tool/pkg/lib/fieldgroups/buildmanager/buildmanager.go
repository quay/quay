package buildmanager

import (
	"fmt"

	"github.com/creasty/defaults"
	"gopkg.in/yaml.v3"
)

// BuildManagerFieldGroup represents the BuildManager config fields
type BuildManagerFieldGroup struct {
	FeatureBuildSupport bool                    `default:"" validate:"" json:"FEATURE_BUILD_SUPPORT" yaml:"FEATURE_BUILD_SUPPORT"`
	BuildManagerConfig  *BuildManagerDefinition `default:"" validate:"" json:"BUILD_MANAGER,omitempty" yaml:"BUILD_MANAGER,omitempty"`
}

// BuildManagerDefinition represents a single storage configuration as a tuple (Name, Arguments)
type BuildManagerDefinition struct {
	Name string            `default:"" validate:"" json:",inline" yaml:",inline"`
	Args *BuildManagerArgs `default:"" validate:"" json:",inline" yaml:",inline"`
}

// BuildManagerArgs represents the arguments in the second value of a definition tuple
type BuildManagerArgs struct {
	// Args for ephemeral
	AllowedWorkerCount int               `default:"" validate:"" json:"ALLOWED_WORKER_COUNT,omitempty" yaml:"ALLOWED_WORKER_COUNT,omitempty"`
	OrchestratorPrefix string            `default:"" validate:"" json:"ORCHESTRATOR_PREFIX,omitempty" yaml:"ORCHESTRATOR_PREFIX,omitempty"`
	Orchestrator       *OrchestratorArgs `default:"" validate:"" json:"ORCHESTRATOR,omitempty" yaml:"ORCHESTRATOR,omitempty"`
	Executors          []*ExecutorArgs   `default:"" validate:"" json:"EXECUTORS,omitempty" yaml:"EXECUTORS,omitempty"`
}

// OrchestratorArgs represents the arguments in the orchestrator object
type OrchestratorArgs struct {
	RedisHost                   string `default:"" validate:"" json:"REDIS_HOST,omitempty" yaml:"REDIS_HOST,omitempty"`
	RedisPassword               string `default:"" validate:"" json:"REDIS_PASSWORD,omitempty" yaml:"REDIS_PASSWORD,omitempty"`
	RedisSSL                    bool   `default:"" validate:"" json:"REDIS_SSL" yaml:"REDIS_SSL"`
	RedisSkipKeyspaceEventSetup bool   `default:"" validate:"" json:"REDIS_SKIP_KEYSPACE_EVENT_SETUP" yaml:"REDIS_SKIP_KEYSPACE_EVENT_SETUP"`
}

// ExecutorArgs represents the arguments in an executor object
type ExecutorArgs struct {
	Executor                string        `default:"" validate:"" json:"EXECUTOR,omitempty" yaml:"EXECUTOR,omitempty"`
	BuilderNamespace        string        `default:"" validate:"" json:"BUILDER_NAMESPACE,omitempty" yaml:"BUILDER_NAMESPACE,omitempty"`
	K8sAPIServer            string        `default:"" validate:"" json:"K8S_API_SERVER,omitempty" yaml:"K8S_API_SERVER,omitempty"`
	VolumeSize              string        `default:"" validate:"" json:"VOLUME_SIZE,omitempty" yaml:"VOLUME_SIZE,omitempty"`
	KubernetesDistribution  string        `default:"" validate:"" json:"KUBERNETES_DISTRIBUTION,omitempty" yaml:"KUBERNETES_DISTRIBUTION,omitempty"`
	ContainerMemoryLimits   string        `default:"" validate:"" json:"CONTAINER_MEMORY_LIMITS,omitempty" yaml:"CONTAINER_MEMORY_LIMITS,omitempty"`
	ContainerCPULimits      string        `default:"" validate:"" json:"CONTAINER_CPU_LIMITS,omitempty" yaml:"CONTAINER_CPU_LIMITS,omitempty"`
	ContainerMemoryRequest  string        `default:"" validate:"" json:"CONTAINER_MEMORY_REQUEST,omitempty" yaml:"CONTAINER_MEMORY_REQUEST,omitempty"`
	ContainerCPURequest     string        `default:"" validate:"" json:"CONTAINER_CPU_REQUEST,omitempty" yaml:"CONTAINER_CPU_REQUEST,omitempty"`
	NodeSelectorLabelKey    string        `default:"" validate:"" json:"NODE_SELECTOR_LABEL_KEY,omitempty" yaml:"NODE_SELECTOR_LABEL_KEY,omitempty"`
	NodeSelectorLabelValue  string        `default:"" validate:"" json:"NODE_SELECTOR_LABEL_VALUE,omitempty" yaml:"NODE_SELECTOR_LABEL_VALUE,omitempty"`
	ContainerRuntime        string        `default:"" validate:"" json:"CONTAINER_RUNTIME,omitempty" yaml:"CONTAINER_RUNTIME,omitempty"`
	ServiceAccountName      string        `default:"" validate:"" json:"SERVICE_ACCOUNT_NAME,omitempty" yaml:"SERVICE_ACCOUNT_NAME,omitempty"`
	ServiceAccountToken     string        `default:"" validate:"" json:"SERVICE_ACCOUNT_TOKEN,omitempty" yaml:"SERVICE_ACCOUNT_TOKEN,omitempty"`
	QuayUsername            string        `default:"" validate:"" json:"QUAY_USERNAME,omitempty" yaml:"QUAY_USERNAME,omitempty"`
	QuayPassword            string        `default:"" validate:"" json:"QUAY_PASSWORD,omitempty" yaml:"QUAY_PASSWORD,omitempty"`
	WorkerImage             string        `default:"" validate:"" json:"WORKER_IMAGE,omitempty" yaml:"WORKER_IMAGE,omitempty"`
	WorkerTag               string        `default:"" validate:"" json:"WORKER_TAG,omitempty" yaml:"WORKER_TAG,omitempty"`
	BuilderVMContainerImage string        `default:"" validate:"" json:"BUILDER_VM_CONTAINER_IMAGE,omitempty" yaml:"BUILDER_VM_CONTAINER_IMAGE,omitempty"`
	SetupTime               int           `default:"" validate:"" json:"SETUP_TIME,omitempty" yaml:"SETUP_TIME,omitempty"`
	MinimumRetryThreshold   int           `default:"" validate:"" json:"MINIMUM_RETRY_THRESHOLD" yaml:"MINIMUM_RETRY_THRESHOLD"`
	SSHAuthorizedKeys       []interface{} `default:"" validate:"" json:"SSH_AUTHORIZED_KEYS,omitempty" yaml:"SSH_AUTHORIZED_KEYS,omitempty"`
	// ec2 fields
	EC2Region           string        `default:"" validate:"" json:"EC2_REGION,omitempty" yaml:"EC2_REGION,omitempty"`
	CoreOSAMI           string        `default:"" validate:"" json:"COREOS_AMI,omitempty" yaml:"COREOS_AMI,omitempty"`
	AwsAccessKey        string        `default:"" validate:"" json:"AWS_ACCESS_KEY,omitempty" yaml:"AWS_ACCESS_KEY,omitempty"`
	AwsSecretKey        string        `default:"" validate:"" json:"AWS_SECRET_KEY,omitempty" yaml:"AWS_SECRET_KEY,omitempty"`
	EC2InstanceType     string        `default:"" validate:"" json:"EC2_INSTANCE_TYPE,omitempty" yaml:"EC2_INSTANCE_TYPE,omitempty"`
	EC2VPCSubnetID      string        `default:"" validate:"" json:"EC2_VPC_SUBNET_ID,omitempty" yaml:"EC2_VPC_SUBNET_ID,omitempty"`
	EC2SecurityGroupIDs []interface{} `default:"" validate:"" json:"EC2_SECURITY_GROUP_IDS,omitempty" yaml:"EC2_SECURITY_GROUP_IDS,omitempty"`
	EC2KeyName          string        `default:"" validate:"" json:"EC2_KEY_NAME,omitempty" yaml:"EC2_KEY_NAME,omitempty"`
	BlockDeviceSize     int           `default:"" validate:"" json:"BLOCK_DEVICE_SIZE,omitempty" yaml:"BLOCK_DEVICE_SIZE,omitempty"`
}

// NewBuildManagerFieldGroup creates a new BitbucketBuildTriggerFieldGroup
func NewBuildManagerFieldGroup(fullConfig map[string]interface{}) (*BuildManagerFieldGroup, error) {
	newBuildManagerFieldGroup := &BuildManagerFieldGroup{}

	bytes, err := yaml.Marshal(fullConfig)
	if err != nil {
		return nil, err
	}

	err = yaml.Unmarshal(bytes, newBuildManagerFieldGroup)
	if err != nil {
		return nil, err
	}

	defaults.Set(newBuildManagerFieldGroup)

	return newBuildManagerFieldGroup, nil
}

func (bm *BuildManagerDefinition) UnmarshalYAML(value *yaml.Node) error {

	// Ensure correct shape
	if len(value.Content) != 2 || value.Content[0].Tag != "!!str" || value.Content[1].Tag != "!!map" {
		return fmt.Errorf("Incorrect format for value BUILD_MANAGER")
	}

	bm.Name = value.Content[0].Value
	err := value.Content[1].Decode(&bm.Args)
	if err != nil {
		return err
	}

	return nil

}

func (bm *BuildManagerDefinition) MarshalYAML() (interface{}, error) {

	name := &yaml.Node{
		Kind:  yaml.ScalarNode,
		Value: bm.Name,
	}

	args := &yaml.Node{}
	err := args.Encode(bm.Args)
	if err != nil {
		return nil, err
	}

	node := &yaml.Node{
		Kind:    yaml.SequenceNode,
		Content: []*yaml.Node{name, args},
	}

	return node, nil

}
