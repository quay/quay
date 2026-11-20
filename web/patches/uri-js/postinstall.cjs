const {apply} = require('./patch.cjs');

if (
  process.env.npm_config_package_lock_only === 'true' ||
  process.env.npm_config_dry_run === 'true'
) {
  console.log(
    'uri-js: metadata-only npm operation; no installed files changed',
  );
} else {
  apply(process.cwd());
  require('./test.cjs');
}
