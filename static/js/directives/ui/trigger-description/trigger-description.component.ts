import { Component, Input, Inject } from 'ng-metadata/core';
import { Trigger } from '../../../types/common.types';


/**
 * A component which displays information about a build trigger.
 */
@Component({
  selector: 'trigger-description',
  templateUrl: '/static/js/directives/ui/trigger-description/trigger-description.component.html'
})
export class TriggerDescriptionComponent {

  @Input('<') public trigger: Trigger;

  constructor(@Inject('TriggerService') private triggerService: any,
              @Inject('KeyService') private keyService: any) {

  }
}
