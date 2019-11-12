import { Input, Component, Inject } from 'ng-metadata/core';
import { Repository } from '../../../types/common.types';


/**
 * A component that displays the configuration and options for repository signing.
 */
@Component({
  selector: 'repository-signing-config',
  templateUrl: '/static/js/directives/ui/repository-signing-config/repository-signing-config.component.html',
})
export class RepositorySigningConfigComponent {

  @Input('<') public repository: Repository;

  private enableTrustInfo: {[key: string]: string} = null;
  private disableTrustInfo: {[key: string]: string} = null;
  private inReadOnlyMode: boolean = false;

  constructor(@Inject("ApiService") private ApiService: any,
              @Inject('StateService') private StateService: any) {
    this.inReadOnlyMode = StateService.inReadOnlyMode();
  }

  private askChangeTrust(newState: boolean) {
    if (newState) {
      this.enableTrustInfo = {};
    } else {
      this.disableTrustInfo = {};
    }
  }

  private changeTrust(newState: boolean, callback: (success: boolean) => void) {
    var params = {
      'repository': this.repository.namespace + '/' + this.repository.name,
    };

    var data = {
      'trust_enabled': newState,
    };

    var errorDisplay = this.ApiService.errorDisplay('Could not change trust', callback);
    this.ApiService.changeRepoTrust(data, params).then((resp) => {
      this.repository.trust_enabled = newState;
      callback(true);
    }, errorDisplay);
  }
}
