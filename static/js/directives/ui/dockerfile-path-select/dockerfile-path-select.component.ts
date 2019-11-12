import { Input, Output, EventEmitter, Component, OnChanges, SimpleChanges } from 'ng-metadata/core';


/**
 * A component that allows the user to select the location of the Dockerfile in their source code repository.
 */
@Component({
  selector: 'dockerfile-path-select',
  templateUrl: '/static/js/directives/ui/dockerfile-path-select/dockerfile-path-select.component.html'
})
export class DockerfilePathSelectComponent implements OnChanges {

  @Input('<') public currentPath: string = '';
  @Input('<') public paths: string[];
  @Input('<') public supportsFullListing: boolean;
  @Output() public pathChanged: EventEmitter<PathChangeEvent> = new EventEmitter();
  public isValidPath: boolean;
  private isUnknownPath: boolean = true;
  private selectedPath: string | null = null;

  public ngOnChanges(changes: SimpleChanges): void {
    this.isValidPath = this.checkPath(this.currentPath, this.paths, this.supportsFullListing);
  }

  public setPath(path: string): void {
    this.currentPath = path;
    this.selectedPath = null;
    this.isValidPath = this.checkPath(path, this.paths, this.supportsFullListing);

    this.pathChanged.emit({path: this.currentPath, isValid: this.isValidPath});
  }

  public setSelectedPath(path: string): void {
    this.currentPath = path;
    this.selectedPath = path;
    this.isValidPath = this.checkPath(path, this.paths, this.supportsFullListing);

    this.pathChanged.emit({path: this.currentPath, isValid: this.isValidPath});
  }

  private checkPath(path: string = '', paths: string[] = [], supportsFullListing: boolean): boolean {
    this.isUnknownPath = false;
    var isValidPath: boolean = false;

    if (path != null && path.length > 0 && path[0] === '/') {
      isValidPath = true;
      this.isUnknownPath = supportsFullListing && paths.indexOf(path) < 0;
    }
    return isValidPath;
  }
}


/**
 * Dockerfile path changed event.
 */
export type PathChangeEvent = {
  path: string;
  isValid: boolean;
};
