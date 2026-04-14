/**
 * Image operation helpers for API tests.
 *
 * These wrap CLI tools (skopeo, oras) for pushing images and attaching
 * artifacts to the registry during test setup. They run synchronously
 * since test execution is serial.
 */

import {execFileSync, execSync} from 'child_process';

/**
 * Push an image to the registry using skopeo.
 *
 * Copies from a source registry (e.g. docker.io) to the test Quay instance.
 *
 * @param hostname - Registry hostname (e.g. "localhost:8080")
 * @param user - Registry username
 * @param pass - Registry password
 * @param source - Source image (e.g. "docker.io/library/busybox")
 * @param sourceTag - Source tag (e.g. "latest")
 * @param org - Target organization/namespace
 * @param repo - Target repository name
 * @param targetTag - Target tag
 */
export function pushImage(
  hostname: string,
  user: string,
  pass: string,
  source: string,
  sourceTag: string,
  org: string,
  repo: string,
  targetTag: string,
): void {
  const srcRef = `docker://${source}:${sourceTag}`;
  const destRef = `docker://${hostname}/${org}/${repo}:${targetTag}`;

  execFileSync(
    'skopeo',
    [
      'copy',
      srcRef,
      destRef,
      '--dest-tls-verify=false',
      `--dest-creds=${user}:${pass}`,
    ],
    {stdio: 'pipe', timeout: 120_000},
  );
}

/**
 * Push an image with all architectures (manifest list) using skopeo.
 */
export function pushImageAll(
  hostname: string,
  user: string,
  pass: string,
  source: string,
  sourceTag: string,
  org: string,
  repo: string,
  targetTag: string,
): void {
  const srcRef = `docker://${source}:${sourceTag}`;
  const destRef = `docker://${hostname}/${org}/${repo}:${targetTag}`;

  execFileSync(
    'skopeo',
    [
      'copy',
      '--all',
      srcRef,
      destRef,
      '--dest-tls-verify=false',
      `--dest-creds=${user}:${pass}`,
    ],
    {stdio: 'pipe', timeout: 120_000},
  );
}

/**
 * Attach an OCI artifact to a repository using oras.
 *
 * @param hostname - Registry hostname
 * @param namespace - Organization/namespace
 * @param repo - Repository name
 * @param user - Registry username
 * @param pass - Registry password
 * @param tag - Tag to attach to
 * @param artifactType - OCI artifact type
 * @param annotation - Annotation key=value
 * @param filePath - Path to the file to attach
 */
export function orasAttach(
  hostname: string,
  namespace: string,
  repo: string,
  user: string,
  pass: string,
  tag: string,
  artifactType: string,
  annotation: string,
  filePath: string,
): void {
  const ref = `${hostname}/${namespace}/${repo}:${tag}`;

  execFileSync(
    'oras',
    [
      'attach',
      ref,
      '--insecure',
      `--username=${user}`,
      `--password=${pass}`,
      `--artifact-type=${artifactType}`,
      `--annotation=${annotation}`,
      filePath,
    ],
    {stdio: 'pipe', timeout: 60_000},
  );
}

/**
 * Check if skopeo is available on the system.
 */
export function isSkopeoAvailable(): boolean {
  try {
    execSync('skopeo --version', {stdio: 'pipe'});
    return true;
  } catch {
    return false;
  }
}

/**
 * Check if oras is available on the system.
 */
export function isOrasAvailable(): boolean {
  try {
    execSync('oras version', {stdio: 'pipe'});
    return true;
  } catch {
    return false;
  }
}
