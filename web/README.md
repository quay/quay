# Quay UI

UI for Quay based on React and Patternfly framework 

## Installation

It is assumed that you have a Quay instance running that you can point the UI to.
Run the following commands to get started

```bash
git clone https://github.com/quay/quay-ui.git
cd quay-ui
npm install
```

## Development

Start the dev server by running

```bash
npm start
```

Runs the app in the development mode.\
Open [http://localhost:9000](http://localhost:9000) to view it in the browser.

The page will reload if you make edits.\
You will also see any lint errors in the console.

By default the UI connects to the quay backend for API. If you don't have 
a backend or want to develop without a backend you can set the environment
variable `MOCK_API=true` before running `npm start`.

In order for you to use this with a Quay backend, you need to configure CORS on the Quay side.
Add the following to your `config.yaml` in Quay

```yaml
CORS_ORIGIN: "http://localhost:9000"
```

If you are using `docker-compose` for local development, you can add this to `local-dev/stack/config.yaml` 
in the Quay repo.

## Testing

```bash
npm test
```

Launches the test runner in the interactive watch mode.\
See the section about [running tests](https://facebook.github.io/create-react-app/docs/running-tests) for more information.

### Integration Tests

Integration tests are ran via [Cypress](https://docs.cypress.io/). The URL under test defaults to `http://localhost:9000` and can be overriden with the `baseUrl` parameter in the `cypress.config.ts` file.

To run tests locally:
- Start the application with `npm start`
- When application has started run the tests with `npm run test:integration`

## Building for Production

```bash
npm run build
```

Builds the app for production to the `dist` folder.\
It correctly bundles React in production mode and optimizes the build for the best performance.

The build is minified and the filenames include the hashes.
See the section about [deployment](https://facebook.github.io/create-react-app/docs/deployment) for more information.
