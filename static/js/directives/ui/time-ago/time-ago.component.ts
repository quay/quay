import { Input, Component } from 'ng-metadata/core';

/**
 * A component that displays how long ago an event occurred, with associated
 * tooltip showing the actual time.
 */
@Component({
  selector: 'timeAgo',
  templateUrl: '/static/js/directives/ui/time-ago/time-ago.component.html'
})
export class TimeAgoComponent {
  @Input('<') public datetime: any;
}
