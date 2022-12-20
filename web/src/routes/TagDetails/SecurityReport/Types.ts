import {
  VulnerabilityMetadata,
  VulnerabilitySeverity,
} from 'src/resources/TagResource';

export interface VulnerabilityListItem {
  PackageName: string;
  CurrentVersion: string;
  Description: string;
  Advisory: string;
  Severity: VulnerabilitySeverity;
  Package: string;
  NamespaceName: string;
  Name: string;
  FixedInVersion: string;
  Metadata: VulnerabilityMetadata;
  Link: string;
}
