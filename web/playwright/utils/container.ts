/**
 * Container utilities for Playwright e2e tests
 *
 * These utilities provide container operations for pushing test images
 * to the registry during e2e tests. Supports both podman and docker.
 */

import {exec} from 'child_process';
import {promisify} from 'util';
import {API_URL} from './config';

const execAsync = promisify(exec);

// Extract registry host from API_URL (e.g., 'localhost:8080')
const REGISTRY_HOST = new URL(API_URL).host;

// Cache the detected container runtime
let containerRuntime: string | null = null;

/**
 * Detect available container runtime (podman or docker)
 *
 * @returns 'podman', 'docker', or null if neither is available
 */
async function detectContainerRuntime(): Promise<string | null> {
  if (containerRuntime !== null) {
    return containerRuntime;
  }

  // Prefer podman, fall back to docker
  for (const runtime of ['podman', 'docker']) {
    try {
      await execAsync(`${runtime} --version`);
      containerRuntime = runtime;
      return runtime;
    } catch {
      // Try next runtime
    }
  }
  return null;
}

/**
 * Push a test image to the registry using podman or docker
 *
 * Uses busybox as a minimal test image
 *
 * @example
 * ```typescript
 * await pushImage('myorg', 'myrepo', 'latest', 'testuser', 'password');
 * ```
 */
export async function pushImage(
  namespace: string,
  repo: string,
  tag: string,
  username: string,
  password: string,
): Promise<void> {
  const runtime = await detectContainerRuntime();
  if (!runtime) {
    throw new Error('No container runtime available (podman or docker)');
  }

  const image = `${REGISTRY_HOST}/${namespace}/${repo}:${tag}`;
  const tlsFlag = runtime === 'podman' ? '--tls-verify=false' : '';

  // Login to registry
  await execAsync(
    `${runtime} login ${REGISTRY_HOST} -u ${username} -p ${password} ${tlsFlag}`.trim(),
  );

  const busyboxImage = 'quay.io/prometheus/busybox:latest';

  // Pull busybox and tag it
  await execAsync(`${runtime} pull ${busyboxImage}`);
  await execAsync(`${runtime} tag ${busyboxImage} ${image}`);

  // Push to registry
  await execAsync(`${runtime} push ${image} ${tlsFlag}`.trim());

  // Cleanup local image
  await execAsync(`${runtime} rmi ${image}`);
}

/**
 * Check if a container runtime (podman or docker) is available
 *
 * @returns true if podman or docker is available
 */
export async function isContainerRuntimeAvailable(): Promise<boolean> {
  return (await detectContainerRuntime()) !== null;
}

/**
 * Push a multi-architecture manifest list to the registry.
 *
 * Uses docker.io/library/hello-world which is a real multi-arch image
 * with amd64, arm64, and other platform variants.
 *
 * @example
 * ```typescript
 * await pushMultiArchImage('myorg', 'myrepo', 'manifestlist', 'testuser', 'password');
 * ```
 */
export async function pushMultiArchImage(
  namespace: string,
  repo: string,
  tag: string,
  username: string,
  password: string,
): Promise<void> {
  const runtime = await detectContainerRuntime();
  if (!runtime) {
    throw new Error('No container runtime available (podman or docker)');
  }

  const targetImage = `${REGISTRY_HOST}/${namespace}/${repo}:${tag}`;
  const sourceImage = 'docker.io/library/hello-world:latest';
  const tlsFlag = runtime === 'podman' ? '--tls-verify=false' : '';
  const insecureFlag = runtime === 'docker' ? '--insecure' : '';

  // Login to registry
  await execAsync(
    `${runtime} login ${REGISTRY_HOST} -u ${username} -p ${password} ${tlsFlag}`.trim(),
  );

  // Use skopeo to copy the multi-arch manifest list
  // This preserves all architecture variants
  try {
    const destTls = runtime === 'podman' ? '--dest-tls-verify=false' : '';
    await execAsync(
      `skopeo copy --all ${destTls} docker://${sourceImage} docker://${targetImage}`.trim(),
    );
  } catch {
    // Fallback: try using the runtime's manifest commands
    if (runtime === 'podman') {
      // Pull all architectures and create manifest
      await execAsync(`${runtime} pull --all-tags ${sourceImage}`);
      await execAsync(
        `${runtime} push --all ${sourceImage} ${targetImage} ${tlsFlag}`.trim(),
      );
    } else {
      // Docker: use buildx imagetools
      await execAsync(
        `docker buildx imagetools create -t ${targetImage} ${sourceImage} ${insecureFlag}`.trim(),
      );
    }
  }
}

/**
 * Get the registry host for container operations
 */
export function getRegistryHost(): string {
  return REGISTRY_HOST;
}
