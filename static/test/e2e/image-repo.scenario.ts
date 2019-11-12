import { browser, element, by, $, $$ } from 'protractor';
import { appHost } from '../protractor.conf';
import { CorTabsViewObject } from '../../js/directives/ui/cor-tabs/cor-tabs.view-object';


describe("Image Repository", () => {
  const username = 'devtable';
  const password = 'password';
  const repoTabs: CorTabsViewObject = new CorTabsViewObject();

  beforeAll((done) => {
    browser.waitForAngularEnabled(false);

    // Sign in
    browser.get(appHost);
    $$('a[href="/signin/"]').get(1).click();
    $('#signin-username').sendKeys(username);
    $('#signin-password').sendKeys(password);
    element(by.partialButtonText('Sign in')).click();
    browser.sleep(4000);

    // Navigate to image repository
    browser.get(`${appHost}/repository/devtable/simple`).then(() => done());
  });

  afterAll(() => {
    browser.waitForAngularEnabled(true);
  });

  describe("information tab", () => {
    const tabTitle: string = 'Information';

    beforeAll((done) => {
      repoTabs.selectTabByTitle(tabTitle).then(() => done());
    });

    it("displays repository description", () => {
      expect(repoTabs.isActiveTab(tabTitle)).toBe(true);
      expect(element(by.cssContainingText('h4', 'Description')).isDisplayed()).toBe(true);
    });
  });

  describe("tags tab", () => {
    const tabTitle: string = 'Tags';

    beforeAll((done) => {
      repoTabs.selectTabByTitle(tabTitle).then(() => done());
    });

    it("displays repository tags", () => {
      expect(repoTabs.isActiveTab(tabTitle)).toBe(true);
      expect(element(by.cssContainingText('.tab-header', 'Repository Tags')).isDisplayed()).toBe(true);
    });
  });

  describe("tag history tab", () => {
    const tabTitle: string = 'Tag History';

    beforeAll((done) => {
      repoTabs.selectTabByTitle(tabTitle).then(() => done());
    });

    it("displays repository tags", () => {
      expect(repoTabs.isActiveTab(tabTitle)).toBe(true);
      expect(element(by.cssContainingText('.tab-header', 'Tag History')).isDisplayed()).toBe(true);
    });
  });

  describe("builds tab", () => {
    const tabTitle: string = 'Builds';

    beforeAll((done) => {
      repoTabs.selectTabByTitle(tabTitle).then(() => done());
    });

    it("displays repository tags", () => {
      expect(repoTabs.isActiveTab(tabTitle)).toBe(true);
      expect(element(by.cssContainingText('.tab-header', 'Repository Builds')).isDisplayed()).toBe(true);
    });
  });

  describe("usage logs tab", () => {
    const tabTitle: string = 'Usage Logs';

    beforeAll((done) => {
      repoTabs.selectTabByTitle(tabTitle).then(() => done());
    });

    it("displays repository tags", () => {
      expect(repoTabs.isActiveTab(tabTitle)).toBe(true);
      expect(element(by.cssContainingText('h3', 'Usage Logs')).isDisplayed()).toBe(true);
    });
  });

  describe("settings tab", () => {
    const tabTitle: string = 'Settings';

    beforeAll((done) => {
      repoTabs.selectTabByTitle(tabTitle).then(() => done());
    });

    it("displays repository tags", () => {
      expect(repoTabs.isActiveTab(tabTitle)).toBe(true);
      expect(element(by.cssContainingText('.tab-header', 'Settings')).isDisplayed()).toBe(true);
    });
  });

  describe("tabs navigation", () => {

    beforeAll((done) => {
      repoTabs.selectTabByTitle('Information');
      repoTabs.selectTabByTitle('Tags');
      done();
    });

    it("back button returns to previous tab", () => {
      browser.navigate().back();

      expect(repoTabs.isActiveTab('Information')).toBe(true);
    });

    it("forward button returns to next tab", () => {
      browser.navigate().forward();

      expect(repoTabs.isActiveTab('Tags')).toBe(true);
    });
  });
});
