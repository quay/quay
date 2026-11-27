const assert = require('node:assert/strict');
const crypto = require('node:crypto');
const fs = require('node:fs');
const path = require('node:path');

const files = [
  'dist/es5/uri.all.js',
  'dist/es5/uri.all.min.js',
  'dist/esnext/uri.js',
];

function removeDotSegments(input) {
  const output = [];
  while (input.length) {
    const before = input.length;
    if (input.match(/^\.\.?\//)) {
      input = input.replace(/^\.\.?\//, '');
    } else if (input.match(/^\/\.(\/|$)/)) {
      input = input.replace(/^\/\.(\/|$)/, '/');
    } else if (input.match(/^\/\.\.(\/|$)/)) {
      input = input.replace(/^\/\.\.(\/|$)/, '/');
      output.pop();
    } else if (input === '.' || input === '..') {
      input = '';
    } else {
      const match = input.match(/^\/?[\s\S]*?(?=\/|$)/);
      if (!match || !match[0].length) {
        throw new Error('Unexpected dot segment condition');
      }
      input = input.slice(match[0].length);
      output.push(match[0]);
    }
    if (input.length >= before) {
      throw new Error('Unexpected dot segment condition');
    }
  }
  return output.join('');
}

function digest(source) {
  return crypto.createHash('sha256').update(source).digest('hex');
}

function patchSource(source, file) {
  const expression = file.endsWith('.min.js')
    ? /function y\(e\)\{for\(var r=\[\];e.length;\).*?return r.join\(""\)\}/g
    : /function removeDotSegments\(input\) \{[\s\S]*?\n\}/g;
  assert.equal(
    [...source.matchAll(expression)].length,
    1,
    `Unexpected function in ${file}`,
  );
  const replacement = removeDotSegments
    .toString()
    .replaceAll('\r\n', '\n')
    .replaceAll('const ', 'var ');
  return source
    .replace(expression, () =>
      file.endsWith('.min.js')
        ? replacement.replace('removeDotSegments', 'y')
        : replacement,
    )
    .replaceAll('/^\\/?(?:.|\\n)*?(?=\\/|$)/', '/^\\/?[\\s\\S]*?(?=\\/|$)/')
    .replace(/^\/\/[#@] sourceMappingURL=.*$/gm, '');
}

function installedCopies(directory) {
  const seen = new Set();
  const copies = [];
  function visit(current) {
    const real = fs.realpathSync(current);
    if (seen.has(real)) return;
    seen.add(real);
    if (
      path.basename(current) === 'uri-js' &&
      fs.existsSync(path.join(real, 'package.json'))
    ) {
      const metadata = JSON.parse(
        fs.readFileSync(path.join(real, 'package.json'), 'utf8'),
      );
      assert.equal(metadata.name, 'uri-js');
      copies.push({directory: real, version: metadata.version});
    }
    for (const entry of fs.readdirSync(real, {withFileTypes: true})) {
      if (entry.name === '.bin') continue;
      const child = path.join(real, entry.name);
      if (
        entry.isDirectory() ||
        (entry.isSymbolicLink() && fs.statSync(child).isDirectory())
      )
        visit(child);
    }
  }
  visit(path.join(directory, 'node_modules'));
  return copies;
}

function apply(directory) {
  const manifest = require('./hashes.json');
  const copies = installedCopies(directory);
  for (const copy of copies) {
    assert.ok(
      manifest[copy.version],
      `Unreviewed uri-js version: ${copy.version}`,
    );
    for (const file of files) {
      const filename = path.join(copy.directory, file);
      const source = fs.readFileSync(filename, 'utf8');
      const expected = manifest[copy.version][file];
      if (digest(source) === expected.patched) continue;
      assert.equal(
        digest(source),
        expected.original,
        `Unreviewed uri-js content: ${filename}`,
      );
      const patched = patchSource(source, file);
      assert.equal(digest(patched), expected.patched);
      fs.writeFileSync(`${filename}.quay-patched`, patched);
      fs.renameSync(`${filename}.quay-patched`, filename);
    }
  }
  console.log(
    `CVE-2026-93690: verified local patch on ${copies.length} uri-js installation(s)`,
  );
}

module.exports = {apply, digest, files, installedCopies, patchSource};
if (require.main === module) apply(process.cwd());
