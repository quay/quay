const Dotenv = require('dotenv-webpack');
const {merge} = require('webpack-merge');
const common = require('./webpack.common.js');
const HOST = process.env.HOST || '0.0.0.0';
const PORT = process.env.PORT || '9000';
const QUAY_PROXY_TARGET =
  process.env.QUAY_PROXY_TARGET || 'http://localhost:8080';

module.exports = merge(common('development'), {
  mode: 'development',
  devtool: 'inline-source-map',
  devServer: {
    host: HOST,
    port: PORT,
    compress: true,
    historyApiFallback: {
      disableDotRule: true,
    },
    open: true,
    proxy: {
      '/api/v1': {
        target: QUAY_PROXY_TARGET,
        logLevel: 'debug',
      },
      '/csrf_token': {
        target: QUAY_PROXY_TARGET,
        logLevel: 'debug',
      },
      '/config': {
        target: QUAY_PROXY_TARGET,
        logLevel: 'debug',
      },
      '/static': {
        target: QUAY_PROXY_TARGET,
        logLevel: 'debug',
      },
      '/oauth': {
        target: QUAY_PROXY_TARGET,
        logLevel: 'debug',
      },
    },
  },
  module: {
    rules: [
      {
        test: /\.css$/,
        use: ['style-loader', 'css-loader'],
      },
    ],
  },
  plugins: [
    new Dotenv({
      systemvars: true,
      silent: true,
      path: './.env.development',
    }),
  ],
});
