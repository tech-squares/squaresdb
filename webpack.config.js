// Based on
// https://www.saaspegasus.com/guides/modern-javascript-for-django-developers/integrating-javascript-pipeline/
// https://dev.to/rinconcamilo/setting-up-react-babel-webpack-typescript-without-create-react-app-a9l
const path = require('path');

module.exports = {
  entry: './react/index.tsx',  // path to our input file
  output: {
    filename: 'index-bundle.js',  // output bundle file name
    path: path.resolve(__dirname, './static/webpack'),  // path to our Django static directory
  },
  module: {
    rules: [
      {
        test: /\.(js|jsx)$/,
        exclude: /node_modules/,
        loader: "babel-loader",
        options: { presets: ["@babel/preset-env", "@babel/preset-react"] }
      },
      {
        test: /\.(ts|tsx)$/,
        exclude: /node_modules/,
        loader: "babel-loader",
        options: { presets: ["@babel/preset-env", "@babel/preset-react", "@babel/preset-typescript"] }
      },
    ]
  },
};
