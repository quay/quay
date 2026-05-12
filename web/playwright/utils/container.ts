/**
 * Registry image utilities for Playwright e2e tests.
 *
 * These helpers intentionally avoid podman/docker. OpenShift CI pods can
 * block user namespaces, which makes container runtimes fail even when the
 * binaries are installed. Skopeo, crane, oras, and regctl operate directly
 * against registries and work in restricted pods.
 */

import {exec, execFile, execFileSync, spawn} from 'child_process';
import * as fs from 'fs';
import {mkdtempSync, rmSync, writeFileSync} from 'fs';
import {mkdtemp, mkdir, rm, writeFile} from 'fs/promises';
import * as os from 'os';
import * as path from 'path';
import {promisify} from 'util';
import {API_URL} from './config';

const execAsync = promisify(exec);
const execFileAsync = promisify(execFile);

// Extract registry host from API_URL (e.g., 'localhost:8080')
const REGISTRY_HOST = new URL(API_URL).host;

const BUSYBOX_IMAGE =
  'quay.io/prometheus/busybox@sha256:760c8f250221675f04a450d740b1a01310aa4d89ad0a16586b6b3fd2c077e978';

type ToolAvailability = {
  skopeo: boolean;
  crane: boolean;
  oras: boolean;
  regctl: boolean;
};

let toolAvailabilityPromise: Promise<ToolAvailability> | null = null;

function targetImage(namespace: string, repo: string, tag: string): string {
  return `${REGISTRY_HOST}/${namespace}/${repo}:${tag}`;
}

function registryAuthConfig(username: string, password: string): string {
  const auth = Buffer.from(`${username}:${password}`).toString('base64');
  return `${JSON.stringify({auths: {[REGISTRY_HOST]: {auth}}})}\n`;
}

async function withRegistryAuthFile<T>(
  username: string,
  password: string,
  operation: (authFile: string) => Promise<T>,
): Promise<T> {
  const authDir = await mkdtemp(path.join(os.tmpdir(), 'quay-registry-auth-'));
  const authFile = path.join(authDir, 'auth.json');

  try {
    await writeFile(authFile, registryAuthConfig(username, password), {
      mode: 0o600,
    });
    return await operation(authFile);
  } finally {
    await rm(authDir, {recursive: true, force: true});
  }
}

function withRegistryAuthFileSync<T>(
  username: string,
  password: string,
  operation: (authFile: string) => T,
): T {
  const authDir = mkdtempSync(path.join(os.tmpdir(), 'quay-registry-auth-'));
  const authFile = path.join(authDir, 'auth.json');

  try {
    writeFileSync(authFile, registryAuthConfig(username, password), {
      mode: 0o600,
    });
    return operation(authFile);
  } finally {
    rmSync(authDir, {recursive: true, force: true});
  }
}

async function withRegctlConfig<T>(
  username: string,
  password: string,
  operation: (env: NodeJS.ProcessEnv) => Promise<T>,
): Promise<T> {
  await requireTool('regctl');

  const configDir = await mkdtemp(path.join(os.tmpdir(), 'quay-regctl-'));
  const configFile = path.join(configDir, 'config.json');
  const env = {...process.env, REGCTL_CONFIG: configFile};

  try {
    await execFileAsync(
      'regctl',
      ['registry', 'set', REGISTRY_HOST, '--tls', 'disabled', '--skip-check'],
      {env},
    );
    await execFileWithInput(
      'regctl',
      [
        'registry',
        'login',
        REGISTRY_HOST,
        '-u',
        username,
        '--pass-stdin',
        '--skip-check',
      ],
      password,
      {env},
    );
    return await operation(env);
  } finally {
    await rm(configDir, {recursive: true, force: true});
  }
}

async function commandAvailable(
  command: string,
  args: string[],
): Promise<boolean> {
  try {
    await execFileAsync(command, args);
    return true;
  } catch {
    return false;
  }
}

async function detectRegistryTools(): Promise<ToolAvailability> {
  if (!toolAvailabilityPromise) {
    toolAvailabilityPromise = Promise.all([
      commandAvailable('skopeo', ['--version']),
      commandAvailable('crane', ['version']),
      commandAvailable('oras', ['version']),
      commandAvailable('regctl', ['version']),
    ]).then(([skopeo, crane, oras, regctl]) => ({
      skopeo,
      crane,
      oras,
      regctl,
    }));
  }
  return toolAvailabilityPromise;
}

async function requireTool(tool: keyof ToolAvailability): Promise<void> {
  const tools = await detectRegistryTools();
  if (!tools[tool]) {
    throw new Error(`${tool} CLI required for registry image tests`);
  }
}

/**
 * Execute an async operation, retrying with fixed 1s delays on failure.
 *
 * Registry pushes can race with repository initialization, so push-like
 * helpers retry their registry operation a few times.
 */
async function retryOperation(
  operation: () => Promise<void>,
  maxAttempts = 5,
): Promise<void> {
  let lastErr: unknown;
  for (let i = 0; i < maxAttempts; i++) {
    try {
      await operation();
      return;
    } catch (err) {
      lastErr = err;
      await new Promise((r) => setTimeout(r, 1000));
    }
  }
  throw lastErr;
}

/**
 * Execute a shell command, retrying with fixed 1s delays on failure.
 *
 * Similar to retryOperation but for direct shell commands via execAsync.
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

async function skopeoCopy(args: string[]): Promise<void> {
  await requireTool('skopeo');
  await execFileAsync('skopeo', ['copy', ...args]);
}

async function craneLogin(
  registryHost: string,
  username: string,
  password: string,
  dockerConfig: string,
): Promise<void> {
  await requireTool('crane');
  await execFileWithInput(
    'crane',
    [
      'auth',
      'login',
      registryHost,
      '--username',
      username,
      '--password-stdin',
      '--insecure',
    ],
    password,
    {env: {...process.env, DOCKER_CONFIG: dockerConfig}},
  );
}

function execFileWithInput(
  command: string,
  args: string[],
  input: string,
  options: {env?: NodeJS.ProcessEnv} = {},
): Promise<void> {
  return new Promise((resolve, reject) => {
    const child = spawn(command, args, {
      env: options.env,
      stdio: ['pipe', 'pipe', 'pipe'],
    });
    let stderr = '';

    child.stderr.setEncoding('utf8');
    child.stderr.on('data', (chunk: string) => {
      stderr += chunk;
    });

    child.on('error', reject);
    child.on('close', (code) => {
      if (code === 0) {
        resolve();
      } else {
        reject(
          new Error(
            `${command} ${args.join(' ')} failed with exit code ${code}: ${stderr}`,
          ),
        );
      }
    });

    child.stdin.end(input);
  });
}

/**
 * Push a test image to the registry using skopeo.
 *
 * Uses busybox as a minimal test image and copies directly from the public
 * source registry to the Quay registry. No local image store is required.
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
  const image = targetImage(namespace, repo, tag);

  await withRegistryAuthFile(username, password, (authFile) =>
    retryOperation(() =>
      skopeoCopy([
        '--override-os=linux',
        '--override-arch=amd64',
        `docker://${BUSYBOX_IMAGE}`,
        `docker://${image}`,
        '--dest-tls-verify=false',
        '--dest-authfile',
        authFile,
      ]),
    ),
  );
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
  await requireTool('crane');

  const image = targetImage(namespace, repo, tag);
  const uniqueId = `${Date.now()}-${Math.random().toString(36).slice(2)}`;
  const tmpDir = await mkdtemp(path.join(os.tmpdir(), 'quay-unique-img-'));
  const rootDir = path.join(tmpDir, 'root');
  const authDir = path.join(tmpDir, 'auth');
  const layerTar = path.join(tmpDir, 'layer.tar');

  try {
    await mkdir(rootDir);
    await mkdir(authDir);
    await writeFile(path.join(rootDir, 'unique'), `${uniqueId}\n`);
    await execFileAsync('tar', ['-C', rootDir, '-cf', layerTar, 'unique']);

    await craneLogin(REGISTRY_HOST, username, password, authDir);

    await retryOperation(() =>
      execFileAsync(
        'crane',
        ['append', '--insecure', '--new_layer', layerTar, '--new_tag', image],
        {env: {...process.env, DOCKER_CONFIG: authDir}},
      ).then(() => undefined),
    );
  } finally {
    await rm(tmpDir, {recursive: true, force: true});
  }
}

/**
 * Pull an image from the registry into a temporary OCI layout.
 *
 * This verifies the image can be pulled without requiring a local
 * podman/docker image store.
 */
export async function pullImage(
  namespace: string,
  repo: string,
  tag: string,
  username: string,
  password: string,
): Promise<void> {
  const image = targetImage(namespace, repo, tag);
  const tmpDir = await mkdtemp(path.join(os.tmpdir(), 'quay-pull-img-'));

  try {
    await withRegistryAuthFile(username, password, (authFile) =>
      skopeoCopy([
        `docker://${image}`,
        `oci:${tmpDir}:${tag}`,
        '--src-tls-verify=false',
        '--src-authfile',
        authFile,
      ]),
    );
  } finally {
    await rm(tmpDir, {recursive: true, force: true});
  }
}

/**
 * Check if registry image tooling is available.
 *
 * Kept under the old name because tests use this fixture to decide whether
 * @container-tagged tests can perform registry image operations.
 */
export async function isContainerRuntimeAvailable(): Promise<boolean> {
  return isRegistryImageToolingAvailable();
}

/**
 * Check if the required daemonless registry image tooling is available.
 */
export async function isRegistryImageToolingAvailable(): Promise<boolean> {
  const tools = await detectRegistryTools();
  return tools.skopeo;
}

/**
 * Push a multi-architecture manifest list to the registry.
 *
 * Uses a pinned busybox manifest list as the source image.
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
  const image = targetImage(namespace, repo, tag);

  await withRegistryAuthFile(username, password, (authFile) =>
    retryOperation(() =>
      skopeoCopy([
        '--all',
        `docker://${BUSYBOX_IMAGE}`,
        `docker://${image}`,
        '--dest-tls-verify=false',
        '--dest-authfile',
        authFile,
      ]),
    ),
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
  const ref = targetImage(namespace, repo, tag);

  withRegistryAuthFileSync(username, password, (authFile) =>
    execFileSync(
      'oras',
      [
        'attach',
        ref,
        '--insecure',
        '--registry-config',
        authFile,
        `--artifact-type=${artifactType}`,
        `--annotation=${annotation}`,
        filePath,
      ],
      {stdio: 'pipe', timeout: 60_000},
    ),
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
  const image = targetImage(namespace, repo, tag);

  await withRegistryAuthFile(username, password, (authFile) =>
    retryOperation(() =>
      skopeoCopy([
        '--format=oci',
        '--override-os=linux',
        '--override-arch=amd64',
        `docker://${BUSYBOX_IMAGE}`,
        `docker://${image}`,
        '--dest-tls-verify=false',
        '--dest-authfile',
        authFile,
      ]),
    ),
  );
}

/**
 * Check if oras CLI is available on the system.
 */
export async function isOrasAvailable(): Promise<boolean> {
  const tools = await detectRegistryTools();
  return tools.oras;
}

/**
 * Check if skopeo CLI is available on the system.
 */
export async function isSkopeoAvailable(): Promise<boolean> {
  const tools = await detectRegistryTools();
  return tools.skopeo;
}

/**
 * Check if crane CLI is available on the system.
 */
export async function isCraneAvailable(): Promise<boolean> {
  const tools = await detectRegistryTools();
  return tools.crane;
}

/**
 * Check if regctl CLI is available on the system.
 */
export async function isRegctlAvailable(): Promise<boolean> {
  const tools = await detectRegistryTools();
  return tools.regctl;
}

/**
 * Check if helm CLI is available on the system.
 */
export async function isHelmAvailable(): Promise<boolean> {
  try {
    await execAsync('helm version');
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
  await requireTool('skopeo');

  const ref = `docker://${REGISTRY_HOST}/${namespace}/${repo}`;
  const {stdout} = await withRegistryAuthFile(username, password, (authFile) =>
    execFileAsync('skopeo', [
      'list-tags',
      ref,
      '--tls-verify=false',
      '--authfile',
      authFile,
    ]),
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
  const {stdout} = await withRegctlConfig(username, password, (env) =>
    execFileAsync('regctl', ['tag', 'ls', ref], {env}),
  );
  return stdout
    .split('\n')
    .map((line) => line.trim())
    .filter((line) => line.length > 0);
}

/**
 * Push a Helm chart to the registry using helm CLI.
 *
 * Creates a minimal test Helm chart, packages it, and pushes to the registry.
 *
 * @param namespace - Organization/namespace
 * @param repo - Repository name (chart name)
 * @param version - Chart version (e.g., '1.0.0')
 * @param username - Registry username
 * @param password - Registry password
 * @param chartMetadata - Optional chart metadata overrides
 *
 * @example
 * ```typescript
 * await pushHelmChart('myorg', 'nginx-chart', '1.0.0', 'testuser', 'password');
 * await pushHelmChart('myorg', 'app-chart', '2.1.0', 'testuser', 'password', {
 *   description: 'My application chart',
 *   appVersion: '2.1.0',
 * });
 * ```
 */
export async function pushHelmChart(
  namespace: string,
  repo: string,
  version: string,
  username: string,
  password: string,
  chartMetadata?: {
    description?: string;
    appVersion?: string;
    dependencies?: Array<{name: string; version: string; repository: string}>;
  },
): Promise<void> {
  // Create temporary directory for chart
  const tmpDir = fs.mkdtempSync(path.join(os.tmpdir(), 'helm-chart-'));
  const chartDir = path.join(tmpDir, repo);

  try {
    // Create chart directory structure
    fs.mkdirSync(chartDir);
    fs.mkdirSync(path.join(chartDir, 'templates'));

    // Create Chart.yaml
    const chartYaml = `apiVersion: v2
name: ${repo}
description: ${chartMetadata?.description || `Test Helm chart for ${repo}`}
type: application
version: ${version}
appVersion: "${chartMetadata?.appVersion || version}"
${
  chartMetadata?.dependencies
    ? `dependencies:\n${chartMetadata.dependencies
        .map(
          (dep) =>
            `  - name: ${dep.name}\n    version: "${dep.version}"\n    repository: "${dep.repository}"`,
        )
        .join('\n')}`
    : ''
}`;

    fs.writeFileSync(path.join(chartDir, 'Chart.yaml'), chartYaml);

    // Create values.yaml
    const valuesYaml = `# Default values for ${repo}
replicaCount: 1

image:
  repository: nginx
  pullPolicy: IfNotPresent
  tag: "latest"

service:
  type: ClusterIP
  port: 80
`;
    fs.writeFileSync(path.join(chartDir, 'values.yaml'), valuesYaml);

    // Create a simple deployment template
    const deploymentYaml = `apiVersion: apps/v1
kind: Deployment
metadata:
  name: {{ include "${repo}.fullname" . }}
  labels:
    app: {{ include "${repo}.name" . }}
spec:
  replicas: {{ .Values.replicaCount }}
  selector:
    matchLabels:
      app: {{ include "${repo}.name" . }}
  template:
    metadata:
      labels:
        app: {{ include "${repo}.name" . }}
    spec:
      containers:
      - name: {{ .Chart.Name }}
        image: "{{ .Values.image.repository }}:{{ .Values.image.tag }}"
        ports:
        - containerPort: 80
`;
    fs.writeFileSync(
      path.join(chartDir, 'templates', 'deployment.yaml'),
      deploymentYaml,
    );

    // Create _helpers.tpl
    const helpersTpl = `{{/*
Expand the name of the chart.
*/}}
{{- define "${repo}.name" -}}
{{- default .Chart.Name .Values.nameOverride | trunc 63 | trimSuffix "-" }}
{{- end }}

{{/*
Create a default fully qualified app name.
*/}}
{{- define "${repo}.fullname" -}}
{{- if .Values.fullnameOverride }}
{{- .Values.fullnameOverride | trunc 63 | trimSuffix "-" }}
{{- else }}
{{- $name := default .Chart.Name .Values.nameOverride }}
{{- printf "%s-%s" .Release.Name $name | trunc 63 | trimSuffix "-" }}
{{- end }}
{{- end }}
`;
    fs.writeFileSync(
      path.join(chartDir, 'templates', '_helpers.tpl'),
      helpersTpl,
    );

    // Package the chart
    await execAsync(`helm package ${chartDir}`, {cwd: tmpDir});

    // Login to registry
    await execAsync(
      `helm registry login ${REGISTRY_HOST} -u ${username} -p ${password} --insecure`,
    );

    // Push the chart (with retries for repo-init race)
    const registryUrl = `oci://${REGISTRY_HOST}`;
    const packagedChart = `${repo}-${version}.tgz`;
    await retryPush(
      `helm push ${path.join(
        tmpDir,
        packagedChart,
      )} ${registryUrl}/${namespace} --insecure`,
    );
  } finally {
    // Cleanup temporary directory
    fs.rmSync(tmpDir, {recursive: true, force: true});
  }
}
