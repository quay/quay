import 'core-js';
import { bundle } from 'ng-metadata/core';
import { QuayModule } from './quay.module';
import { provideRun } from './quay-run';
import * as angular from 'angular';


// Load all JS/CSS files into bundle: http://stackoverflow.com/a/30652110
declare var require: any;
function requireAll(r) {
  r.keys().forEach(r);
}
// Use Webpack script-loader to eval in global scope: https://webpack.js.org/loaders/script-loader/
requireAll(require.context('script-loader!../lib', true, /\.js$/));
requireAll(require.context('../lib', true, /\.css$/));


/**
 * Register ng-metadata module as a traditional AngularJS module on the global namespace for non-TypeScript components.
 * TODO: Needed for non-TypeScript components/services to register themselves. Remove once they are migrated.
 * See https://hotell.gitbooks.io/ng-metadata/content/docs/recipes/bootstrap.html
 */
const ng1QuayModule: string = bundle(QuayModule, []).name;
angular.module('quay', [ng1QuayModule])
  .run(provideRun);


// Load JS/CSS/HTML dependent on above AngularJS module
requireAll(require.context('.', true, /\.js$/));
requireAll(require.context('../css', true, /\.css$/));
requireAll(require.context('../partials', true, /\.html/));
requireAll(require.context('../directives', true, /\.html/));
requireAll(require.context('.', true, /\.html/));
