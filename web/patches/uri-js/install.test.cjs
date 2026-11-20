const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');
const {spawnSync} = require('node:child_process');
const {test} = require('node:test');
const {digest, files, installedCopies} = require('./patch.cjs');
const manifest = require('./hashes.json');

function npm(directory, args) {
  const env = {...process.env};
  delete env.npm_config_package_lock_only;
  delete env.npm_config_dry_run;
  const result = spawnSync(
    process.platform === 'win32' ? 'npm.cmd' : 'npm',
    [...args, '--offline', '--no-audit', '--no-fund'],
    {cwd: directory, env, timeout: 30000, encoding: 'utf8'},
  );
  assert.ifError(result.error);
  return result;
}

for (const location of ['web/patches/uri-js', 'patches/uri-js']) {
  test(`${location}: npm metadata-only operations skip, real installs enforce`, () => {
    const temporary = fs.mkdtempSync(path.join(os.tmpdir(), 'uri-npm-'));
    try {
      fs.cpSync(__dirname, path.join(temporary, location), {recursive: true});
      fs.writeFileSync(
        path.join(temporary, 'package.json'),
        JSON.stringify({
          name: 'uri-install-regression',
          version: '1.0.0',
          private: true,
          scripts: {postinstall: `node ${location}/postinstall.cjs`},
        }),
      );
      for (const flag of ['--package-lock-only', '--dry-run']) {
        const result = npm(temporary, ['install', flag]);
        assert.equal(result.status, 0, result.stdout + result.stderr);
        assert.match(result.stdout, /metadata-only npm operation/);
        assert.equal(
          fs.existsSync(path.join(temporary, 'node_modules')),
          false,
        );
      }
      for (const args of [['install'], ['run', 'postinstall']]) {
        const result = npm(temporary, args);
        assert.notEqual(result.status, 0, result.stdout + result.stderr);
        assert.doesNotMatch(result.stdout, /metadata-only npm operation/);
      }
      const copy = installedCopies(process.cwd())[0];
      const target = path.join(temporary, 'node_modules/uri-js');
      fs.cpSync(copy.directory, target, {recursive: true});
      const valid = npm(temporary, ['run', 'postinstall']);
      assert.equal(valid.status, 0, valid.stdout + valid.stderr);
      assert.match(valid.stdout, /# pass 5/);
      fs.appendFileSync(path.join(target, files[0]), '\n');
      const tamperedSource = fs.readFileSync(path.join(target, files[0]));
      const tampered = npm(temporary, ['run', 'postinstall']);
      assert.notEqual(tampered.status, 0);
      assert.match(tampered.stderr, /Unreviewed uri-js content/);
      for (const flag of ['--package-lock-only', '--dry-run']) {
        const result = npm(temporary, ['install', flag]);
        assert.equal(result.status, 0, result.stdout + result.stderr);
        assert.match(result.stdout, /metadata-only npm operation/);
        assert.deepEqual(
          fs.readFileSync(path.join(target, files[0])),
          tamperedSource,
        );
      }
    } finally {
      fs.rmSync(temporary, {recursive: true, force: true});
    }
  });
}

test('CRLF checkout keeps approved LF replacement hashes unchanged', () => {
  const temporary = fs.mkdtempSync(path.join(os.tmpdir(), 'uri-crlf-'));
  try {
    fs.cpSync(__dirname, temporary, {recursive: true});
    for (const filename of fs.readdirSync(temporary)) {
      if (!filename.endsWith('.cjs')) continue;
      const destination = path.join(temporary, filename);
      fs.writeFileSync(
        destination,
        fs.readFileSync(destination, 'utf8').replace(/\r?\n/g, '\r\n'),
      );
    }
    const crlf = require(path.join(temporary, 'patch.cjs'));
    for (const copy of installedCopies(process.cwd())) {
      for (const file of files.filter(
        (filename) => !filename.endsWith('.min.js'),
      )) {
        const source = fs.readFileSync(path.join(copy.directory, file), 'utf8');
        assert.equal(
          digest(crlf.patchSource(source, file)),
          manifest[copy.version][file].patched,
        );
      }
    }
  } finally {
    fs.rmSync(temporary, {recursive: true, force: true});
  }
});
