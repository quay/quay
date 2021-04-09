const webpack = require('webpack');
const path = require('path');
const TerserPlugin = require('terser-webpack-plugin');

let config = {
  entry: {
    configapp: "./js/main.ts"
  },
  output: {
    path: path.resolve(__dirname, "static/build"),
    filename: '[name]-quay-frontend.bundle.js',
    chunkFilename: '[name]-quay-frontend.chunk.js'
  },
  resolve: {
    extensions: [".ts", ".js"],
    modules: [
      // Allows us to use the top-level node modules
      path.resolve(__dirname, '../node_modules'),
      path.resolve(__dirname, '../static/css/')
    ]
  },
  externals: {
    angular: "angular",
    jquery: "$",
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
      {
        test: /\.(woff(2)?|ttf|eot|svg)(\?v=\d+\.\d+\.\d+)?$/,
        use: [
          {
            loader: 'file-loader',
            options: {
              // TODO: Workaround for incompatible file-loader + html-loader versions
              // https://github.com/webpack-contrib/html-loader/issues/203
              esModule: false
            }
          }
        ]
      }
    ]
  },
  optimization: {},
  plugins: [
    // Replace references to global variables with associated modules
    new webpack.ProvidePlugin({
      FileSaver: 'file-saver',
      angular: "angular",
      $: "jquery",
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
  config.output.filename = '[name]-quay-frontend-[hash].bundle.js';
}

module.exports = config;
