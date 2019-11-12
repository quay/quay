import { Directive, Inject, Host, AfterContentInit, Input } from 'ng-metadata/core';
import { CorTabPanelComponent } from '../cor-tab-panel/cor-tab-panel.component';


/**
 * Adds routing capabilities to cor-tab-panel using a browser cookie.
 */
@Directive({
  selector: '[corCookieTabs]'
})
export class CorCookieTabsDirective implements AfterContentInit {

  @Input('@corCookieTabs') public cookieName: string;

  constructor(@Host() @Inject(CorTabPanelComponent) private panel: CorTabPanelComponent,
              @Inject('CookieService') private cookieService: any) {

  }

  public ngAfterContentInit(): void {
    // Set initial tab
    const tabId: string = this.cookieService.get(this.cookieName);

    this.panel.activeTab.next(tabId);

    this.panel.activeTab.subscribe((tab: string) => {
      this.cookieService.putPermanent(this.cookieName, tab);
    });
  }
}
