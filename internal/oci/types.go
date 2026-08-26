package oci

// RepositoryName identifies a container image repository by namespace and name.
type RepositoryName struct {
	Namespace string
	Name      string
}

func (r RepositoryName) String() string {
	if r.Namespace == "" {
		return r.Name
	}
	return r.Namespace + "/" + r.Name
}
