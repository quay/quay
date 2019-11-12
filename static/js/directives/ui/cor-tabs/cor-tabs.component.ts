import { Component, Input, Output, Inject, EventEmitter, Host } from 'ng-metadata/core';
import { CorTabPanelComponent } from './cor-tab-panel/cor-tab-panel.component';


/**
 * A component that holds the actual tabs.
 */
@Component({
  selector: 'cor-tabs',
  templateUrl: '/static/js/directives/ui/cor-tabs/cor-tabs.component.html',
  legacy: {
    transclude: true,
  }
})
export class CorTabsComponent {

  private isClosed: boolean = true;

  constructor(@Host() @Inject(CorTabPanelComponent) private parent: CorTabPanelComponent) {

  }

  private toggleClosed(e): void {
    this.isClosed = !this.isClosed;
  }
}
