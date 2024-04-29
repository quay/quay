const path = require("path");
const HtmlWebpackPlugin = require("html-webpack-plugin");
const CopyPlugin = require("copy-webpack-plugin");
const TsconfigPathsPlugin = require("tsconfig-paths-webpack-plugin");
const BG_IMAGES_DIRNAME = "assets";
const ASSET_PATH = process.env.ASSET_PATH || "/";
module.exports = (env) => {
  return {
    entry: "./web/src/index.tsx",
    module: {
      rules: [
        {
          test: /\.(tsx|ts|jsx)?$/,
          use: [
            {
              loader: "ts-loader",
              options: {
                transpileOnly: true,
                experimentalWatchApi: true,
              },
            },
          ],
        },
        {
          test: /\.(svg|ttf|eot|woff|woff2)$/,
          // only process modules with this loader
          // if they live under a 'fonts' or 'pficon' directory
          include: [
            path.resolve(__dirname, "node_modules/patternfly/dist/fonts"),
            path.resolve(
              __dirname,
              "node_modules/@patternfly/react-core/dist/styles/assets/fonts",
            ),
            path.resolve(
              __dirname,
              "node_modules/@patternfly/react-core/dist/styles/assets/pficon",
            ),
            path.resolve(
              __dirname,
              "node_modules/@patternfly/patternfly/assets/fonts",
            ),
            path.resolve(
              __dirname,
              "node_modules/@patternfly/patternfly/assets/pficon",
            ),
          ],
          generator: {
            filename: "assets/[name].[ext]",
          },
        },
        {
          test: /\.svg$/,
          include: (input) => input.indexOf("background-filter.svg") > 1,
          use: [
            {
              loader: "url-loader",
              options: {
                limit: 5000,
                outputPath: "svgs",
                name: "[name].[ext]",
              },
            },
          ],
        },
        {
          test: /\.svg$/,
          // only process SVG modules with this loader if they live under a 'bgimages' directory
          // this is primarily useful when applying a CSS background using an SVG
          include: (input) => input.indexOf(BG_IMAGES_DIRNAME) > -1,
          use: {
            loader: "svg-url-loader",
            options: {},
          },
        },
        {
          test: /\.svg$/i,
          // only process SVG modules with this loader when they don't live under a 'bgimages',
          // 'fonts', or 'pficon' directory, those are handled with other loaders
          include: (input) =>
            input.indexOf(BG_IMAGES_DIRNAME) === -1 &&
            input.indexOf("fonts") === -1 &&
            input.indexOf("background-filter") === -1 &&
            input.indexOf("pficon") === -1,
          use: {
            loader: "file-loader",
            options: {},
          },
        },
        {
          test: /\.(jpg|jpeg|png|gif)$/i,
          include: [
            path.resolve(__dirname, "node_modules/patternfly"),
            path.resolve(
              __dirname,
              "node_modules/@patternfly/patternfly/assets/images",
            ),
            path.resolve(
              __dirname,
              "node_modules/@patternfly/react-styles/css/assets/images",
            ),
            path.resolve(
              __dirname,
              "node_modules/@patternfly/react-core/dist/styles/assets/images",
            ),
            path.resolve(
              __dirname,
              "node_modules/@patternfly/react-core/node_modules/@patternfly/react-styles/css/assets/images",
            ),
            path.resolve(
              __dirname,
              "node_modules/@patternfly/react-table/node_modules/@patternfly/react-styles/css/assets/images",
            ),
            path.resolve(
              __dirname,
              "node_modules/@patternfly/react-inline-edit-extension/node_modules/@patternfly/react-styles/css/assets/images",
            ),
          ],
          use: [
            {
              loader: "url-loader",
              options: {
                limit: 5000,
                outputPath: "images",
                name: "[name].[ext]",
              },
            },
          ],
        },
        {
          test: /\.s[ac]ss$/i,
          use: [
            // Creates `style` nodes from JS strings
            "style-loader",
            // Translates CSS into CommonJS
            "css-loader",
            // Compiles Sass to CSS
            "sass-loader",
          ],
        },
      ],
    },
    output: {
      filename: "[name].bundle.js",
      path: path.resolve(__dirname, "dist"),
      publicPath: ASSET_PATH,
    },
    plugins: [
      new HtmlWebpackPlugin({
        template: path.resolve(__dirname, "web", "src", "index.html"),
      }),
      new CopyPlugin({
        patterns: [{ from: "./web/src/assets/favicon.png", to: "images" }],
      }),
    ],
    resolve: {
      alias: { src: "/web/src" },
      extensions: [".js", ".ts", ".tsx", ".jsx"],
      plugins: [
        new TsconfigPathsPlugin({
          configFile: path.resolve(__dirname, "./tsconfig.json"),
        }),
      ],
      symlinks: false,
      cacheWithContext: false,
    },
  };
};
