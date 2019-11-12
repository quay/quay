import { browser } from 'protractor';
import { appHost } from '../protractor.conf';


describe("sanity test", () => {

  beforeEach(() => {
    browser.get(appHost);
  });

  it("loads home view with no AngularJS errors", () => {
    browser.manage().logs().get('browser')
      .then((browserLog: any) => {
        browserLog.forEach((log: any) => {
          expect(log.message).not.toContain("angular");
        });
      });
  });
});
