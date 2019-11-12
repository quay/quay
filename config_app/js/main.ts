// imports shims, etc
import 'core-js';

import * as angular from 'angular';
import { ConfigAppModule } from './config-app.module';
import { bundle } from 'ng-metadata/core';

// load all app dependencies
require('../static/lib/angular-file-upload.min.js');
require('../../static/js/tar');

const ng1QuayModule: string = bundle(ConfigAppModule, []).name;
angular.module('quay-config', [ng1QuayModule])
    .run(() => {
    });

declare var require: any;
function requireAll(r) {
    r.keys().forEach(r);
}

// load all services
requireAll(require.context('./services', true, /\.js$/));


// load all the components after services
requireAll(require.context('./setup', true, /\.js$/));
requireAll(require.context('./core-config-setup', true, /\.js$/));
requireAll(require.context('./components', true, /\.js$/));

// load config-app specific css
requireAll(require.context('../static/css', true, /\.css$/));


// Load all the main quay css
requireAll(require.context('../../static/css', true, /\.css$/));
requireAll(require.context('../../static/lib', true, /\.css$/));
