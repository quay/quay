/**
 * S3 utilities for verifying geo-replication and object storage in Playwright
 * e2e tests.
 *
 * Uses awscli via child_process to stay portable across any S3-compatible
 * backend (Garage, MinIO, real S3, etc.). Follows the same exec pattern
 * as container.ts.
 *
 * Configure via environment variables:
 *   S3_ENDPOINT           - S3 API endpoint (default: http://localhost:3900; the
 *                           object-storage spec runs only when S3_ENDPOINT is set
 *                           explicitly)
 *   S3_REGION             - AWS region (default: us-east-1)
 *   S3_BUCKETS            - Comma-separated bucket names used by Quay
 *                           (default: quay-us-east,quay-eu-west)
 *   S3_STORAGE_PATH       - Quay storage path prefix inside the bucket
 *                           (default: datastorage/registry)
 *   AWS_ACCESS_KEY_ID     - Access key
 *   AWS_SECRET_ACCESS_KEY - Secret key
 */

import {exec, execFile} from 'child_process';
import {promisify} from 'util';

const execAsync = promisify(exec);
const execFileAsync = promisify(execFile);

const S3_ENDPOINT = process.env.S3_ENDPOINT ?? 'http://localhost:3900';
const S3_REGION = process.env.S3_REGION ?? 'us-east-1';
const AWS_BASE = `AWS_PAGER="" aws --endpoint-url ${S3_ENDPOINT} --region ${S3_REGION}`;

export async function isAwscliAvailable(): Promise<boolean> {
  try {
    await execAsync('aws --version');
    return true;
  } catch {
    return false;
  }
}

export async function listBuckets(): Promise<string[]> {
  const {stdout} = await execAsync(
    `${AWS_BASE} s3api list-buckets --output json`,
  );
  const resp = JSON.parse(stdout);
  return (resp.Buckets ?? []).map((b: {Name: string}) => b.Name);
}

export async function listBucketObjects(bucket: string): Promise<string[]> {
  const {stdout} = await execAsync(
    `${AWS_BASE} s3api list-objects-v2 --bucket ${bucket} --output json`,
  );
  const resp = JSON.parse(stdout);
  return (resp.Contents ?? []).map((o: {Key: string}) => o.Key);
}

export async function deleteObject(bucket: string, key: string): Promise<void> {
  await execAsync(
    `${AWS_BASE} s3api delete-object --bucket ${bucket} --key ${key}`,
  );
}

// ---------------------------------------------------------------------------
// Helpers for object-storage verification
// ---------------------------------------------------------------------------

/**
 * Returns true when S3_ENDPOINT is set (non-empty) and awscli is available.
 * Use this to skip tests that require a live S3 backend.
 */
export async function isS3Configured(): Promise<boolean> {
  if (!process.env.S3_ENDPOINT) {
    return false;
  }
  return isAwscliAvailable();
}

/**
 * Returns the list of Quay storage bucket names.
 *
 * Reads S3_BUCKETS from the environment as a comma-separated list of names,
 * trimmed, with empty entries dropped. Defaults to ["quay-us-east",
 * "quay-eu-west"] when unset.
 */
export function getStorageBuckets(): string[] {
  const raw = process.env.S3_BUCKETS;
  if (raw) {
    const parsed = raw
      .split(',')
      .map((s) => s.trim())
      .filter((s) => s.length > 0);
    if (parsed.length > 0) {
      return parsed;
    }
  }
  return ['quay-us-east', 'quay-eu-west'];
}

/**
 * Returns the name of the primary Quay storage bucket (first in
 * getStorageBuckets()).
 */
export function getPrimaryBucket(): string {
  return getStorageBuckets()[0];
}

/**
 * Returns the Quay storage path prefix used inside each S3 bucket.
 * Reads S3_STORAGE_PATH from the environment; falls back to the Quay default
 * "datastorage/registry". Leading and trailing slashes are stripped.
 */
export function getStoragePath(): string {
  const raw = process.env.S3_STORAGE_PATH ?? 'datastorage/registry';
  return raw.replace(/^\/+|\/+$/g, '');
}

/**
 * Converts a sha256 digest (e.g. "sha256:abcd1234…") into the S3 object key
 * where Quay stores the blob, using the storage path prefix from
 * getStoragePath().
 *
 * Mirrors Quay's _init_path (storage/cloud.py): the storage_path is joined
 * with the key and a leading "/" is stripped, so an empty or root storage_path
 * ("", "/") yields no prefix — the key starts directly with "sha256/…".
 *
 * Key format: [<storagePath>/]sha256/<first2chars>/<fullhash>
 * Examples:
 *   storagePath ""                 → sha256/ab/abcd1234…
 *   storagePath "datastorage/registry" → datastorage/registry/sha256/ab/abcd1234…
 */
export function blobKey(digest: string): string {
  const hash = digest.replace('sha256:', '');
  const prefix = getStoragePath();
  return `${prefix ? `${prefix}/` : ''}sha256/${hash.substring(0, 2)}/${hash}`;
}

/**
 * Returns the size of an S3 object in bytes, or null when the object does not
 * exist. Classifies "not found" solely on the aws CLI stderr so that a key
 * whose hex hash happens to contain "404" is never misclassified.
 *
 * Returns null when stderr matches /(404)|NoSuchKey|Not Found/.
 * Rethrows any other error (e.g. auth failure). Because some backends also
 * return 404 for a missing bucket, a 404 is only reported as "missing object"
 * after head-bucket confirms the bucket exists; otherwise the error is thrown.
 */
export async function headObject(
  bucket: string,
  key: string,
): Promise<{size: number} | null> {
  try {
    const {stdout} = await execFileAsync(
      'aws',
      [
        '--endpoint-url',
        S3_ENDPOINT,
        '--region',
        S3_REGION,
        's3api',
        'head-object',
        '--bucket',
        bucket,
        '--key',
        key,
        '--output',
        'json',
      ],
      {env: {...process.env, AWS_PAGER: ''}},
    );
    const resp = JSON.parse(stdout) as {ContentLength: number};
    return {size: resp.ContentLength};
  } catch (err) {
    const stderr: string =
      err != null && typeof err === 'object' && 'stderr' in err
        ? String((err as {stderr: unknown}).stderr)
        : '';
    if (/\(404\)|NoSuchKey|Not Found/.test(stderr)) {
      // Some backends also return 404 for a missing bucket. Confirm the bucket
      // is reachable so a missing bucket or endpoint is never mistaken for a
      // deleted object (head-bucket throws if it is not).
      await execFileAsync(
        'aws',
        [
          '--endpoint-url',
          S3_ENDPOINT,
          '--region',
          S3_REGION,
          's3api',
          'head-bucket',
          '--bucket',
          bucket,
        ],
        {env: {...process.env, AWS_PAGER: ''}},
      );
      return null;
    }
    throw err;
  }
}
