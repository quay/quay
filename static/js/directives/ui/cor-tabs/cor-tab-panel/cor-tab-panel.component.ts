import { Component, Input, Output, EventEmitter, OnChanges, SimpleChanges, OnInit } from 'ng-metadata/core';
import { CorTabComponent } from '../cor-tab/cor-tab.component';
import { CorTabPaneComponent } from '../cor-tab-pane/cor-tab-pane.component';
import { BehaviorSubject } from 'rxjs/BehaviorSubject';


/**
 * A component that contains a cor-tabs and handles all of its logic.
 */
@Component({
  selector: 'cor-tab-panel',
  templateUrl: '/static/js/directives/ui/cor-tabs/cor-tab-panel/cor-tab-panel.component.html',
  legacy: {
    transclude: true
  }
})
export class CorTabPanelComponent implements OnInit, OnChanges {

  @Input('@') public orientation: 'horizontal' | 'vertical' = 'horizontal';

  @Output() public tabChange: EventEmitter<string> = new EventEmitter();

  public basePath: string;
  public activeTab = new BehaviorSubject<string>(null);

  private tabs: CorTabComponent[] = [];
  private tabPanes: {[id: string]: CorTabPaneComponent} = {};

  public ngOnInit(): void {
    this.activeTab.subscribe((tabId: string) => {
      // Catch null values and replace with tabId of first tab
      if (!tabId && this.tabs[0]) {
        this.activeTab.next(this.tabs[0].tabId);
      } else {
        this.tabChange.emit(tabId);
      }
    });
  }

  public ngOnChanges(changes: SimpleChanges): void {
    switch (Object.keys(changes)[0]) {
      case 'selectedIndex':
        if (this.tabs.length > changes['selectedIndex'].currentValue) {
          this.activeTab.next(this.tabs[changes['selectedIndex'].currentValue].tabId);
        }
        break;
    }
  }

  public addTab(tab: CorTabComponent): void {
    this.tabs.push(tab);

    if (!this.activeTab.getValue()) {
      this.activeTab.next(this.tabs[0].tabId);
    }
  }

  public addTabPane(tabPane: CorTabPaneComponent): void {
    this.tabPanes[tabPane.id] = tabPane;
  }

  public isVertical(): boolean {
    return this.orientation == 'vertical';
  }
}
