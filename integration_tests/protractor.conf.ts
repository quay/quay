import { Config, browser, logging } from 'protractor';
import { execSync } from 'child_process';
import * as HtmlScreenshotReporter from 'protractor-jasmine2-screenshot-reporter';
import * as _ from 'lodash';
import { TapReporter, JUnitXmlReporter } from 'jasmine-reporters';
import * as ConsoleReporter from 'jasmine-console-reporter';
import * as failFast from 'protractor-fail-fast';
import { createWriteStream } from 'fs';
import { format } from 'util';

const tap = !!process.env.TAP;

export const BROWSER_TIMEOUT = 15000;
export const appHost = `${process.env.QUAY_APP_ADDRESS}${(process.env.QUAY_BASE_PATH || '/').replace(/\/$/, '')}`;
export const testName = `test-${Math.random().toString(36).replace(/[^a-z]+/g, '').substr(0, 5)}`;

const htmlReporter = new HtmlScreenshotReporter({ dest: './gui_test_screenshots', inlineImages: true, captureOnlyFailedSpecs: true, filename: 'test-gui-report.html' });
const junitReporter = new JUnitXmlReporter({ savePath: './gui_test_screenshots', consolidateAll: true });
const browserLogs: logging.Entry[] = [];

//const suite = (tests: string[]) => (!_.isNil(process.env.BRIDGE_KUBEADMIN_PASSWORD) ? ['tests/login.scenario.ts'] : []).concat(['tests/base.scenario.ts', ...tests]);
const suite = (tests: string[]) => (['tests/base.scenario.ts', ...tests]);


export const config: Config = {
  framework: 'jasmine',
  directConnect: true,
  skipSourceMapSupport: true,
  jasmineNodeOpts: {
    print: () => null,
    defaultTimeoutInterval: 40000,
  },
  logLevel: tap ? 'ERROR' : 'INFO',
  plugins: [failFast.init()],
  capabilities: {
    browserName: 'chrome',
    acceptInsecureCerts: true,
    chromeOptions: {
      args: [
        '--disable-gpu',
//        '--headless',
        '--no-sandbox',
        '--window-size=1920,1200',
        '--disable-background-timer-throttling',
        '--disable-renderer-backgrounding',
        '--disable-raf-throttling',
        // Avoid crashes when running in a container due to small /dev/shm size
        // https://bugs.chromium.org/p/chromium/issues/detail?id=715363
        '--disable-dev-shm-usage',
      ],
      prefs: {
        'profile.password_manager_enabled': false,
        'credentials_enable_service': false,
        'password_manager_enabled': false,
      },
    },
/**
 * 'browserName': 'firefox',
 * 'moz:firefoxOptions': {
 *   'args': ['--safe-mode']
 *   }
 */
  },
  beforeLaunch: () => new Promise(resolve => htmlReporter.beforeLaunch(resolve)),
  onPrepare: () => {
    browser.waitForAngularEnabled(false);
    jasmine.getEnv().addReporter(htmlReporter);
    jasmine.getEnv().addReporter(junitReporter);
    if (tap) {
      jasmine.getEnv().addReporter(new TapReporter());
    } else {
      jasmine.getEnv().addReporter(new ConsoleReporter());
    }
  },
  onComplete: async() => {
    const consoleLogStream = createWriteStream('gui_test_screenshots/browser.log', { flags: 'a' });
    browserLogs.forEach(log => {
      const { level, message } = log;
      const messageStr = _.isArray(message) ? message.join(' ') : message;
      consoleLogStream.write(`${format.apply(null, [`[${level.name}]`, messageStr])}\n`);
    });

    const url = await browser.getCurrentUrl();
    console.log('Last browser URL: ', url);

    await browser.close();

    // should add a step to clean up organizations and repos created during
    // testing
//    execSync(`if kubectl get ${resource} ${testName} 2> /dev/null; then kubectl delete ${resource} ${testName}; fi`);
  },
  onCleanUp: (exitCode) => {
    return console.log('Cleaning up completed');
  },
  afterLaunch: (exitCode) => {
    failFast.clean();
    return new Promise(resolve => htmlReporter.afterLaunch(resolve.bind(this, exitCode)));
  },
  suites: {
    filter: suite([
      'tests/filter.scenario.ts',
    ]),
    login: [
      'tests/login.scenario.ts',
    ],
    quaylogin: [
      'tests/quay-login.scenario.ts',
    ],
  },
};

export const checkLogs = async() => (await browser.manage().logs().get('browser'))
  .map(log => {
    browserLogs.push(log);
    return log;
  });

function hasError() {
  return window.windowError;
}
export const checkErrors = async() => await browser.executeScript(hasError).then(err => {
  if (err) {
    fail(`omg js error: ${err}`);
  }
});

export const waitForCount = (elementArrayFinder, expectedCount) => {
  return async() => {
    const actualCount = await elementArrayFinder.count();
    return expectedCount >= actualCount;
  };
};

export const waitForNone = (elementArrayFinder) => {
  return async() => {
    const count = await elementArrayFinder.count();
    return count === 0;
  };
};
