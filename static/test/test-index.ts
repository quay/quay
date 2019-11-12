declare var require: NodeRequire;

// Require all modules ending in ".spec.ts" from the js directory and all subdirectories
var testsContext = (<any>require).context("../js", true, /\.spec\.ts$/);
testsContext.keys().forEach(testsContext);
