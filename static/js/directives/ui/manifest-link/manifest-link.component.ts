import { Input, Component, Inject } from 'ng-metadata/core';
import { Repository } from '../../../types/common.types';


/**
 * A component that links to a manifest view.
 */
@Component({
  selector: 'manifest-link',
  templateUrl: '/static/js/directives/ui/manifest-link/manifest-link.component.html'
})
export class ManifestLinkComponent {

  @Input('<') public repository: Repository;
  @Input('<') public manifestDigest: string;
  @Input('<') public imageId: string;

  private showingCopyBox: boolean = false;

  constructor(@Inject('$timeout') private $timeout, @Inject('$element') private $element) {
  }

  private hasSHA256(digest: string) {
    return digest && digest.indexOf('sha256:') == 0;
  }

  private getShortDigest(digest: string) {
    if (!digest) { return ''; }
    return digest.substr('sha256:'.length).substr(0, 12);
  }

  private showCopyBox() {
    this.showingCopyBox = true;

    // Necessary to wait for digest cycle to complete.
    this.$timeout(() => {
      this.$element.find('.modal').modal('show');
    }, 10);
  };

  private hideCopyBox() {
    this.$element.find('.modal').modal('hide');

    // Wait for the modal to hide before removing from the DOM.
    this.$timeout(() => {
      this.showingCopyBox = false;
    }, 10);
  };
}
