const fs = require('fs');
const path = require('path');

const indexPath = path.resolve(__dirname, 'dist/index.html');
const targetFilePath = path.resolve(__dirname, 'dist/200.html');
// ensure we have bookmarkable url's when publishing to surge
// https://surge.sh/help/adding-a-200-page-for-client-side-routing
fs.createReadStream(indexPath).pipe(fs.createWriteStream(targetFilePath));
