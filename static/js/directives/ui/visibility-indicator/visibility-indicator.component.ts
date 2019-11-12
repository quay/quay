import { Input, Component } from 'ng-metadata/core';


/**
 * A component that displays a box with "Public" or "Private", depending on the visibility
 * of the repository.
 */
@Component({
  selector: 'visibility-indicator',
  templateUrl: '/static/js/directives/ui/visibility-indicator/visibility-indicator.component.html'
})
export class VisibilityIndicatorComponent {

  @Input('<') public repository: any;
}
