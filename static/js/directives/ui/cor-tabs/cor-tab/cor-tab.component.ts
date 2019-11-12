import { Component, Input, Output, Inject, EventEmitter, Host, OnInit } from 'ng-metadata/core';
import { CorTabPanelComponent } from '../cor-tab-panel/cor-tab-panel.component';
import 'rxjs/add/operator/filter';


/**
 * A component that creates a single tab under a cor-tabs component.
 */
@Component({
  selector: 'cor-tab',
  templateUrl: '/static/js/directives/ui/cor-tabs/cor-tab/cor-tab.component.html',
  legacy: {
    transclude: true,
  }
})
export class CorTabComponent implements OnInit {
  @Input('@') public tabId: string;
  @Input('@') public tabTitle: string;
  @Input('<') public tabActive: boolean = false;

  @Output() public tabInit: EventEmitter<any> = new EventEmitter();
  @Output() public tabShow: EventEmitter<any> = new EventEmitter();
  @Output() public tabHide: EventEmitter<any> = new EventEmitter();

  private isActive: boolean = false;

  constructor(@Host() @Inject(CorTabPanelComponent) private panel: CorTabPanelComponent) {

  }

  public ngOnInit(): void {
    this.isActive = this.tabActive;

    this.panel.activeTab
      .filter(tabId => tabId != undefined)
      .subscribe((tabId: string) => {
        if (!this.isActive && this.tabId === tabId) {
          this.isActive = true;
          this.tabInit.emit({});
          this.tabShow.emit({});
        } else if (this.isActive && this.tabId !== tabId) {
          this.isActive = false;
          this.tabHide.emit({});
        }
      });

    this.panel.addTab(this);
  }

  private tabClicked(event: MouseEvent): void {
    if (!this.panel.basePath) {
      event.preventDefault();
      this.panel.activeTab.next(this.tabId);
    }
  }
}
