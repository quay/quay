# Installer & Quadlet Patterns

Guide for working on the Go installer CLI (`internal/installer/`) and Quadlet/systemd integration (`internal/system/`).

## Overview

The installer CLI (`quay install`) deploys the registry as a Quadlet-managed systemd service. It supports both fresh installs and in-place upgrades. The entry point is `internal/cmd/install.go`, which calls `installer.Run()`.

Key source files:

| File | Purpose |
|------|---------|
| `internal/cmd/install.go` | CLI flag definitions and entry point |
| `internal/installer/installer.go` | Install/upgrade orchestration, `resolvePort()` |
| `internal/installer/validate.go` | Input validation (`ValidateHostname`, `ValidatePort`) |
| `internal/system/quadlet.go` | Quadlet file generation, `registryContainerPort` constant |
| `internal/system/env.go` | Root vs user mode detection, Quadlet directory paths |
| `internal/system/systemd.go` | systemctl start/stop/reload |

## Quadlet PublishPort Mapping

The container always listens on a fixed internal port defined by the `registryContainerPort` constant in `internal/system/quadlet.go` (currently `8443`). The Quadlet `PublishPort` directive maps `hostPort:containerPort`.

**Correct:** `PublishPort=9443:8443` (host port 9443 forwarded to container port 8443)

**Wrong:** `PublishPort=9443:9443` (the container does not listen on 9443)

When generating or modifying Quadlet files, always use `registryContainerPort` for the container side. Never copy the host port to both sides of the mapping.

```go
// Correct - uses the constant for the container side
content := fmt.Sprintf("PublishPort=%s:%s", spec.Port, registryContainerPort)

// Wrong - maps port to itself
content := fmt.Sprintf("PublishPort=%s:%s", spec.Port, spec.Port)
```

## Upgrade Path State Preservation

The installer detects existing installations via `quadlet.Exists()`. When upgrading, deployment-time settings (port, hostname, data directory) must be read from the existing Quadlet file, not defaulted from CLI flag defaults. This prevents upgrades from silently changing the deployment configuration.

### The resolvePort() Pattern

`resolvePort()` in `internal/installer/installer.go` is the canonical example:

```go
func (inst *Installer) resolvePort(requestedPort string, upgrading bool) (string, error) {
    port := requestedPort
    if port == "" {
        if upgrading {
            // Read from existing Quadlet file
            port, err = inst.quadlet.HostPort(quadletServiceName)
        } else {
            // Fresh install: use hardcoded default
            port = defaultPort
        }
    }
    // Validate regardless of source
    return port, ValidatePort(port)
}
```

The resolution logic:

1. If the user provides an explicit value via the CLI flag, use it (overrides everything).
2. If upgrading and no explicit value, read from the existing Quadlet file (`HostPort()`).
3. If fresh install and no explicit value, use the hardcoded default (`defaultPort`).

### Why This Matters

Without this pattern, an upgrade with `quay install -hostname registry.example.com` (no `-port` flag) would reset the port from a previously configured custom port (e.g., 9443) back to the default 8443. The health check URL and final output would also use the wrong port, causing the upgrade to appear to fail even if the service started correctly.

## Config Resolution Pattern for New Flags

When adding a new CLI flag that represents a deployment-time decision (something stored in the Quadlet file), follow this checklist:

1. **Define the flag with an empty default** in `internal/cmd/install.go`, not with the production default value. This allows the installer to distinguish "user provided a value" from "user did not provide a value."

   ```go
   // Correct - empty default lets resolveX() detect omission
   port := fs.String("port", "", "HTTPS port (default 8443; preserved on upgrade)")

   // Wrong - cannot distinguish "user wants 8443" from "user didn't specify"
   port := fs.String("port", "8443", "HTTPS port")
   ```

2. **Add a resolve function** following the `resolvePort()` pattern: explicit value > existing state > hardcoded default.

3. **Add a reader method** to `QuadletManager` (like `HostPort()`) that parses the existing Quadlet file to extract the current value.

4. **Use the resolved value everywhere** downstream: Quadlet generation, health check URL, log output, etc. Never use the CLI flag default directly after resolution.

5. **Write tests covering all three resolution paths:**
   - Explicit value on fresh install
   - Explicit value on upgrade (should override existing)
   - Omitted value on upgrade (should preserve existing)
   - Omitted value on fresh install (should use hardcoded default)

   See `TestUpgradeUsesEffectivePort` and `TestResolvePortDefaultsFreshInstall` in `internal/installer/installer_test.go`.

## Testing

Run installer and Quadlet tests:

```bash
go test ./internal/installer/... -v
go test ./internal/system/... -v
```

Tests use `t.TempDir()` for Quadlet file paths and a `recordingServiceManager` stub (defined in `installer_test.go`) to capture systemctl calls without requiring a real systemd environment.
