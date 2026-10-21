const {DefinePlugin} = require('webpack');
const {merge} = require('webpack-merge');
const {readFileSync} = require('fs');
const {createHostedQuay} = require('./hosted-quay.js');

// Set this before loading the common configuration so sample invoices aren't copied.
process.env.MOCK_API = 'false';
const common = require('./webpack.common.js');
const port = Number(process.env.PORT || 9010);
if (!Number.isInteger(port) || port < 1 || port > 65535) {
  throw new Error('PORT must be an integer between 1 and 65535.');
}
const hosted = createHostedQuay({
  token: process.env.QUAY_OAUTH_TOKEN,
  port,
  allowBillingWrites: process.env.QUAY_BILLING_WRITES === 'true',
});
const cert = process.env.QUAY_DEV_TLS_CERT;
const key = process.env.QUAY_DEV_TLS_KEY;
if (!!cert !== !!key) {
  throw new Error('Configure both QUAY_DEV_TLS_CERT and QUAY_DEV_TLS_KEY.');
}

module.exports = merge(common('development'), {
  mode: 'development',
  devtool: 'inline-source-map',
  devServer: {
    host: '127.0.0.1',
    port,
    allowedHosts: ['localhost', '127.0.0.1'],
    server: {
      type: 'https',
      ...(cert
        ? {options: {cert: readFileSync(cert), key: readFileSync(key)}}
        : {}),
    },
    compress: true,
    open: false,
    historyApiFallback: {disableDotRule: true},
    proxy: [hosted.proxy],
    setupMiddlewares(middlewares) {
      middlewares.unshift({
        name: 'hosted-quay-access',
        middleware: hosted.guard,
      });
      return middlewares;
    },
  },
  module: {rules: [{test: /\.css$/, use: ['style-loader', 'css-loader']}]},
  plugins: [
    new DefinePlugin({
      'process.env.MOCK_API': JSON.stringify('false'),
      'process.env.QUAY_HOSTED': JSON.stringify('true'),
      'process.env.REACT_QUAY_APP_API_URL': JSON.stringify(''),
      'process.env.REACT_APP_QUAY_DOMAIN': JSON.stringify(`localhost:${port}`),
    }),
  ],
});
