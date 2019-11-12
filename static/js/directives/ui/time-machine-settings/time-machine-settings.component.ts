import { Input, Component, Inject } from 'ng-metadata/core';
import * as moment from "moment";


/**
 * A component that displays settings for a namespace for time machine.
 */
@Component({
  selector: 'timeMachineSettings',
  templateUrl: '/static/js/directives/ui/time-machine-settings/time-machine-settings.component.html'
})
export class TimeMachineSettingsComponent implements ng.IComponentController {

  @Input('<') public user: any;
  @Input('<') public organization: any;

  private initial_s: number;
  private current_s: number;
  private updating: boolean;

  constructor(@Inject('Config') private Config: any, @Inject('ApiService') private ApiService: any,
               @Inject('Features') private Features: any) {
    this.current_s = 0;
    this.initial_s = 0;
    this.updating = false;
  }

  public $onInit(): void {
    if (this.user) {
      this.current_s = this.user.tag_expiration_s;
      this.initial_s = this.user.tag_expiration_s;
    } else if (this.organization) {
      this.current_s = this.organization.tag_expiration_s;
      this.initial_s = this.organization.tag_expiration_s;
    }
  }

  private getSeconds(durationStr: string): number {
    if (!durationStr) {
      return 0;
    }

    var number = durationStr.substring(0, durationStr.length - 1);
    var suffix = durationStr.substring(durationStr.length - 1);
    return moment.duration(parseInt(number), <moment.unitOfTime.Base>suffix).asSeconds();
  }

  private durationExplanation(durationSeconds: number): string {
    return moment.duration(durationSeconds || 0, 's').humanize();
  }

  private updateExpiration(): void {
    this.updating = true;
    var errorDisplay = this.ApiService.errorDisplay('Could not update time machine setting', () => {
      this.updating = false;
    });

    var method = (this.user ? this.ApiService.changeUserDetails :
                              this.ApiService.changeOrganizationDetails);
    var params = {};
    if (this.organization) {
      params['orgname'] = this.organization.name;
    }

    var data = {
      'tag_expiration_s': this.current_s,
    };

    method(data, params).then((resp) => {
      this.updating = false;
      this.initial_s = this.current_s;
    }, errorDisplay);
  }
}
