Quay Integration Testing
============================

## Dependencies:

1. [node.js](https://nodejs.org/) >= 8 & [yarn](https://yarnpkg.com/en/docs/install) >= 1.3.2
2. Google Chrome/Chromium >= 60 (needs --headless flag) for integration tests

### Install Dependencies

To install the dependencies:
```
yarn install
```
You must run this command once, and every time the dependencies change. `node_modules` are not committed to git.

## Integration Tests

Integration tests are run in a headless Chrome driven by [protractor](http://www.protractortest.org/#/).  Requirements include Chrome, a working Quay, podman.

Setup (or any time you change node_modules - `yarn add` or `yarn install`)
```
cd integration_tests && yarn run webdriver-update
```

Run integration tests:
```
yarn run test-all
```

Run integration tests against a specific test suite:
```
yarn run test-suite --suite <test suite>
```
Could check test suite list in package.json.

### Required Environment Varaiable

```
export QUAY_APP_ADDRESS=<Quay Hostname>
export QUAY_INTERNAL_USERNAME=<Username>
export QUAY_INTERNAL_PASSWORD=<Password>
```

### Hacking Integration Tests

To see what the tests are actually doing, it is posible to run in none `headless` mode by setting the `NO_HEADLESS` environment variable:

```
$ NO_HEADLESS=true yarn run test-suite --suite <test suite>
```

To avoid skipping remaining portion of tests upon encountering the first failure, `NO_FAILFAST` environment variable can be used:

```
$ NO_FAILFAST=true yarn run test-suite --suite <test suite>
```

### Debugging Integration Tests

1. Add `debugger;` statements to any test suite
2. `yarn run debug-test-suite --suite <suite-to-debug>`
3. Chrome browser URL: 'chrome://inspect/#devices', click on the 'inspect' link in **Target (v10...)** section.
4. Launches chrome-dev tools, click Resume button to continue
5. Will break on any `debugger;` statements
6. Pauses browser when not using `--headless` argument!

## Supported Browsers

Support the latest versions of the following browsers:

- Edge
- Chrome
- Safari
- Firefox

