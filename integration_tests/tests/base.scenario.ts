import { browser, ExpectedConditions as until, $, $$ } from 'protractor';

import { appHost, testName, userName, userPasswd } from '../protractor.conf';
import * as loginView from '../views/login.view';

const JASMINE_DEFAULT_TIMEOUT_INTERVAL = jasmine.DEFAULT_TIMEOUT_INTERVAL;
const JASMINE_EXTENDED_TIMEOUT_INTERVAL = 1000 * 60 * 3;

const BROWSER_TIMEOUT = 15000;

describe('Login', async() => {
  beforeAll(async() => {
    await browser.get(appHost);
    await browser.sleep(3000); // Wait long enough for the login redirect to complete
      // Extend the default jasmine timeout interval just in case it takes a while for the htpasswd idp to be ready
    jasmine.DEFAULT_TIMEOUT_INTERVAL = JASMINE_EXTENDED_TIMEOUT_INTERVAL;
  });

  afterAll(() => {
      // Set jasmine timeout interval back to the original value after these tests are done
    jasmine.DEFAULT_TIMEOUT_INTERVAL = JASMINE_DEFAULT_TIMEOUT_INTERVAL;
  });

  it('logs in with provided user account', async() => {
    await loginView.login(userName, userPasswd);
    expect(browser.getCurrentUrl()).toContain(appHost);
    expect(loginView.userDropdown.getText()).toContain(userName);
  });

});

