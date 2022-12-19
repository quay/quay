const Dotenv = require('dotenv-webpack');
const {merge} = require('webpack-merge');
const common = require('./webpack.common.js');
const HOST = process.env.HOST || 'localhost';
const PORT = process.env.PORT || '9000';

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
