import { Input, Component, Inject } from 'ng-metadata/core';
import { ApostilleDelegationsSet, ApostilleSignatureDocument, ApostilleTagDocument } from '../../../types/common.types';
import * as moment from "moment";


type TagSigningInfo = {
  delegations: DelegationInfo[];
  delegationsByName: {[delegationName: string]: DelegationInfo};

  hasExpiringSoon: boolean;
  hasExpired: boolean;
  hasInvalid: boolean;
};


type DelegationInfo = {
  delegationName: string;
  delegationHash: string;
  expiration: moment.Moment;
  hasMatchingHash: boolean;
  isExpired: boolean;
  isExpiringSoon: boolean
};


const RELEASES = ['targets/releases', 'targets'];


/**
 * A component that displays the signing status of a tag in the repository view.
 */
@Component({
  selector: 'tag-signing-display',
  templateUrl: '/static/js/directives/ui/tag-signing-display/tag-signing-display.component.html',
})
export class TagSigningDisplayComponent {

  @Input('<') public compact: boolean;
  @Input('<') public tag: any;
  @Input('<') public delegations: ApostilleDelegationsSet;

  private cachedSigningInfo: TagSigningInfo | null = null;

  constructor(@Inject("$sanitize") private $sanitize: ng.sanitize.ISanitizeService) {

  }

  private base64ToHex(base64String: string): string {
    // Based on: http://stackoverflow.com/questions/39460182/decode-base64-to-hexadecimal-string-with-javascript
    try {
      var raw = atob(base64String);
    } catch (e) {
      return '(invalid)';
    }

    var hexString = '';
    for (var i = 0; i < raw.length; ++i) {
      var char = raw.charCodeAt(i);
      var hex = char.toString(16);
      hexString += (hex.length == 2 ? hex : '0' + hex);
    }
    return hexString;
  }

  private buildDelegationInfo(tag: any,
                              delegationName: string,
                              delegation: ApostilleSignatureDocument): DelegationInfo {
    var digest_without_prefix = tag.manifest_digest.substr('sha256:'.length);
    var hex_signature = this.base64ToHex(delegation.targets[tag.name].hashes['sha256']);

    var expires = moment(delegation.expiration);
    var now = moment();
    var withOneWeek = moment().add('1', 'w');

    return {
      'delegationName': delegationName,
      'hasMatchingHash': digest_without_prefix == hex_signature,
      'expiration': expires,
      'delegationHash': hex_signature,
      'isExpired': expires.isSameOrBefore(now),
      'isExpiringSoon': !expires.isSameOrBefore(now) && expires.isSameOrBefore(withOneWeek),
    };
  }

  private buildTagSigningInfo(tag: any, delegationSet: ApostilleDelegationsSet): TagSigningInfo {
    var info = {
      'delegations': [],
      'delegationsByName': {},
      'hasExpired': false,
      'hasExpiringSoon': false,
      'hasInvalid': false,
    };

    // Find all delegations containing the tag as a target.
    Object.keys(delegationSet.delegations).forEach((delegationName) => {
      var delegation = delegationSet.delegations[delegationName];
      if (delegation && delegation.targets && delegation.targets[tag.name]) {
        var DelegationInfo = this.buildDelegationInfo(tag, delegationName, delegation);
        info.delegations.push(DelegationInfo);
        info.delegationsByName[delegationName] = DelegationInfo;

        if (DelegationInfo.isExpired) {
          info.hasExpired = true;
        }

        if (DelegationInfo.isExpiringSoon) {
          info.hasExpiringSoon = true;
        }

        if (!DelegationInfo.hasMatchingHash) {
          info.hasInvalid = true;
        }
      }
    });

    return info;
  }

  private isDefaultDelegation(name: string): boolean {
    return RELEASES.indexOf(name) >= 0;
  }

  private getSigningInfo(tag: any, delegationSet: ApostilleDelegationsSet): TagSigningInfo {
    if (!this.cachedSigningInfo) {
      this.cachedSigningInfo = this.buildTagSigningInfo(tag, delegationSet);
    }
    return this.cachedSigningInfo;
  }

  private signingStatus(tag: any, delegationSet: ApostilleDelegationsSet): string {
    if (!tag || !delegationSet) {
      return 'loading';
    }

    if (!tag.manifest_digest) {
      return 'not-signed';
    }

    if (delegationSet.error) {
      return 'error';
    }

    // Check if signed at all.
    var signingInfo = this.getSigningInfo(tag, delegationSet);
    if (!signingInfo.delegations.length) {
      return 'not-signed';
    }

    // Check if all delegations are signed and valid.
    var allReleasesValid = true;
    var oneReleaseValid = false;

    this.cachedSigningInfo.delegations.forEach(function(delegation) {
      var isValid = delegation.hasMatchingHash && !delegation.isExpired;
      if (isValid) {
        oneReleaseValid = true;
      }

      allReleasesValid = allReleasesValid && isValid;
    });

    // Check if the special RELEASES target(s) is/are signed and valid.
    var releasesDelegation = null;
    RELEASES.forEach((releaseTarget) => {
      var delegation = this.cachedSigningInfo.delegationsByName[releaseTarget];
      if (delegation && !releasesDelegation) {
        releasesDelegation = delegation;
      }
    });

    if (releasesDelegation && releasesDelegation.hasMatchingHash && !releasesDelegation.isExpired) {
      if (allReleasesValid && this.cachedSigningInfo.delegations.length > 1) {
        return 'all-signed';
      } else {
        return 'release-signed';
      }
    }

    if (allReleasesValid || oneReleaseValid) {
      return 'non-release-signed';
    }

    return 'invalid-signed';
  }
}
