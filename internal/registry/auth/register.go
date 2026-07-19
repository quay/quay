package auth

import (
	"fmt"
	"sync"

	distauth "github.com/distribution/distribution/v3/registry/auth"
)

const (
	// DistributionBackendName is the registered upstream auth backend name.
	DistributionBackendName = "quaytoken"
	// DistributionControllerOption carries the prebuilt controller through
	// Distribution's weakly typed plugin options.
	DistributionControllerOption = "controller"
)

// Distribution exposes custom access controllers only through a process-wide
// plugin registry. This once/error pair is the constrained exception to Go
// OMR's no-global-state rule: it registers a stateless adapter and never stores
// a controller, key, database handle, or other runtime dependency globally.
var (
	registerOnce sync.Once
	registerErr  error
)

// RegisterDistributionAdapter registers the stateless quaytoken adapter once.
func RegisterDistributionAdapter() error {
	registerOnce.Do(func() {
		registerErr = distauth.Register(DistributionBackendName, distauth.InitFunc(func(options map[string]interface{}) (distauth.AccessController, error) {
			controller, ok := options[DistributionControllerOption].(*Controller)
			if !ok || controller == nil {
				return nil, fmt.Errorf("%q must be set to *auth.Controller", DistributionControllerOption)
			}
			return controller, nil
		}))
	})
	return registerErr
}
