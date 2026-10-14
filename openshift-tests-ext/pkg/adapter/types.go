// Package adapter provides the generic Quay exec adapter for the Quay OTE extension.
//
// The adapter is scenario-agnostic: every Quay scenario is a JSON ScenarioSpec.
package adapter

// ScenarioSpec is the only per-scenario input the adapter understands.
//
// The adapter is scenario-agnostic: it must not branch on Name, Tags, or any
// product type. Adding a scenario is another JSON object, not a new Go file.
type ScenarioSpec struct {
	// Name is the full OTE test name, e.g. "[sig-quay] Quay registry is operational".
	Name string `json:"name"`

	// Entrypoint is the program to exec (typically "/bin/bash").
	Entrypoint string `json:"entrypoint,omitempty"`

	// Args are extra argv passed to Entrypoint.
	// Example: ["-c", "${INTEROP_SCRIPTS_DIR}/check-quay-registry.sh"]
	Args []string `json:"args,omitempty"`

	// WorkDir is an optional chdir before exec.
	WorkDir string `json:"workDir,omitempty"`

	// Tags become ExtensionTestSpec.Labels.
	// Use them for suite membership ("quay") and filters ("SMOKE").
	Tags []string `json:"tags,omitempty"`

	// EnvVars is the scenario parameter surface.
	// Values override ambient env.
	EnvVars map[string]string `json:"envVars,omitempty"`

	// EnvFrom copies an ambient env key onto another name before EnvVars apply.
	EnvFrom map[string]string `json:"envFrom,omitempty"`

	// IncludeCEL / ExcludeCEL restrict when the spec is selected.
	// Example: `platform == "aws"` for cloud-specific tests.
	IncludeCEL string `json:"includeCEL,omitempty"`
	ExcludeCEL string `json:"excludeCEL,omitempty"`

	// Informing marks lifecycle=informing so failures do not fail the job.
	Informing bool `json:"informing,omitempty"`

	// Timeout is the adapter-enforced deadline (time.ParseDuration, e.g. "5m").
	Timeout string `json:"timeout,omitempty"`
}
