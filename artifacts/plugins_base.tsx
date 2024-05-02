import * as npmPlugin from "./plugins/npm/ui";
export function InitPlugins() {
  // Load all plugins
  npmPlugin.init();
}
