import { NgModule } from 'ng-metadata/core';
import * as restangular from 'restangular';

import { ConfigSetupAppComponent } from './components/config-setup-app/config-setup-app.component';
import { DownloadTarballModalComponent } from './components/download-tarball-modal/download-tarball-modal.component';
import { LoadConfigComponent } from './components/load-config/load-config.component';
import { KubeDeployModalComponent } from './components/kube-deploy-modal/kube-deploy-modal.component';
import { MarkdownModule } from './components/markdown/markdown.module';
import { MarkdownInputComponent } from './components/markdown/markdown-input.component';
import { MarkdownViewComponent } from './components/markdown/markdown-view.component';
import { MarkdownToolbarComponent } from './components/markdown/markdown-toolbar.component';
import { MarkdownEditorComponent } from './components/markdown/markdown-editor.component';

const quayDependencies: any[] = [
    'restangular',
    'ngCookies',
    'angularFileUpload',
    'ngSanitize',
];

@NgModule(({
    imports: quayDependencies,
    declarations: [],
    providers: [
        provideConfig,
    ]
}))
class DependencyConfig{}


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
        MarkdownModule,
    ],
    declarations: [
        ConfigSetupAppComponent,
        DownloadTarballModalComponent,
        LoadConfigComponent,
        KubeDeployModalComponent,
        MarkdownInputComponent,
        MarkdownViewComponent,
        MarkdownToolbarComponent,
        MarkdownEditorComponent,
    ],
    providers: []
})
export class ConfigAppModule {}
