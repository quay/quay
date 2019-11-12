import {Input, Component, Inject, Output, EventEmitter} from 'ng-metadata/core';
const templateUrl = require('./download-tarball-modal.component.html');
const styleUrl = require('./download-tarball-modal.css');

declare const FileSaver: any;

/**
 * Initial Screen and Choice in the Config App
 */
@Component({
    selector: 'download-tarball-modal',
    templateUrl: templateUrl,
    styleUrls: [ styleUrl ],
})
export class DownloadTarballModalComponent {
    @Input('<') public loadedConfig;
    @Input('<') public isKubernetes;
    @Output() public chooseDeploy = new EventEmitter<any>();

    constructor(@Inject('ApiService') private ApiService) {

    }

    private downloadTarball(): void {
        const errorDisplay: Function = this.ApiService.errorDisplay(
          'Could not save configuration. Please report this error.'
        );

        // We need to set the response type to 'blob', to ensure it's never encoded as a string
        // (string encoded binary data can be difficult to transform with js)
        // and to make it easier to save (FileSaver expects a blob)
        this.ApiService.scGetConfigTarball(null, null, null, null, 'blob').then(function(resp) {
            FileSaver.saveAs(resp, 'quay-config.tar.gz');
        }, errorDisplay);
    }

    private goToDeploy() {
        this.chooseDeploy.emit({});
    }
}
