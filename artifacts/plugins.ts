import * as path from "node:path";
import * as fs from "fs";

function InitPlugins() {
  // Load all plugins
  const plugins = fs.readdirSync(path.join(__dirname, "plugins"));
  plugins.forEach((plugin) => {
    require(path.join(__dirname, "plugins", plugin));
  });
}
