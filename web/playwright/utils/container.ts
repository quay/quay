/**
 * Container utilities for Playwright e2e tests
 *
 * These utilities provide container operations for pushing test images
 * to the registry during e2e tests. Supports both podman and docker.
 */

import {exec, execFileSync} from 'child_process';
import {promisify} from 'util';
import {API_URL} from './config';

const execAsync = promisify(exec);

// Extract registry host from API_URL (e.g., 'localhost:8080')
const REGISTRY_HOST = new URL(API_URL).host;

// Cache the detected container runtime
let containerRuntime: string | null = null;

// Deduplicate the busybox pull — concurrent workers share one Promise
let busyboxPullPromise: Promise<void> | null = null;

// Per-user auth file paths — avoids parallel workers overwriting each other's
// credentials in the shared podman/docker credential store.
const userAuthFiles = new Map<string, string>();

function getAuthFile(username: string): string {
  if (!userAuthFiles.has(username)) {
    const safeName = username.replace(/[^a-zA-Z0-9_-]/g, '_');
    userAuthFiles.set(username, `/tmp/quay-auth-${safeName}.json`);
  }
  return userAuthFiles.get(username)!;
}

function credsFlag(
  runtime: string,
  username: string,
  password: string,
): string {
  if (runtime === 'podman') {
    return `--creds=${username}:${password}`;
  }
  return '';
}

async function ensureLogin(
  runtime: string,
  username: string,
  password: string,
  tlsFlag: string,
): Promise<void> {
  if (runtime !== 'podman') {
    const authFile = getAuthFile(username);
    await execAsync(
      `${runtime} --config $(dirname ${authFile}) login ${REGISTRY_HOST} -u ${username} -p ${password} ${tlsFlag}`.trim(),
    );
  }
}

function authFileFlag(runtime: string, username: string): string {
  if (runtime !== 'podman') {
    return `--config $(dirname ${getAuthFile(username)})`;
  }
  return '';
}

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
 * Execute a shell command, retrying with fixed 1s delays on failure.
 *
 * @param cmd - Shell command to run
 * @param maxAttempts - Maximum number of attempts (default: 5)
 */
async function retryPush(cmd: string, maxAttempts = 5): Promise<void> {
  let lastErr: unknown;
  for (let i = 0; i < maxAttempts; i++) {
    try {
      await execAsync(cmd);
      return;
    } catch (err) {
      lastErr = err;
      await new Promise((r) => setTimeout(r, 1000));
    }
  }
  throw lastErr;
}

/**
 * Push a test image to the registry using podman or docker.
 *
 * Uses busybox as a minimal test image. Login and busybox pull are
 * deduplicated per process so concurrent workers don't race on them.
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

  await ensureLogin(runtime, username, password, tlsFlag);

  const busyboxImage = 'quay.io/prometheus/busybox:latest';

  // Pull busybox once per process; concurrent callers wait on the same Promise.
  if (!busyboxPullPromise) {
    busyboxPullPromise = execAsync(`${runtime} pull ${busyboxImage}`).then(
      () => undefined,
    );
  }
  await busyboxPullPromise;

  await execAsync(`${runtime} tag ${busyboxImage} ${image}`);

  const creds = credsFlag(runtime, username, password);
  const authCfg = authFileFlag(runtime, username);

  await retryPush(
    `${runtime} ${authCfg} push ${image} ${creds} ${tlsFlag}`.trim(),
  );

  if (!process.env.CI) {
    await execAsync(`${runtime} rmi ${image}`);
  }
}

/**
 * Push an image with a unique layer to the registry, guaranteeing
 * unique blob digests (no deduplication with prior pushes).
 */
export async function pushUniqueImage(
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

  await ensureLogin(runtime, username, password, tlsFlag);

  const uniqueId = `${Date.now()}-${Math.random().toString(36).slice(2)}`;
  const tmpDir = `/tmp/quay-unique-img-${uniqueId}`;
  await execAsync(
    `mkdir -p ${tmpDir} && echo "${uniqueId}" > ${tmpDir}/unique && ` +
      `printf 'FROM busybox\\nCOPY unique /unique\\n' > ${tmpDir}/Dockerfile`,
  );
  try {
    const formatFlag = runtime === 'podman' ? '--format docker' : '';
    await execAsync(
      `${runtime} build ${formatFlag} --tag ${image} ${tmpDir}`.trim(),
    );
    const creds = credsFlag(runtime, username, password);
    const authCfg = authFileFlag(runtime, username);
    await retryPush(
      `${runtime} ${authCfg} push ${image} ${creds} ${tlsFlag}`.trim(),
    );
  } finally {
    await execAsync(`rm -rf ${tmpDir}`).catch(() => undefined);
    if (!process.env.CI) {
      await execAsync(`${runtime} rmi ${image}`).catch(() => undefined);
    }
  }
}

/**
 * Pull an image from the registry. Removes it afterwards to avoid
 * polluting the local image store during tests.
 */
export async function pullImage(
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

  await ensureLogin(runtime, username, password, tlsFlag);

  const creds = credsFlag(runtime, username, password);
  const authCfg = authFileFlag(runtime, username);

  await execAsync(
    `${runtime} ${authCfg} pull ${image} ${creds} ${tlsFlag}`.trim(),
  );
  await execAsync(`${runtime} rmi ${image}`).catch(() => undefined);
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

  // Use skopeo to copy the entire multi-arch manifest list in one command.
  // Retry for the same repo-init race as pushImage.
  await retryPush(
    `skopeo copy --all docker://${sourceImage} docker://${targetImage} --dest-tls-verify=false --dest-creds=${username}:${password}`,
  );
}

/**
 * Attach an OCI artifact to a repository using oras.
 *
 * @param namespace - Organization/namespace
 * @param repo - Repository name
 * @param tag - Tag to attach to
 * @param username - Registry username
 * @param password - Registry password
 * @param artifactType - OCI artifact type
 * @param annotation - Annotation key=value
 * @param filePath - Path to the file to attach
 */
export function orasAttach(
  namespace: string,
  repo: string,
  tag: string,
  username: string,
  password: string,
  artifactType: string,
  annotation: string,
  filePath: string,
): void {
  const ref = `${REGISTRY_HOST}/${namespace}/${repo}:${tag}`;

  execFileSync(
    'oras',
    [
      'attach',
      ref,
      '--insecure',
      `--username=${username}`,
      `--password=${password}`,
      `--artifact-type=${artifactType}`,
      `--annotation=${annotation}`,
      filePath,
    ],
    {stdio: 'pipe', timeout: 60_000},
  );
}

/**
 * Push an image in OCI manifest format to the registry using skopeo.
 *
 * Uses `--format=oci` to guarantee the manifest uses the OCI content type,
 * which exercises a different code path in the security scanner than
 * Docker v2 schema 2 manifests.
 *
 * @example
 * ```typescript
 * await pushOCIImage('myorg', 'myrepo', 'latest', 'testuser', 'password');
 * ```
 */
export async function pushOCIImage(
  namespace: string,
  repo: string,
  tag: string,
  username: string,
  password: string,
): Promise<void> {
  const targetImage = `${REGISTRY_HOST}/${namespace}/${repo}:${tag}`;
  const sourceImage = 'quay.io/prometheus/busybox:latest';

  await retryPush(
    `skopeo copy --format=oci --override-os=linux --override-arch=amd64 docker://${sourceImage} docker://${targetImage} --dest-tls-verify=false --dest-creds=${username}:${password}`,
  );
}

/**
 * Check if oras CLI is available on the system.
 */
export async function isOrasAvailable(): Promise<boolean> {
  try {
    await execAsync('oras version');
    return true;
  } catch {
    return false;
  }
}

/**
 * Check if skopeo CLI is available on the system.
 */
export async function isSkopeoAvailable(): Promise<boolean> {
  try {
    await execAsync('skopeo --version');
    return true;
  } catch {
    return false;
  }
}

/**
 * Check if regctl CLI is available on the system.
 */
export async function isRegctlAvailable(): Promise<boolean> {
  try {
    await execAsync('regctl version');
    return true;
  } catch {
    return false;
  }
}

/**
 * List tags for a repository using skopeo.
 *
 * @returns Array of tag name strings
 */
export async function skopeoListTags(
  namespace: string,
  repo: string,
  username: string,
  password: string,
): Promise<string[]> {
  const ref = `docker://${REGISTRY_HOST}/${namespace}/${repo}`;
  const {stdout} = await execAsync(
    `skopeo list-tags ${ref} --tls-verify=false --creds=${username}:${password}`,
  );
  const result = JSON.parse(stdout);
  return result.Tags ?? [];
}

/**
 * List tags for a repository using regctl.
 *
 * @returns Array of tag name strings
 */
export async function regctlListTags(
  namespace: string,
  repo: string,
  username: string,
  password: string,
): Promise<string[]> {
  const ref = `${REGISTRY_HOST}/${namespace}/${repo}`;
  const hostCfg = `reg=${REGISTRY_HOST},user=${username},pass=${password},tls=disabled`;
  const {stdout} = await execAsync(`regctl tag ls --host ${hostCfg} ${ref}`);
  return stdout
    .split('\n')
    .map((line) => line.trim())
    .filter((line) => line.length > 0);
}
