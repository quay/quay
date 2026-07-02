package v1

import "strings"

// RepositoryPath returns a matcher for routes containing Quay's apirepopath
// semantics: the namespace is the first path segment and the repository name
// may contain additional slash-separated segments before suffix.
func RepositoryPath(paramName, prefix, suffix string) Matcher {
	return MatchFunc(func(path string) (Params, bool) {
		if !strings.HasPrefix(path, prefix) || !strings.HasSuffix(path, suffix) {
			return nil, false
		}

		repositoryPath := strings.TrimSuffix(strings.TrimPrefix(path, prefix), suffix)
		namespace, repository, ok := strings.Cut(repositoryPath, "/")
		if !ok || namespace == "" || repository == "" {
			return nil, false
		}

		return Params{
			"namespace": namespace,
			paramName:   repository,
		}, true
	})
}
