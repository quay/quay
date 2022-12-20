import {Vulnerability, VulnerabilitySeverity} from 'src/resources/TagResource';
import {VulnerabilityStats} from '../SecurityReport/SecurityReportChart';

export interface PackagesListItem {
  PackageName: string;
  CurrentVersion: string;
  Vulnerabilities: Vulnerability[];

  VulnerabilityCounts: VulnerabilityStats;
  HighestVulnerabilitySeverity: VulnerabilitySeverity;

  VulnerabilityCountsAfterFix: VulnerabilityStats;
  HighestVulnerabilitySeverityAfterFix: VulnerabilitySeverity;
}
