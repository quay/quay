import { NgModule } from 'ng-metadata/core';
import { CorTabsComponent } from './cor-tabs.component';
import { CorTabComponent } from './cor-tab/cor-tab.component';
import { CorNavTabsDirective } from './cor-nav-tabs/cor-nav-tabs.directive';
import { CorTabContentComponent } from './cor-tab-content/cor-tab-content.component';
import { CorTabPaneComponent } from './cor-tab-pane/cor-tab-pane.component';
import { CorTabPanelComponent } from './cor-tab-panel/cor-tab-panel.component';
import { CorCookieTabsDirective } from './cor-cookie-tabs/cor-cookie-tabs.directive';


/**
 * Module containing everything needed for cor-tabs.
 */
@NgModule({
  imports: [

  ],
  declarations: [
    CorNavTabsDirective,
    CorTabComponent,
    CorTabContentComponent,
    CorTabPaneComponent,
    CorTabPanelComponent,
    CorTabsComponent,
    CorCookieTabsDirective,
  ],
  providers: [

  ]
})
export class CorTabsModule {

}
