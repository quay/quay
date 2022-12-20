const Dotenv = require('dotenv-webpack');
const {merge} = require('webpack-merge');
const MiniCssExtractPlugin = require('mini-css-extract-plugin');
const CssMinimizerPlugin = require('css-minimizer-webpack-plugin');
const TerserJSPlugin = require('terser-webpack-plugin');
const common = require('./webpack.common.js');

module.exports = merge(common('production'), {
  mode: 'production',
  devtool: 'source-map',
  optimization: {
    minimize: true,
    minimizer: [
      new TerserJSPlugin({
        terserOptions: {
          compress: {
            pure_funcs: ['console.log', 'console.debug'],
          },
        },
      }),
      new CssMinimizerPlugin({
        minimizerOptions: {
          preset: ['default', {mergeLonghand: false}],
        },
      }),
    ],
    splitChunks: {
      // groups styles from node_modules (like PatternFly) into vendor.css
      // all other styles under src will be grouped into main.css
      chunks: 'all',
      cacheGroups: {
        vendor: {
          test: /node_modules/,
          name: 'vendor',
          chunks: 'initial',
          enforce: true,
        },
      },
    },
  },
  plugins: [
    new Dotenv({
      systemvars: true,
      silent: true,
    }),
    new MiniCssExtractPlugin({
      filename: '[name].css',
    }),
  ],
  module: {
    rules: [
      {
        test: /\.css$/,
        use: [MiniCssExtractPlugin.loader, 'css-loader'],
        sideEffects: true,
      },
    ],
  },
});
