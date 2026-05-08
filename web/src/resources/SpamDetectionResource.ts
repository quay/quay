import axios from 'src/libs/axios';
import {AxiosResponse} from 'axios';

export interface ISpamDetectionRule {
  uuid: string;
  name: string;
  rule_type: string;
  pattern: string | null;
  config: Record<string, unknown>;
  confidence_score: number;
  enabled: boolean;
  created_at: string | null;
  updated_at: string | null;
}

export interface IFlaggedRepo {
  uuid: string;
  namespace_name: string;
  repository_name: string;
  status: string;
  original_description: string | null;
  matched_rules: Array<{
    rule_uuid: string;
    rule_name: string;
    rule_type: string;
    confidence: number;
  }>;
  total_confidence_score: number;
  is_empty: boolean;
  scan_id: string | null;
  actioned_by: string | null;
  actioned_at: string | null;
  created_at: string | null;
  updated_at: string | null;
}

export interface IScanReport {
  scan_id: string;
  total_scanned: number;
  flagged: number;
  skipped: number;
  clean: number;
  below_threshold: number;
  errors: number;
  started_at: string | null;
  finished_at: string | null;
}

export interface CreateSpamRuleRequest {
  name: string;
  rule_type: string;
  pattern?: string;
  config?: Record<string, unknown>;
  confidence_score?: number;
  enabled?: boolean;
}

export async function fetchSpamRules(): Promise<ISpamDetectionRule[]> {
  const response: AxiosResponse = await axios.get(
    '/api/v1/superuser/spam/rules',
  );
  return response.data.rules || [];
}

export async function createSpamRule(
  data: CreateSpamRuleRequest,
): Promise<ISpamDetectionRule> {
  const response: AxiosResponse = await axios.post(
    '/api/v1/superuser/spam/rules',
    data,
  );
  return response.data;
}

export async function updateSpamRule(
  uuid: string,
  data: Partial<CreateSpamRuleRequest>,
): Promise<ISpamDetectionRule> {
  const response: AxiosResponse = await axios.put(
    `/api/v1/superuser/spam/rules/${uuid}`,
    data,
  );
  return response.data;
}

export async function deleteSpamRule(uuid: string): Promise<void> {
  await axios.delete(`/api/v1/superuser/spam/rules/${uuid}`);
}

export async function fetchFlaggedRepos(params?: {
  status?: string;
  min_confidence?: number;
  namespace?: string;
  scan_id?: string;
  page_token?: string;
  limit?: number;
}): Promise<{flagged_repos: IFlaggedRepo[]; next_page_token?: string}> {
  const response: AxiosResponse = await axios.get(
    '/api/v1/superuser/spam/flagged',
    {params},
  );
  return response.data;
}

export async function getFlaggedRepo(uuid: string): Promise<IFlaggedRepo> {
  const response: AxiosResponse = await axios.get(
    `/api/v1/superuser/spam/flagged/${uuid}`,
  );
  return response.data;
}

export async function quarantineRepo(uuid: string): Promise<void> {
  await axios.post(`/api/v1/superuser/spam/flagged/${uuid}/quarantine`);
}

export async function restoreRepo(uuid: string): Promise<void> {
  await axios.post(`/api/v1/superuser/spam/flagged/${uuid}/restore`);
}

export async function dismissRepo(uuid: string): Promise<void> {
  await axios.post(`/api/v1/superuser/spam/flagged/${uuid}/dismiss`);
}

export async function triggerSpamScan(): Promise<IScanReport> {
  const response: AxiosResponse = await axios.post(
    '/api/v1/superuser/spam/scan',
  );
  return response.data;
}
