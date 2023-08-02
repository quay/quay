const webpack = require('webpack');
const path = require('path');
const TerserPlugin = require('terser-webpack-plugin');

let config = {
  entry: {
    configapp: "./js/main.ts"
  },
  output: {
    path: path.resolve(__dirname, "static/build"),
    filename: '[name]-quay-editor.bundle.js',
    chunkFilename: '[name]-quay-editor.chunk.js'
  },
  resolve: {
    extensions: [".ts", ".js"],
    modules: [
      "node_modules"
    ]
  },
  module: {
    rules: [
      {
        test: /\.ts$/,
        use: ["ts-loader"],
        exclude: /node_modules/
      },
      {
        test: /\.css$/,
        use: [
          "style-loader",
          "css-loader?minimize=true",
        ],
      },
      {
        test: /\.html$/,
        use: [
          'ngtemplate-loader?relativeTo=' + (path.resolve(__dirname)),
          'html-loader',
        ]
      },
    ]
  },
  optimization: {},
  plugins: [
    // Replace references to global variables with associated modules
    new webpack.ProvidePlugin({
      $: "jquery",
      jQuery: "jquery"
    }),
  ],
  devtool: "cheap-module-source-map",
};

/**
 * Production settings
 */
if (process.env.NODE_ENV === 'production') {
  config.optimization.minimizer = [
    new TerserPlugin({
      // Disable mangle to prevent AngularJS errors
      terserOptions: {mangle: false},
      sourceMap: true,
    }),
  ];
  config.output.filename = '[name]-quay-editor.bundle.js';
}

module.exports = config;
