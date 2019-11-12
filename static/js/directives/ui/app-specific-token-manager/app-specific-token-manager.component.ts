import { Input, Component, Inject } from 'ng-metadata/core';
import * as bootbox from "bootbox";

/**
 * A component that displays and manage all app specific tokens for a user.
 */
@Component({
  selector: 'app-specific-token-manager',
  templateUrl: '/static/js/directives/ui/app-specific-token-manager/app-specific-token-manager.component.html',
})
export class AppSpecificTokenManagerComponent {
  private appTokensResource: any;
  private appTokens: Array<any>;
  private tokenCredentials: any;
  private revokeTokenInfo: any;
  private inReadOnlyMode: boolean;

  constructor(@Inject('ApiService') private ApiService: any, @Inject('UserService') private UserService: any,
              @Inject('NotificationService') private NotificationService: any,
              @Inject('StateService') private StateService: any) {
    this.loadTokens();
    this.inReadOnlyMode = StateService.inReadOnlyMode();
  }

  private loadTokens() {
    this.appTokensResource = this.ApiService.listAppTokensAsResource().get((resp) => {
      this.appTokens = resp['tokens'];
    });
  }

  private askCreateToken() {
    bootbox.prompt('Please enter a descriptive title for the new application token', (title) => {
      if (!title) { return; }

      const errorHandler = this.ApiService.errorDisplay('Could not create the application token');
      this.ApiService.createAppToken({title}).then((resp) => {
        this.loadTokens();        
      }, errorHandler);
    });
  }

  private showRevokeToken(token) {
    this.revokeTokenInfo = {
      'token': token,
    };
  };

  private revokeToken(token, callback) {
    const errorHandler = this.ApiService.errorDisplay('Could not revoke application token', callback);
    const params = {
      'token_uuid': token['uuid'],
    };

    this.ApiService.revokeAppToken(null, params).then((resp) => {
      this.loadTokens();

      // Update the notification service so it hides any banners if we revoked an expiring token.
      this.NotificationService.update();
      callback(true);
    }, errorHandler);
  }

  private showToken(token) {
    const errorHandler = this.ApiService.errorDisplay('Could not find application token');
    const params = {
      'token_uuid': token['uuid'],
    };

    this.ApiService.getAppToken(null, params).then((resp) => {
      this.tokenCredentials = {
        'title': resp['token']['title'],
        'namespace': this.UserService.currentUser().username,
        'username': '$app',
        'password': resp['token']['token_code'],
      };
    }, errorHandler);
  }
}
