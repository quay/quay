package repomirror

// Fields returns a list of strings representing the fields in this field group
func (fg *RepoMirrorFieldGroup) Fields() []string {
	return []string{"FEATURE_REPO_MIRROR", "REPO_MIRROR_INTERVAL", "REPO_MIRROR_SERVER_HOSTNAME", "REPO_MIRROR_TLS_VERIFY"}
}
