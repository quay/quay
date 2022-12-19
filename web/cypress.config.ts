import {defineConfig} from 'cypress';

export default defineConfig({
  e2e: {
    env: {
      REACT_QUAY_APP_API_URL: 'http://localhost:8080',
    },
    baseUrl: 'http://localhost:9000',
    video: false,
    defaultCommandTimeout: 20000,
    setupNodeEvents(on, config) {
      // implement node event listeners here
    },
  },
});
