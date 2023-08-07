import {AxiosError, AxiosResponse} from 'axios';
import axios from 'src/libs/axios';
import {
  assertHttpCode,
  BulkOperationError,
  ResourceError,
  throwIfError,
} from './ErrorHandling';

export interface TagsResponse {
  page: number;
  has_additional: boolean;
  tags: Tag[];
}

export interface Tag {
  name: string;
  is_manifest_list: boolean;
  last_modified: string;
  manifest_digest: string;
  reversion: boolean;
  size: number;
  start_ts: number;
  manifest_list: ManifestList;
  expiration?: string;
  end_ts?: number;
}

export interface ManifestList {
  schemaVersion: number;
  mediaType: string;
  manifests: Manifest[];
}

export interface Manifest {
  mediaType: string;
  size: number;
  digest: string;
  platform: Platform;
  security: SecurityDetailsResponse;
  layers: Layer[];
}

export interface Layer {
  size: number;
}

export interface Platform {
  architecture: string;
  os: string;
  features?: string[];
  variant?: string;
  'os.version'?: string;
}

export interface LabelsResponse {
  labels: Label[];
}

export interface Label {
  id?: string;
  key: string;
  value: string;
  media_type?: string;
  source_type?: string;
}
export interface ManifestByDigestResponse {
  digest: string;
  is_manifest_list: boolean;
  manifest_data: string;
  config_media_type?: any;
  layers?: any;
}

export interface SecurityDetailsResponse {
  status: string;
  data: Data;
  suppressed_vulnerabilities: string[];
}

export interface ManifestVulnerabilitySuppressionsResponse {
  status: string;
  suppressed_vulnerabilities: string[];
}
export interface Data {
  Layer: Layer;
}
export interface Layer {
  Name: string;
  ParentName: string;
  NamespaceName: string;
  IndexedByVersion: number;
  Features: Feature[];
}
export interface Feature {
  Name: string;
  VersionFormat: string;
  NamespaceName: string;
  AddedBy: string;
  Version: string;
  Vulnerabilities?: Vulnerability[];
}

export interface Vulnerability {
  Severity: VulnerabilitySeverity;
  NamespaceName: string;
  Link: string;
  FixedBy: string;
  Description: string;
  Name: string;
  Metadata: VulnerabilityMetadata;
  SuppressedBy?: string;
}

export interface VulnerabilityMetadata {
  UpdatedBy: string;
  RepoName: string;
  RepoLink: string;
  DistroName: string;
  DistroVersion: string;
  NVD: {
    CVSSv3: {
      Vectors: string;
      Score: number;
    };
  };
}

export enum VulnerabilitySeverity {
  Critical = 'Critical',
  High = 'High',
  Medium = 'Medium',
  Low = 'Low',
  Negligible = 'Negligible',
  None = 'None',
  Unknown = 'Unknown',
  Suppressed = 'Suppressed',
}

export const VulnerabilityOrder = {
  [VulnerabilitySeverity.Critical]: 0,
  [VulnerabilitySeverity.High]: 1,
  [VulnerabilitySeverity.Medium]: 2,
  [VulnerabilitySeverity.Low]: 3,
  [VulnerabilitySeverity.Negligible]: 4,
  [VulnerabilitySeverity.Unknown]: 5,
};

export enum VulnerabilitySuppressionSource {
  Manifest = 'manifest',
  Organization = 'organization',
  Repository = 'repository',
}

// TODO: Support cancelation signal here
export async function getTags(
  org: string,
  repo: string,
  page: number,
  limit = 100,
  specificTag = null,
  onlyActiveTags = true,
) {
  let path = `/api/v1/repository/${org}/${repo}/tag/?limit=${limit}&page=${page}`;
  if (onlyActiveTags) {
    path = path.concat(`&onlyActiveTags=true`);
  }
  if (specificTag) {
    path = path.concat(`&specificTag=${specificTag}`);
  }

  const urlSearchParams = new URLSearchParams(window.location.search);
  const urlParams = Object.fromEntries(urlSearchParams.entries());
  if (urlParams['filter_tag_name']) {
    path = path.concat(`&filter_tag_name=${urlParams['filter_tag_name']}`);
  }
  const response: AxiosResponse<TagsResponse> = await axios.get(path);
  assertHttpCode(response.status, 200);
  return response.data;
}

export async function getLabels(
  org: string,
  repo: string,
  digest: string,
  signal: AbortSignal,
) {
  const response: AxiosResponse<LabelsResponse> = await axios.get(
    `/api/v1/repository/${org}/${repo}/manifest/${digest}/labels`,
    {signal},
  );
  assertHttpCode(response.status, 200);
  return response.data.labels;
}

export async function bulkCreateLabels(
  org: string,
  repo: string,
  manifest: string,
  labels: Label[],
) {
  const responses = await Promise.allSettled(
    labels.map((label) => createLabel(org, repo, manifest, label)),
  );
  throwIfError(responses, 'Error creating labels');
}

export async function bulkDeleteLabels(
  org: string,
  repo: string,
  manifest: string,
  labels: Label[],
) {
  const responses = await Promise.allSettled(
    labels.map((label) => deleteLabel(org, repo, manifest, label)),
  );
  throwIfError(responses, 'Error deleting labels');
}

export async function createLabel(
  org: string,
  repo: string,
  manifest: string,
  label: Label,
) {
  try {
    await axios.post(
      `/api/v1/repository/${org}/${repo}/manifest/${manifest}/labels`,
      {
        key: label.key,
        value: label.value,
        media_type: label.media_type,
      },
    );
  } catch (error) {
    throw new ResourceError(
      'Unable to create label',
      `${label.key}=${label.value}`,
      error,
    );
  }
}

export async function deleteLabel(
  org: string,
  repo: string,
  manifest: string,
  label: Label,
) {
  try {
    await axios.delete(
      `/api/v1/repository/${org}/${repo}/manifest/${manifest}/labels/${label.id}`,
    );
  } catch (error) {
    throw new ResourceError('Unable to delete label', label.id, error);
  }
}

interface TagLocation {
  org: string;
  repo: string;
  tag: string;
}

export async function bulkDeleteTags(
  org: string,
  repo: string,
  tags: string[],
  force = false,
) {
  const deletion_function = force ? expireTag : deleteTag;
  const responses = await Promise.allSettled(
    tags.map((tag) => deletion_function(org, repo, tag)),
  );

  // Filter failed responses
  const errResponses = responses.filter(
    (r) => r.status == 'rejected',
  ) as PromiseRejectedResult[];

  // If errors collect and throw
  if (errResponses.length > 0) {
    const bulkDeleteError = new BulkOperationError<TagDeleteError>(
      'error deleting tags',
    );
    for (const response of errResponses) {
      const reason = response.reason as TagDeleteError;
      bulkDeleteError.addError(reason.tag, reason);
    }
    throw bulkDeleteError;
  }
}

export class TagDeleteError extends Error {
  error: Error;
  tag: string;
  constructor(message: string, tag: string, error: AxiosError) {
    super(message);
    this.tag = tag;
    this.error = error;
    Object.setPrototypeOf(this, TagDeleteError.prototype);
  }
}

export async function deleteTag(org: string, repo: string, tag: string) {
  try {
    const response: AxiosResponse = await axios.delete(
      `/api/v1/repository/${org}/${repo}/tag/${tag}`,
    );
    assertHttpCode(response.status, 204);
  } catch (err) {
    throw new TagDeleteError(
      'failed to delete tag',
      `${org}/${repo}:${tag}`,
      err,
    );
  }
}

export async function expireTag(org: string, repo: string, tag: string) {
  try {
    const response: AxiosResponse = await axios.post(
      `/api/v1/repository/${org}/${repo}/tag/${tag}/expire`,
      {
        include_submanifests: true,
        is_alive: true,
      },
    );
    assertHttpCode(response.status, 200);
  } catch (err) {
    throw new TagDeleteError(
      'failed to expire tag',
      `${org}/${repo}:${tag}`,
      err,
    );
  }
}

export async function getManifestByDigest(
  org: string,
  repo: string,
  digest: string,
) {
  const response: AxiosResponse<ManifestByDigestResponse> = await axios.get(
    `/api/v1/repository/${org}/${repo}/manifest/${digest}`,
  );
  assertHttpCode(response.status, 200);
  return response.data;
}

export async function getSecurityDetails(
  org: string,
  repo: string,
  digest: string,
) {
  const response: AxiosResponse<SecurityDetailsResponse> = await axios.get(
    `/api/v1/repository/${org}/${repo}/manifest/${digest}/security?vulnerabilities=true&suppressions=true`,
  );
  assertHttpCode(response.status, 200);
  return response.data;
}

export async function createTag(
  org: string,
  repo: string,
  tag: string,
  manifest: string,
) {
  await axios.put(`/api/v1/repository/${org}/${repo}/tag/${tag}`, {
    manifest_digest: manifest,
  });
}

export async function bulkSetExpiration(
  org: string,
  repo: string,
  tags: string[],
  expiration: number,
) {
  const responses = await Promise.allSettled(
    tags.map((tag) => setExpiration(org, repo, tag, expiration)),
  );
  throwIfError(responses, 'Error setting expiration for tags');
}

export async function setExpiration(
  org: string,
  repo: string,
  tag: string,
  expiration: number,
) {
  try {
    await axios.put(`/api/v1/repository/${org}/${repo}/tag/${tag}`, {
      expiration: expiration,
    });
  } catch (error) {
    throw new ResourceError('Unable to set tag expiration', tag, error);
  }
}

export async function restoreTag(
  org: string,
  repo: string,
  tag: string,
  digest: string,
) {
  const response: AxiosResponse = await axios.post(
    `/api/v1/repository/${org}/${repo}/tag/${tag}/restore`,
    {
      manifest_digest: digest,
    },
  );
}

export async function permanentlyDeleteTag(
  org: string,
  repo: string,
  tag: string,
  digest: string,
) {
  const response: AxiosResponse = await axios.post(
    `/api/v1/repository/${org}/${repo}/tag/${tag}/expire`,
    {
      manifest_digest: digest,
      include_submanifests: true,
      is_alive: false,
    },
  );
}

export async function getManifestVulnerabilitySuppressions(
  org: string,
  repo: string,
  digest: string,
) {
  const response: AxiosResponse<ManifestVulnerabilitySuppressionsResponse> =
    await axios.get(
      `/api/v1/repository/${org}/${repo}/manifest/${digest}/suppressed_vulnerabilities`,
    );
  assertHttpCode(response.status, 200);
  return response.data;
}

export class SetVulnerabilitySupressionsError extends Error {
  error: Error;
  manifest?: string;
  repository?: string;
  organization?: string;
  constructor(
    message: string,
    error: AxiosError,
    manifest?: string,
    repository?: string,
    organization?: string,
  ) {
    super(message);
    this.error = error;
    this.manifest = manifest ?? undefined;
    this.repository = repository ?? undefined;
    this.organization = organization ?? undefined;

    if (
      this.manifest === undefined &&
      this.repository === undefined &&
      this.organization === undefined
    ) {
      throw new Error(
        'At least one of manifest, repository, or organization must be defined',
      );
    }

    Object.setPrototypeOf(this, TagDeleteError.prototype);
  }
}
export async function setManifestVulnerabilitySuppressions(
  org: string,
  repo: string,
  digest: string,
  suppressions: string[],
) {
  const data = {
    suppressed_vulnerabilities: suppressions,
  };
  axios
    .put(
      `/api/v1/repository/${org}/${repo}/manifest/${digest}/suppressed_vulnerabilities`,
      data,
    )
    .then((response) => {
      assertHttpCode(response.status, 204);
      return response;
    })
    .catch((error) => {
      throw new SetVulnerabilitySupressionsError(
        'failed to set vulnerability suppressions',
        error,
        digest,
        repo,
        org,
      );
    });
}
