import { Directive, Inject, Host, AfterContentInit, Input } from 'ng-metadata/core';
import { CorTabPanelComponent } from '../cor-tab-panel/cor-tab-panel.component';


/**
 * Adds routing capabilities to cor-tab-panel, either using URL query parameters, or browser cookie.
 */
@Directive({
  selector: '[corNavTabs]'
})
export class CorNavTabsDirective implements AfterContentInit {

  constructor(@Host() @Inject(CorTabPanelComponent) private panel: CorTabPanelComponent,
              @Inject('$location') private $location: ng.ILocationService,
              @Inject('$rootScope') private $rootScope: ng.IRootScopeService) {
    this.$rootScope.$on('$routeUpdate', () => {
      const tabId: string = this.$location.search()['tab'];
      this.panel.activeTab.next(tabId);
    });
  }

  public ngAfterContentInit(): void {
    this.panel.basePath = this.$location.path();

    // Set initial tab
    const tabId: string = this.$location.search()['tab'];
    this.panel.activeTab.next(tabId);
  }
}
