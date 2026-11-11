const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');
const os = require('node:os');
const {spawnSync} = require('node:child_process');
const {test} = require('node:test');
const {apply, digest, files, installedCopies} = require('./patch.cjs');
const manifest = require('./hashes.json');

const directory = path.resolve(process.argv[2] || process.cwd());
const copies = installedCopies(directory);
assert.ok(copies.length, `No uri-js copies found in ${directory}`);

test('patch is idempotent and every installed distribution has the reviewed patched hash', () => {
  for (const copy of copies) {
    for (const file of files) {
      assert.equal(
        digest(fs.readFileSync(path.join(copy.directory, file))),
        manifest[copy.version][file].patched,
      );
    }
  }
  apply(directory);
});

test('patch rejects unknown content and versions and deduplicates linked copies', () => {
  const temporary = fs.mkdtempSync(path.join(os.tmpdir(), 'quay-uri-js-'));
  try {
    const target = path.join(temporary, 'node_modules', 'uri-js');
    for (const file of files) {
      const destination = path.join(target, file);
      fs.mkdirSync(path.dirname(destination), {recursive: true});
      fs.copyFileSync(path.join(copies[0].directory, file), destination);
    }
    const metadata = path.join(target, 'package.json');
    fs.writeFileSync(
      metadata,
      JSON.stringify({name: 'uri-js', version: copies[0].version}),
    );
    const nested = path.join(
      temporary,
      'node_modules',
      'nested',
      'node_modules',
    );
    fs.mkdirSync(nested, {recursive: true});
    fs.symlinkSync(target, path.join(nested, 'uri-js'), 'dir');
    assert.equal(installedCopies(temporary).length, 1);
    apply(temporary);
    fs.appendFileSync(path.join(target, files[0]), '\n');
    assert.throws(() => apply(temporary), /Unreviewed uri-js content/);
    fs.writeFileSync(
      metadata,
      JSON.stringify({name: 'uri-js', version: '0.0.0'}),
    );
    assert.throws(() => apply(temporary), /Unreviewed uri-js version/);
  } finally {
    fs.rmSync(temporary, {recursive: true, force: true});
  }
});

for (const copy of copies) {
  for (const file of files) {
    test(`${copy.directory}/${file}: separators and RFC dot-segment controls terminate correctly`, () => {
      const filename = path.join(copy.directory, file);
      const source = `
        const assert = require('node:assert/strict');
        const fs = require('node:fs');
        const vm = require('node:vm');
        const filename = ${JSON.stringify(filename)};
        const esm = filename.includes('/esnext/');
        const uri = esm
          ? {removeDotSegments: vm.runInNewContext('(' + fs.readFileSync(filename, 'utf8').match(/function removeDotSegments\\(input\\) \\{[\\s\\S]*?\\n\\}/)[0] + ')')}
          : require(filename);
        for (const separator of ['\\u2028', '\\u2029']) {
          assert.equal(uri.removeDotSegments('/' + separator + 'foo'), '/' + separator + 'foo');
          assert.equal(uri.removeDotSegments('/a/../' + separator + 'foo/./bar'), '/' + separator + 'foo/bar');
          if (!esm) {
            assert.equal(uri.serialize({path: '/' + separator + 'foo'}, {iri: true}), '/' + separator + 'foo');
            assert.equal(uri.resolve('https://example.com/', '/' + separator + 'foo', {iri: true, unicodeSupport: true}), 'https://example.com/' + separator + 'foo');
          }
        }
        for (const [input, expected] of [['/a/b/../c/./d', '/a/c/d'], ['../x', 'x'], ['a/../b', '/b'], ['.', ''], ['..', ''], ['/a/b/..', '/a/'], ['/a\\nb/./c', '/a\\nb/c']]) {
          assert.equal(uri.removeDotSegments(input), expected);
        }
        if (!esm) assert.equal(uri.resolve('http://a/b/c/d;p?q', '../../g'), 'http://a/g');
      `;
      const result = spawnSync(
        process.execPath,
        ['--max-old-space-size=128', '-e', source],
        {timeout: 2000, encoding: 'utf8'},
      );
      assert.ifError(result.error);
      assert.equal(result.status, 0, result.stderr);
    });
  }
}
