import { NgModule } from 'ng-metadata/core';

import { ConfigSetupAppComponent } from './components/config-setup-app/config-setup-app.component';

import * as restangular from 'restangular';

const quayDependencies: any[] = [
    restangular,
];

@NgModule(({
    imports: quayDependencies,
    declarations: [],
    providers: [
        provideConfig,
    ]
}))
class DependencyConfig { }


provideConfig.$inject = [
    '$provide',
    '$injector',
    '$compileProvider',
    'RestangularProvider',
];

function provideConfig($provide: ng.auto.IProvideService,
    $injector: ng.auto.IInjectorService,
    $compileProvider: ng.ICompileProvider,
    RestangularProvider: any): void {

    // Configure the API provider.
    RestangularProvider.setBaseUrl('/api/v1/');
}


@NgModule({
    imports: [
        DependencyConfig,
    ],
    declarations: [
        ConfigSetupAppComponent,
    ],
    providers: []
})
export class ConfigAppModule { }
