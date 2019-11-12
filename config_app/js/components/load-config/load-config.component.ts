import {
    Component,
    EventEmitter,
    Inject,
    Output,
} from 'ng-metadata/core';
const templateUrl = require('./load-config.component.html');

declare var bootbox: any;

@Component({
    selector: 'load-config',
    templateUrl,
})
export class LoadConfigComponent {
    private readyToSubmit: boolean = false;
    private uploadFunc: Function;
    @Output() public configLoaded: EventEmitter<any> = new EventEmitter();

    private handleTarballSelected(files: File[], callback: Function) {
        this.readyToSubmit = true;
        callback(true)
    }

    private handleTarballCleared() {
        this.readyToSubmit = false;
    }

    private uploadTarball() {
        this.uploadFunc(success => {
            if (success) {
                this.configLoaded.emit({});
            } else {
                bootbox.dialog({
                    "message": 'Could not upload configuration. Please check you have provided a valid tar file' +
                               'If this problem persists, please contact support',
                    "title": 'Error Loading Configuration',
                    "buttons": {
                        "close": {
                            "label": "Close",
                            "className": "btn-primary"
                        }
                    }
                });
            }
        });
    }

    /**
     * When files are validated, this is called by the child to give us
     * the callback function to upload
     * @param files: files to upload
     * @param uploadFiles: function to call to upload files
     */
    private tarballValidatedByUploadBox(files, uploadFiles) {
        this.uploadFunc = uploadFiles;
    }
}