import { element, by, browser, $, ElementFinder, ExpectedConditions as until } from 'protractor';


export class CorTabsViewObject {

  public selectTabByTitle(title: string) {
    return $(`cor-tab[tab-title="${title}"] a`).click();
  }

  public isActiveTab(title: string) {
    return $(`cor-tab[tab-title="${title}"] .cor-tab-itself.active`).isPresent();
  }
}
