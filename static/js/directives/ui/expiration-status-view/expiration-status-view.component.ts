import { Input, Component, Inject } from 'ng-metadata/core';
import * as moment from "moment";
import './expiration-status-view.component.css';

type expirationInfo = {
  className: string;
  icon: string;
};

/**
 * A component that displays expiration status.
 */
@Component({
  selector: 'expiration-status-view',
  templateUrl: '/static/js/directives/ui/expiration-status-view/expiration-status-view.component.html',
})
export class ExpirationStatusViewComponent {
  @Input('<') public expirationDate: Date;

  private getExpirationInfo(expirationDate): expirationInfo|null {
    if (!expirationDate) {
      return null;
    }

    const expiration = moment(expirationDate);
    if (moment().isAfter(expiration)) {
      return {'className': 'expired', 'icon': 'fa-warning'};
    }

    if (moment().add(1, 'week').isAfter(expiration)) {
      return {'className': 'critical', 'icon': 'fa-warning'};
    }

    if (moment().add(1, 'month').isAfter(expiration)) {
      return {'className': 'warning', 'icon': 'fa-warning'};
    }

    return {'className': 'info', 'icon': 'fa-clock-o'};
  }
}
