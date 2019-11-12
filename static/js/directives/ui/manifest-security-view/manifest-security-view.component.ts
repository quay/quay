import { Input, Component, Inject } from 'ng-metadata/core';
import { Repository } from '../../../types/common.types';


/**
 * A component that displays the security status of a manifest.
 */
@Component({
  selector: 'manifest-security-view',
  templateUrl: '/static/js/directives/ui/manifest-security-view/manifest-security-view.component.html',
})
export class ManifestSecurityView {
  @Input('<') public repository: Repository;
  @Input('<') public manifestDigest: string;
  
  private cachedSecurityStatus: Object = null;

  constructor(@Inject('VulnerabilityService') private VulnerabilityService: any) {
  }

  private getSecurityStatus(repository: Repository, manifestDigest: string): Object {
    if (repository == null || !manifestDigest) {
      return {'status': 'loading'};
    }

    if (this.cachedSecurityStatus) {
      return this.cachedSecurityStatus;
    }

    this.cachedSecurityStatus = {'status': 'loading'};
    this.loadManifestVulnerabilities(this.cachedSecurityStatus);
    return this.cachedSecurityStatus;
  }

  private loadManifestVulnerabilities(securityStatus) {
    this.VulnerabilityService.loadManifestVulnerabilities(this.repository, this.manifestDigest, (resp) => {
      securityStatus.loading = false;
      securityStatus.status = resp['status'];

      if (securityStatus.status == 'scanned') {
        var vulnerabilities = [];
        var highest = {
          'Priority': 'Unknown',
          'Count': 0,
          'index': 100000,
          'Color': 'gray',
        };

        this.VulnerabilityService.forEachVulnerability(resp, (vuln) => {
          if (this.VulnerabilityService.LEVELS[vuln.Severity].index < highest.index) {
            highest = {
              'Priority': vuln.Severity,
              'Count': 1,
              'index': this.VulnerabilityService.LEVELS[vuln.Severity].index,
              'Color': this.VulnerabilityService.LEVELS[vuln.Severity].color
            }
          } else if (this.VulnerabilityService.LEVELS[vuln.Severity].index == highest.index) {
            highest['Count']++;
          }

          vulnerabilities.push(vuln);
        });

        securityStatus.hasFeatures = this.VulnerabilityService.hasFeatures(resp);
        securityStatus.hasVulnerabilities = !!vulnerabilities.length;
        securityStatus.vulnerabilities = vulnerabilities;
        securityStatus.highestVulnerability = highest;
        securityStatus.featuresInfo = this.VulnerabilityService.buildFeaturesInfo(null, resp);
        securityStatus.vulnerabilitiesInfo = this.VulnerabilityService.buildVulnerabilitiesInfo(null, resp);
      }
    }, () => {
      securityStatus.loading = false;
      securityStatus.hasError = true;
    });
  }
}
