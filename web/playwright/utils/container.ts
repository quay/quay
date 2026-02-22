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
 * Result of attempting to push an image
 */
export interface PushResult {
  success: boolean;
  error?: string;
  stdout?: string;
  stderr?: string;
}

/**
 * Attempt to push an image and return the result (success/failure).
 *
 * Unlike `pushImage`, this function does not throw on failure.
 * Use this when testing scenarios where push should be blocked.
 *
 * @example
 * ```typescript
 * const result = await tryPushImage('myorg', 'myrepo', 'latest', 'user', 'pass');
 * expect(result.success).toBe(false);
 * expect(result.error).toContain('denied');
 * ```
 */
export async function tryPushImage(
  namespace: string,
  repo: string,
  tag: string,
  username: string,
  password: string,
): Promise<PushResult> {
  const runtime = await detectContainerRuntime();
  if (!runtime) {
    return {
      success: false,
      error: 'No container runtime available (podman or docker)',
    };
  }

  const image = `${REGISTRY_HOST}/${namespace}/${repo}:${tag}`;
  const tlsFlag = runtime === 'podman' ? '--tls-verify=false' : '';

  try {
    // Login to registry
    await execAsync(
      `${runtime} login ${REGISTRY_HOST} -u ${username} -p ${password} ${tlsFlag}`.trim(),
    );

    const busyboxImage = 'quay.io/prometheus/busybox:latest';

    // Pull busybox and tag it
    await execAsync(`${runtime} pull ${busyboxImage}`);
    await execAsync(`${runtime} tag ${busyboxImage} ${image}`);

    // Push to registry
    const {stdout, stderr} = await execAsync(
      `${runtime} push ${image} ${tlsFlag}`.trim(),
    );

    // Cleanup local image
    try {
      await execAsync(`${runtime} rmi ${image}`);
    } catch {
      // Ignore cleanup errors
    }

    return {success: true, stdout, stderr};
  } catch (error) {
    // Extract error message
    const err = error as Error & {
      stdout?: string;
      stderr?: string;
      message?: string;
    };
    return {
      success: false,
      error: err.stderr || err.message || String(error),
      stdout: err.stdout,
      stderr: err.stderr,
    };
  }
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
