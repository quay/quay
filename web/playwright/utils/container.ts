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
 * Uses quay.io/prometheus/busybox:latest as the source image.
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
  const targetImage = `${REGISTRY_HOST}/${namespace}/${repo}:${tag}`;
  const sourceImage = 'quay.io/prometheus/busybox:latest';

  // Use skopeo to copy the entire multi-arch manifest list in one command
  // --all flag copies all architectures and the manifest list
  await execAsync(
    `skopeo copy --all docker://${sourceImage} docker://${targetImage} --dest-tls-verify=false --dest-creds=${username}:${password}`,
  );
}

/**
 * Push an image with known vulnerabilities to the registry.
 *
 * @example
 * ```typescript
 * await pushVulnerableImage('myorg', 'myrepo', 'vulns', 'testuser', 'password');
 * ```
 */
export async function pushVulnerableImage(
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
  const tlsFlag = runtime === 'podman' ? '--tls-verify=false' : '';

  // Use UBI8 8.1 - an older image with known CVEs that Clair will detect
  const sourceImage = 'registry.access.redhat.com/ubi8/ubi:8.1';

  // Login to registry
  await execAsync(
    `${runtime} login ${REGISTRY_HOST} -u ${username} -p ${password} ${tlsFlag}`.trim(),
  );

  // Only pull if not already cached locally
  try {
    await execAsync(`${runtime} image inspect ${sourceImage} >/dev/null 2>&1`);
  } catch {
    // Image not found locally, pull it
    await execAsync(`${runtime} pull ${sourceImage}`);
  }

  await execAsync(`${runtime} tag ${sourceImage} ${targetImage}`);

  // Push to registry (--remove-signatures needed for signed images like UBI)
  const sigFlag = runtime === 'podman' ? '--remove-signatures' : '';
  await execAsync(
    `${runtime} push ${targetImage} ${tlsFlag} ${sigFlag}`.trim(),
  );

  // Cleanup local target image (keep source cached for speed)
  await execAsync(`${runtime} rmi ${targetImage}`);
}
