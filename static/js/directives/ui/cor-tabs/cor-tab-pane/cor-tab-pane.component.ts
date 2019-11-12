import { Component, Input, Inject, Host, OnInit } from 'ng-metadata/core';
import { CorTabPanelComponent } from '../cor-tab-panel/cor-tab-panel.component';
import 'rxjs/add/operator/filter';


/**
 * A component that creates a single tab pane under a cor-tabs component.
 */
@Component({
  selector: 'cor-tab-pane',
  templateUrl: '/static/js/directives/ui/cor-tabs/cor-tab-pane/cor-tab-pane.component.html',
  legacy: {
    transclude: true,
  }
})
export class CorTabPaneComponent implements OnInit {

  @Input('@') public id: string;

  public isActiveTab: boolean = false;

  constructor(@Host() @Inject(CorTabPanelComponent) private panel: CorTabPanelComponent) {

  }

  public ngOnInit(): void {
    this.panel.addTabPane(this);

    this.panel.activeTab
      .filter(tabId => tabId != undefined)
      .subscribe((tabId: string) => {
        this.isActiveTab = (this.id === tabId);
      });
  }
}
