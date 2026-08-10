/**
 * Container utilities for Playwright e2e tests
 *
 * These utilities provide container operations for pushing test images
 * to the registry during e2e tests. Supports both podman and docker.
 */

import {exec, execFileSync, execSync} from 'child_process';
import {promisify} from 'util';
import {API_URL} from './config';

const execAsync = promisify(exec);

// Extract registry host from API_URL (e.g., 'localhost:8080')
const REGISTRY_HOST = new URL(API_URL).host;

// Cache the detected container runtime
let containerRuntime: string | null = null;

// Deduplicate the busybox pull — concurrent workers share one Promise
let busyboxPullPromise: Promise<void> | null = null;

// Track registries we've already logged into so each worker logs in only once.
// Quay rate-limits concurrent logins (HTTP 429) when many workers fire at once.
const loggedInRegistries = new Set<string>();

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
  const loginKey = `${runtime}:${REGISTRY_HOST}:${username}`;

  if (!loggedInRegistries.has(loginKey)) {
    await execAsync(
      `${runtime} login ${REGISTRY_HOST} -u ${username} -p ${password} ${tlsFlag}`.trim(),
    );
    loggedInRegistries.add(loginKey);
  }

  const busyboxImage = 'quay.io/prometheus/busybox:latest';

  // Pull busybox once per process; concurrent callers wait on the same Promise.
  if (!busyboxPullPromise) {
    busyboxPullPromise = execAsync(`${runtime} pull ${busyboxImage}`).then(
      () => undefined,
    );
  }
  await busyboxPullPromise;

  await execAsync(`${runtime} tag ${busyboxImage} ${image}`);

  // Push with retries — repo creation is async; the push can race against
  // Quay's backend committing the repo, especially with many parallel workers.
  await retryPush(`${runtime} push ${image} ${tlsFlag}`.trim());

  // Cleanup local image (skip in CI — ephemeral runners don't need disk reclaimed)
  if (!process.env.CI) {
    await execAsync(`${runtime} rmi ${image}`);
  }
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
 * Push an image in OCI manifest format to the registry using skopeo.
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
 * Pull an image from the registry using podman or docker.
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
