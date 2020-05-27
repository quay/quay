const webpack = require('webpack');
const path = require('path');
const TerserPlugin = require('terser-webpack-plugin');


let config = {
  entry: "./static/js/main.ts",
  output: {
    path: path.resolve(__dirname, "static/build"),
    publicPath: "/static/build/",
    filename: '[name]-quay-frontend.bundle.js',
    chunkFilename: '[name]-quay-frontend.chunk.js'
  },
  resolve: {
    extensions: [".ts", ".js"],
  },
  // Use global variables to maintain compatibility with non-Webpack components
  externals: {
    angular: "angular",
    jquery: "$",
    moment: "moment",
    "raven-js": "Raven",
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
      FileSaver: 'file-saver',
      angular: "angular",
      $: "jquery",
      moment: "moment",
    }),
    // Restrict the extra locales that moment.js can load; en is always included
    new webpack.ContextReplacementPlugin(/moment[\/\\]locale$/, /en/),
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
      terserOptions: {mangle: false, keep_classnames: true, keep_fnames: true},
      sourceMap: true,
    }),
  ];
  config.output.filename = '[name]-quay-frontend-[hash].bundle.js';
}

module.exports = config;
