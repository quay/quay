import {defineConfig} from 'cypress';
import {GenerateCtrfReport} from 'cypress-ctrf-json-reporter';

export default defineConfig({
  chromeWebSecurity: false, // Required for stripe integration tests
  e2e: {
    env: {
      REACT_QUAY_APP_API_URL: 'http://localhost:8080',
    },
    baseUrl: 'http://localhost:9000',
    video: false,
    defaultCommandTimeout: 25000,
    retries: 0,
    setupNodeEvents(on, config) {
      // CTRF JSON reporter for test results
      new GenerateCtrfReport({
        on,
        outputDir: 'cypress/reports',
        outputFile: 'ctrf-report.json',
        screenshot: true, // Enable base64-encoded screenshots for failed tests
      });
    },
  },
  viewportWidth: 1280,
  viewportHeight: 800,
});
