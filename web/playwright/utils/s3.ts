/**
 * S3 utilities for verifying geo-replication in Playwright e2e tests.
 *
 * Uses awscli via child_process to stay portable across any S3-compatible
 * backend (Garage, MinIO, real S3, etc.). Follows the same exec pattern
 * as container.ts.
 *
 * Configure via environment variables:
 *   S3_ENDPOINT       - S3 API endpoint (default: http://localhost:3900)
 *   S3_REGION         - AWS region (default: us-east-1)
 *   AWS_ACCESS_KEY_ID - Access key
 *   AWS_SECRET_ACCESS_KEY - Secret key
 */

import {exec} from 'child_process';
import {promisify} from 'util';

const execAsync = promisify(exec);

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
