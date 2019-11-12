import { Component, Inject } from 'ng-metadata/core';
const templateUrl = require('./config-setup-app.component.html');

declare var window: any;

/**
 * Initial Screen and Choice in the Config App
 */
@Component({
    selector: 'config-setup-app',
    templateUrl: templateUrl,
})
export class ConfigSetupAppComponent {
    private state
        : 'choice'
        | 'setup'
        | 'load'
        | 'download'
        | 'deploy';

    private loadedConfig = false;
    private kubeNamespace: string | boolean = false;

    constructor(@Inject('ApiService') private apiService) {
        this.state = 'choice';
        if (window.__kubernetes_namespace) {
            this.kubeNamespace = window.__kubernetes_namespace;
        }
    }

    private chooseSetup(): void {
        this.apiService.scStartNewConfig()
            .then(() => {
                this.state = 'setup';
            })
            .catch(this.apiService.errorDisplay(
                'Could not initialize new setup. Please report this error'
        ));
    }

    private chooseLoad(): void {
        this.state = 'load';
        this.loadedConfig = true;
    }

    private choosePopulate(): void {
        this.apiService.scKubePopulateConfig()
            .then(() => {
                this.state = 'setup';
                this.loadedConfig = true;
            })
            .catch(err => {
                this.apiService.errorDisplay(
                    `Could not populate the configuration from your cluster. Please report this error: ${JSON.stringify(err)}`
                )()
            })
    }

    private configLoaded(): void {
        this.state = 'setup';
    }

    private setupCompleted(): void {
        this.state = 'download';
    }

    private chooseDeploy(): void {
        this.state = 'deploy';
    }
}
