import {SourceRegistryType} from 'src/resources/OrgMirrorResource';

export type SyncUnit = 'seconds' | 'minutes' | 'hours' | 'days' | 'weeks';
export type Visibility = 'public' | 'private';

// Form data types for Organization Mirroring components
export interface OrgMirroringFormData {
  isEnabled: boolean;
  externalRegistryType: SourceRegistryType | '';
  externalRegistryUrl: string;
  externalNamespace: string;
  robotUsername: string;
  visibility: Visibility;
  repositoryFilters: string;
  syncStartDate: string;
  syncValue: string;
  syncUnit: SyncUnit;
  username: string;
  password: string;
  verifyTls: boolean;
  httpProxy: string;
  httpsProxy: string;
  noProxy: string;
  skopeoTimeout: number;
}
