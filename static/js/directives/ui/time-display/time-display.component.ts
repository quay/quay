import { Input, Component } from 'ng-metadata/core';

/**
 * A component that displays when an event occurred.
 */
@Component({
  selector: 'timeDisplay',
  templateUrl: '/static/js/directives/ui/time-display/time-display.component.html'
})
export class TimeDisplayComponent {
  @Input('<') public datetime: any;
  @Input('<') public dateOnly: boolean;

  private getFormat(dateOnly: boolean): string {
    if (dateOnly) {
      return 'll';
    }

    return 'llll';
  }
}
