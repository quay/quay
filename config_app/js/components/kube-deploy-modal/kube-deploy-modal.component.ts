import { Input, Component, Inject, OnDestroy } from 'ng-metadata/core';
import { AngularPollChannel, PollHandle } from "../../services/services.types";
const templateUrl = require('./kube-deploy-modal.component.html');
const styleUrl = require('./kube-deploy-modal.css');

// The response from the API about deployment rollout status
type DeploymentRollout = {
    status: 'available' | 'progressing' | 'failed',
    message: string
};

type DeploymentStatus = {
    name: string,
    numPods: number,
    message?: string,
    pollHandler?: PollHandle,
}

const DEPLOYMENT_POLL_SLEEPTIME = 5000; /* 5 seconds */

@Component({
    selector: 'kube-deploy-modal',
    templateUrl,
    styleUrls: [ styleUrl ],
})
export class KubeDeployModalComponent implements OnDestroy {
    @Input('<') public loadedConfig;
    private state
        : 'loadingDeployments'
        | 'readyToDeploy'
        | 'deployingConfiguration'
        | 'cyclingDeployments'
        | 'deployed'
        | 'error'
        | 'rolledBackWarning' = 'loadingDeployments';
    private errorMessage: string;
    private deploymentsStatus: DeploymentStatus[] = [];
    private deploymentsCycled: number = 0;
    private onDestroyListeners: Function[] = [];
    private rollingBackStatus
        : 'none'
        | 'offer'
        | 'rolling' = 'none';

    constructor(@Inject('ApiService') private ApiService, @Inject('AngularPollChannel') private AngularPollChannel: AngularPollChannel) {
        ApiService.scGetNumDeployments().then(resp => {
            this.deploymentsStatus = resp.items.map(dep => ({ name: dep.metadata.name, numPods: dep.spec.replicas }));
            this.state = 'readyToDeploy';
        }).catch(err => {
            this.state = 'error';
            this.errorMessage = `There are no Quay deployments active in this namespace. \
                                Please check that you are running this \
                                tool in the same namespace as the Red Hat Quay application\
                                Associated error message: ${err.toString()}`;
        })
    }

    // Call all listeners of the onDestroy
    ngOnDestroy(): any {
        this.onDestroyListeners.forEach(fn => {
            fn()
        });
    }


    deployConfiguration(): void {
        this.ApiService.scDeployConfiguration().then(() => {
            this.state = 'deployingConfiguration';
            const deploymentNames: string[] = this.deploymentsStatus.map(dep => dep.name);

            this.ApiService.scCycleQEDeployments({ deploymentNames }).then(() => {
                this.state = 'cyclingDeployments';
                this.watchDeployments();
            }).catch(err => {
                this.state = 'error';
                this.errorMessage = `Could not cycle the deployments with the new configuration. Error: ${err.toString()}`;
            })
        }).catch(err => {
            this.state = 'error';
            this.errorMessage = `Could not deploy the configuration. Error: ${err.toString()}`;
        })
    }

    watchDeployments(): void {
        this.deploymentsStatus.forEach(deployment => {
            const pollChannel = this.AngularPollChannel.create({
                // Have to mock the scope object for the poll channel since we're calling into angular1 code
                // We register the onDestroy function to be called later when this object is destroyed
                '$on': (_, onDestruction) => { this.onDestroyListeners.push(onDestruction) }
            }, this.getDeploymentStatus(deployment), DEPLOYMENT_POLL_SLEEPTIME);

            pollChannel.start();
        });
    }

    // Query each deployment every 5s, and stop polling once it's either available or failed
    getDeploymentStatus(deployment: DeploymentStatus): (boolean) => void {
        return (continue_callback: (shouldContinue: boolean) => void) => {
            const params = {
                'deployment': deployment.name
            };

            this.ApiService.scGetDeploymentRolloutStatus(null, params).then((deploymentRollout: DeploymentRollout) => {
                if (deploymentRollout.status === 'available') {
                    continue_callback(false);

                    this.deploymentsCycled++;
                    if (this.deploymentsCycled === this.deploymentsStatus.length) {
                        this.state = 'deployed';
                    }
                } else if (deploymentRollout.status === 'progressing') {
                    continue_callback(true);
                    deployment.message = deploymentRollout.message;
                } else { // deployment rollout failed
                    this.state = 'error';
                    continue_callback(false);
                    deployment.message = deploymentRollout.message;
                    this.errorMessage = `Could not cycle deployments: ${deploymentRollout.message}`;

                    // Only offer rollback if we loaded/populated a config. (Can't rollback an initial setup)
                    if (this.loadedConfig) {
                        this.rollingBackStatus = 'offer';
                        this.errorMessage = `Could not cycle deployments: ${deploymentRollout.message}`;
                    }
                }
            }).catch(err => {
                continue_callback(false);
                this.state = 'error';
                this.errorMessage = `Could not cycle the deployments with the new configuration. Error: ${err.toString()}\
                                     Would you like to rollback the deployment to its previous state?`;
                // Only offer rollback if we loaded/populated a config. (Can't rollback an initial setup)
                if (this.loadedConfig) {
                    this.rollingBackStatus = 'offer';
                    this.errorMessage = `Could not get deployment information for: ${deployment}`;
                }
            });
        }
    }

    rollbackDeployments(): void {
        this.rollingBackStatus = 'rolling';
        const deploymentNames: string[] = this.deploymentsStatus.map(dep => dep.name);

        this.ApiService.scRollbackDeployments({ deploymentNames }).then(() => {
            this.state = 'rolledBackWarning';
            this.rollingBackStatus = 'none';
        }).catch(err => {
            this.rollingBackStatus = 'none';
            this.state = 'error';
            this.errorMessage = `Could not cycle the deployments back to their previous states. Please contact support: ${err.toString()}`;
        })
    }
}