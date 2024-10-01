import {defineConfig} from 'cypress';

export default defineConfig({
  chromeWebSecurity: false, // Required for stripe integration tests
  e2e: {
    env: {
      REACT_QUAY_APP_API_URL: 'http://localhost:8080',
    },
    baseUrl: 'http://localhost:9000',
    video: false,
    defaultCommandTimeout: 25000,
    retries: 3,
    setupNodeEvents(on, config) {
      // implement node event listeners here
    },
  },
  viewportWidth: 1280,
  viewportHeight: 800,
});
