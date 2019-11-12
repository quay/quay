import { Component } from 'ng-metadata/core';


/**
 * A component that is placed under a cor-tabs to wrap tab content with additional styling.
 */
@Component({
  selector: 'cor-tab-content',
  templateUrl: '/static/js/directives/ui/cor-tabs/cor-tab-content/cor-tab-content.component.html',
  legacy: {
    transclude: true,
    replace: true,
  }
})
export class CorTabContentComponent {

}
