var width = 1060;
var height = 768;

var casper = require('casper').create({
  viewportSize: {
    width: width,
    height: height
  },
  verbose: true,
  logLevel: "debug"
});

var options = casper.cli.options;
var isDebug = !!options['d'];

var rootUrl = isDebug ? 'http://localhost:5000/' : 'https://quay.io/';
var repo = isDebug ? 'complex' : 'r0';
var org = isDebug ? 'buynlarge' : 'devtable'
var orgrepo = isDebug ? 'buynlarge/orgrepo' : 'quay/testconnect2';
var buildrepo = isDebug ? 'devtable/building' : 'quay/testconnect2';

var outputDir = "screenshots/";

casper.on("remote.message", function(msg, trace) {
  this.echo("Message: " + msg, "DEBUG");
});

casper.on("page.error", function(msg, trace) {
  this.echo("Page error: " + msg, "ERROR");
  for (var i = 0; i < trace.length; i++) {
    this.echo(JSON.stringify(trace[i]), "ERROR");
  }
});

casper.start(rootUrl + 'signin', function () {
  this.wait(1000);
});

casper.thenClick('.accordion-toggle[data-target="#collapseSignin"]', function() {
  this.wait(1000);
});

casper.then(function () {
  this.fill('.form-signin', {
    'username': isDebug ? 'devtable' : 'quaydemo',
    'password': isDebug ? 'password': 'C>K98%y"_=54x"<',
  }, false);
});

casper.thenClick('.form-signin button[type=submit]', function() {
  this.waitForText('Repositories');
});

casper.then(function() {
  this.waitForSelector('.repo-list');
  this.log('Generating repositories screenshot.');
});

casper.then(function() {
  this.capture(outputDir + 'user-home.png');
});

casper.then(function() {
  this.log('Generating repository view screenshot.');
});

casper.thenOpen(rootUrl + 'repository/devtable/' + repo + '?tag=v2.0', function() {
  this.wait(1000);
});

casper.then(function() {
  this.capture(outputDir + 'repo-view.png');
});

casper.then(function() {
  this.log('Generating repository tags screenshot.');
});

casper.thenOpen(rootUrl + 'repository/devtable/' + repo + '?tab=tags&tag=v2.0', function() {
  this.wait(1000);
});

casper.then(function() {
  this.capture(outputDir + 'repo-tags.png');
});

casper.then(function() {
  this.log('Generating repository tree screenshot.');
});

casper.thenOpen(rootUrl + 'repository/devtable/' + repo + '?tab=changes&tag=v2.0,prod,staging', function() {
  this.wait(5000);
});

casper.then(function() {
  this.capture(outputDir + 'repo-tree.png');
});

casper.then(function() {
  this.log('Generating repository settings screenshot.');
});

casper.thenOpen(rootUrl + 'repository/devtable/' + repo + '?tab=settings', function() {
  this.wait(1000);
});

casper.then(function() {
  this.capture(outputDir + 'repo-settings.png');
});

casper.thenOpen(rootUrl + 'repository/devtable/' + repo + '?tab=tags', function() {
  this.wait(1000);
});

casper.then(function() {
  this.log('Generating organization view screenshot.');
});

casper.thenOpen(rootUrl + 'organization/' + org, function() {
  this.waitForSelector('.organization-name');
});

casper.then(function() {
  this.capture(outputDir + 'org-view.png');
});

casper.then(function() {
  this.log('Generating organization teams screenshot.');
});

casper.thenOpen(rootUrl + 'organization/' + org + '?tab=teams', function() {
  this.waitForText('Owners');
});

casper.then(function() {
  this.capture(outputDir + 'org-teams.png');
});

casper.then(function() {
  this.log('Generating organization settings screenshot.');
});

casper.thenOpen(rootUrl + 'organization/' + org + '?tab=usage', function() {
  this.wait(1000)
});

casper.then(function() {
  this.capture(outputDir + 'org-settings.png');
});

casper.then(function() {
  this.log('Generating organization logs screenshot.');
});

casper.thenClick('a[data-target="#logs"]', function() {
  this.waitForSelector('svg > g', function() {
    this.wait(1000, function() {
      this.capture(outputDir + 'org-logs.png', {
        top: 0,
        left: 0,
        width: width,
        height: height + 200
      });
    });
  });
});

casper.then(function() {
  this.log('Generating build history screenshot.');
});

casper.thenOpen(rootUrl + 'repository/' + buildrepo + '?tab=builds', function() {
  this.wait(10000);
  this.waitForText('Triggered By');
});

casper.then(function() {
  this.capture(outputDir + 'build-history.png');
});

casper.run();
