import { Config, browser } from 'protractor';
import * as request from 'request';


/*
* Use a set environment variable or default value for the app host.
*/
export const appHost: string = process.env.APP_HOST || 'http://localhost:5000';


/**
 * Protractor is configured to run against a Selenium instance running locally on port 4444 and a Quay instance running
 * locally on port 5000.
 * Easiest method is running the Quay and Selenium containers:
 *     $ docker run -d --net=host -v /dev/shm:/dev/shm selenium/standalone-chrome:3.4.0
 *     $ docker run -d --net=host quay.io/quay/quay
 *     $ yarn run e2e
 */
export const config: Config = {
  framework: 'jasmine',
  seleniumAddress: 'http://localhost:4444/wd/hub',
  // Uncomment to run tests against local Chrome instance
  // directConnect: true,
  capabilities: {
    browserName: 'chrome',
    chromeOptions: {
      args: [
        '--disable-infobars'
      ],
      prefs: {
        'profile.password_manager_enabled': false,
        'credentials_enable_service': false,
        'password_manager_enabled': false
      }
    }
  },
  onPrepare: () => {
    browser.driver.manage().window().maximize();

    // Resolve promise when request returns HTTP 200
    return new Promise((resolve, reject) => {
      const pollServer = (success, failure) => {
        request(appHost, (error, response, body) => {
          if (!error && response.statusCode == 200) {
            console.log(`Successfully connected to server at ${appHost}`);
            success();
          } else {
            console.log(`Could not connect to server at ${appHost}`);
            setTimeout(() => {
              failure(success, failure);
            }, 5000);
          }
        });
      };

      pollServer(resolve, pollServer);
    });
  },
  onComplete: () => {
    browser.close();
  },
  specs: [
    // './e2e/sanity.scenario.ts',
    // './e2e/trigger-creation.scenario.ts',
    './e2e/image-repo.scenario.ts',
  ],
};
