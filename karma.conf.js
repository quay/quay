var webpackConfig = require('./webpack.config');


module.exports = function(config) {
  config.set({
    basePath: '',
    frameworks: ['jasmine'],
    files: [
      // CDN resources
      'node_modules/jquery/dist/jquery.js',
      'node_modules/angular/angular.js',
      'node_modules/angular-animate/angular-animate.js',
      'node_modules/angular-cookies/angular-cookies.js',
      'node_modules/angular-mocks/angular-mocks.js',
      'node_modules/angular-route/angular-route.js',
      'node_modules/angular-sanitize/angular-sanitize.js',
      'node_modules/moment/moment.js',
      'node_modules/bootstrap-datepicker/dist/js/bootstrap-datepicker.js',
      'node_modules/eonasdan-bootstrap-datetimepicker/src/js/bootstrap-datetimepicker.js',
      'node_modules/bootbox/bootbox.js',
      'node_modules/underscore/underscore.js',
      'node_modules/restangular/dist/restangular.js',
      'node_modules/d3/d3.js',
      'node_modules/raven-js/dist/raven.js',
      'node_modules/cal-heatmap/cal-heatmap.js',

      // Polyfills
      'node_modules/core-js/index.js',

      // static/lib resources
      'static/lib/**/*.js',

      // Single entrypoint for all tests
      'static/test/test-index.ts',

      // Tests utils
      'static/test/**/*.js',
    ],
    exclude: [],
    preprocessors: {
      'static/lib/angular-moment.min.js': ['webpack'],
      'node_modules/core-js/index.js': ['webpack'],
      'static/test/test-index.ts': ['webpack'],
    },
    webpack: webpackConfig,
    webpackMiddleware: {
      stats: 'errors-only'
    },
    reporters: ['dots', 'coverage'],
    coverageReporter: {
      dir: 'coverage',
      type: 'html'
    },
    client: {
      captureConsole: true
    },
    port: 9876,
    colors: true,
    logLevel: config.LOG_INFO,
    autoWatch: true,
    browsers: ['ChromeNoSandbox'],
    customLaunchers: {
      ChromeNoSandbox: {
        base: 'ChromeHeadless',
        flags: ['--no-sandbox']
      }
    },
    singleRun: false,
    concurrency: Infinity,
    mime: {
      'text/x-typescript': ['ts','tsx']
    }
  });
};
