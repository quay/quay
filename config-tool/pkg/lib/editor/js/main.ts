// imports shims, etc
import "core-js";
import * as $ from 'jquery';
import * as angular from "angular";
import { ConfigAppModule } from "./config-app.module";
import { bundle } from "ng-metadata/core";

import "bootstrap";

window.$ = $;
window.jQuery = jQuery;

const ng1QuayModule: string = bundle(ConfigAppModule, []).name;
angular.module("quay-config", [ng1QuayModule]).run(() => {});

declare var require: any;
function requireAll(r) {
  r.keys().forEach(r);
}

// load all services
requireAll(require.context("./services", true, /\.js$/));

// load all the components after services
requireAll(require.context("./core-config-setup", true, /\.js$/));
requireAll(require.context("./components", true, /\.js$/));

//requireAll(require.context('../static/css', true, /\.css$/));
