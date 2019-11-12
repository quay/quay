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

## Supported Browsers

Support the latest versions of the following browsers:

- Edge
- Chrome
- Safari
- Firefox

