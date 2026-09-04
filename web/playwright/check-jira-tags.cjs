#!/usr/bin/env node
/**
 * check-jira-tags.cjs
 *
 * Verifies that every top-level (and nested) test.describe block in
 * Playwright spec files carries at least one Jira linkage tag matching
 * @PROJQUAY-#### or @QUAYIO-####.  A nested describe is considered
 * covered if any ancestor describe already carries a Jira tag.
 *
 * Usage
 * -----
 *   # Check only files changed vs master (default — "diff mode"):
 *   node playwright/check-jira-tags.cjs
 *
 *   # Check specific files:
 *   node playwright/check-jira-tags.cjs playwright/e2e/api/api-v2.spec.ts
 *
 *   # Check all spec files under playwright/e2e/:
 *   node playwright/check-jira-tags.cjs --all
 *
 * Exit codes
 * ----------
 *   0  All checked describe blocks carry a Jira tag.
 *   1  One or more describe blocks are missing a Jira tag.
 */

'use strict';

const fs = require('fs');
const path = require('path');
const {execSync} = require('child_process');

// TypeScript compiler API — already a devDependency via @playwright/test
const ts = require('typescript');

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

/** Matches @PROJQUAY-1234 or @QUAYIO-5678 */
const JIRA_TAG_RE = /^@(PROJQUAY|QUAYIO)-\d+$/;

const SPEC_FILE_RE = /\.spec\.tsx?$/;
const SPEC_EXTENSIONS = new Set(['.ts', '.tsx']);

// ---------------------------------------------------------------------------
// Path helpers
// ---------------------------------------------------------------------------

const webRoot = path.resolve(__dirname, '..');
const testRoot = path.join(webRoot, 'playwright', 'e2e');
const repoRoot = path.resolve(webRoot, '..');

// ---------------------------------------------------------------------------
// File discovery
// ---------------------------------------------------------------------------

function listAllSpecFiles(dir) {
  const files = [];
  for (const entry of fs.readdirSync(dir, {withFileTypes: true})) {
    const full = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      files.push(...listAllSpecFiles(full));
    } else if (
      entry.isFile() &&
      SPEC_FILE_RE.test(entry.name) &&
      SPEC_EXTENSIONS.has(path.extname(entry.name))
    ) {
      files.push(full);
    }
  }
  return files.sort();
}

function getChangedSpecFiles() {
  // Determine the merge-base branch (prefer origin/HEAD, fall back to master).
  let baseBranch = 'master';
  try {
    const ref = execSync(
      'git symbolic-ref refs/remotes/origin/HEAD --short 2>/dev/null',
      {encoding: 'utf8', cwd: repoRoot},
    ).trim();
    if (ref) baseBranch = ref;
  } catch {
    /* use default */
  }

  try {
    return execSync(
      `git diff --name-only --diff-filter=ACM ${baseBranch}...HEAD`,
      {encoding: 'utf8', cwd: repoRoot},
    )
      .trim()
      .split('\n')
      .filter(Boolean)
      .map((rel) => path.resolve(repoRoot, rel))
      .filter(
        (abs) =>
          abs.startsWith(testRoot) &&
          SPEC_FILE_RE.test(abs) &&
          SPEC_EXTENSIONS.has(path.extname(abs)) &&
          fs.existsSync(abs),
      );
  } catch {
    return [];
  }
}

// ---------------------------------------------------------------------------
// AST helpers
// ---------------------------------------------------------------------------

function expressionChain(expr) {
  if (ts.isIdentifier(expr)) return [expr.text];
  if (ts.isPropertyAccessExpression(expr)) {
    return [...expressionChain(expr.expression), expr.name.text];
  }
  return [];
}

/**
 * Returns true for `test.describe(...)` calls.
 * Excludes `test.describe.configure(...)`.
 */
function isDescribeCall(node) {
  if (!ts.isCallExpression(node)) return false;
  const chain = expressionChain(node.expression);
  return (
    chain.length >= 2 &&
    chain[0] === 'test' &&
    chain[1] === 'describe' &&
    chain[2] !== 'configure'
  );
}

/**
 * Extracts string tags from the optional details argument:
 *   test.describe('Name', { tag: '@foo' }, () => ...)
 *   test.describe('Name', { tag: ['@foo', '@bar'] }, () => ...)
 */
function tagsFromDetailsArg(callArgs) {
  // Details arg is at index 1 (between the title and the callback).
  if (callArgs.length < 2) return [];
  const detailsArg = callArgs[1];
  if (!ts.isObjectLiteralExpression(detailsArg)) return [];

  const tagProp = detailsArg.properties.find(
    (p) =>
      ts.isPropertyAssignment(p) &&
      p.name &&
      ts.isIdentifier(p.name) &&
      p.name.text === 'tag',
  );
  if (!tagProp || !ts.isPropertyAssignment(tagProp)) return [];

  const init = tagProp.initializer;
  if (ts.isStringLiteral(init)) return [init.text];
  if (ts.isArrayLiteralExpression(init)) {
    return init.elements.filter(ts.isStringLiteral).map((e) => e.text);
  }
  return [];
}

function lineNumber(sourceFile, node) {
  return (
    sourceFile.getLineAndCharacterOfPosition(node.getStart(sourceFile)).line + 1
  );
}

// ---------------------------------------------------------------------------
// Core analysis
// ---------------------------------------------------------------------------

/**
 * Walks the AST and collects describe blocks that lack a Jira tag
 * (neither the block itself nor any of its ancestor describes carries one).
 *
 * @param {string} filePath
 * @returns {Array<{relativePath: string, line: number, name: string}>}
 */
function collectFindings(filePath) {
  const source = fs.readFileSync(filePath, 'utf8');
  const sourceFile = ts.createSourceFile(
    filePath,
    source,
    ts.ScriptTarget.Latest,
    /* setParentNodes */ true,
  );
  const relativePath = path.relative(webRoot, filePath);
  const findings = [];

  function visitNode(node, ancestorJiraTags) {
    // Unwrap expression statements to get at the call expression.
    let callExpr = null;
    if (ts.isCallExpression(node) && isDescribeCall(node)) {
      callExpr = node;
    } else if (
      ts.isExpressionStatement(node) &&
      ts.isCallExpression(node.expression) &&
      isDescribeCall(node.expression)
    ) {
      callExpr = node.expression;
    }

    if (callExpr) {
      const ownTags = tagsFromDetailsArg(callExpr.arguments);
      const ownJiraTags = ownTags.filter((t) => JIRA_TAG_RE.test(t));
      const effectiveJiraTags = [...ancestorJiraTags, ...ownJiraTags];

      if (effectiveJiraTags.length === 0) {
        const nameArg = callExpr.arguments[0];
        const name =
          nameArg && ts.isStringLiteralLike(nameArg)
            ? nameArg.text
            : '<unnamed>';
        findings.push({
          relativePath,
          line: lineNumber(sourceFile, callExpr),
          name,
        });
      }

      // Recurse into the callback body, passing the updated tag set down.
      const lastArg = callExpr.arguments[callExpr.arguments.length - 1];
      if (
        lastArg &&
        (ts.isArrowFunction(lastArg) || ts.isFunctionExpression(lastArg)) &&
        lastArg.body &&
        ts.isBlock(lastArg.body)
      ) {
        for (const stmt of lastArg.body.statements) {
          visitNode(stmt, effectiveJiraTags);
        }
      }

      // Don't fall through to ts.forEachChild — we already handled children.
      return;
    }

    ts.forEachChild(node, (child) => visitNode(child, ancestorJiraTags));
  }

  for (const stmt of sourceFile.statements) {
    visitNode(stmt, []);
  }

  return findings;
}

// ---------------------------------------------------------------------------
// Argument parsing and file selection
// ---------------------------------------------------------------------------

const helpMode = process.argv.includes('--help') || process.argv.includes('-h');

if (helpMode) {
  console.log(`Usage: node playwright/check-jira-tags.cjs [--all] [<files...>]

Checks that every test.describe block in Playwright spec files carries at
least one Jira linkage tag (@PROJQUAY-#### or @QUAYIO-####).  A nested
describe inherits Jira tags from ancestor describes — only the outermost
block needs the tag.

Options
  --all          Check all spec files under playwright/e2e/ instead of only
                 files changed vs the default branch.
  --help, -h     Show this message.

Arguments
  <files...>     Explicit spec file paths to check.  Overrides --all and
                 diff-mode discovery.

Exit codes
  0  All checked describe blocks carry a Jira tag (or no files to check).
  1  One or more describe blocks are missing a Jira tag.

Examples
  # CI: pass changed files explicitly
  node playwright/check-jira-tags.cjs playwright/e2e/api/api-v2.spec.ts

  # Developer: check your own changes automatically
  node playwright/check-jira-tags.cjs

  # Full sweep (retroactive audit)
  node playwright/check-jira-tags.cjs --all`);
  process.exit(0);
}

const allMode = process.argv.includes('--all');
const positionalArgs = process.argv.slice(2).filter((a) => !a.startsWith('--'));

let specFiles;

if (positionalArgs.length > 0) {
  // Explicit file paths — resolve relative to cwd.
  specFiles = positionalArgs
    .map((f) => path.resolve(process.cwd(), f))
    .filter((f) => {
      if (!fs.existsSync(f)) {
        console.error(`Warning: file not found, skipping: ${f}`);
        return false;
      }
      return true;
    });
} else if (allMode) {
  specFiles = listAllSpecFiles(testRoot);
} else {
  // Default: diff mode — only files changed vs the default branch.
  specFiles = getChangedSpecFiles();
  if (specFiles.length === 0) {
    console.log(
      'No changed Playwright spec files detected. ' +
        'Pass --all to check all spec files, or provide explicit file paths.',
    );
    process.exit(0);
  }
  console.log(
    `Checking ${specFiles.length} changed spec file(s) for Jira tags...`,
  );
}

if (specFiles.length === 0) {
  console.log('No spec files to check.');
  process.exit(0);
}

// ---------------------------------------------------------------------------
// Run checks and report
// ---------------------------------------------------------------------------

const allFindings = specFiles.flatMap(collectFindings);

if (allFindings.length === 0) {
  console.log(
    `✓ All test.describe blocks carry a Jira linkage tag. ` +
      `(${specFiles.length} file(s) checked)`,
  );
  process.exit(0);
}

console.error(
  `✗ Missing Jira linkage tag on ${allFindings.length} test.describe block(s):\n`,
);
for (const finding of allFindings) {
  console.error(`  ${finding.relativePath}:${finding.line}  "${finding.name}"`);
}
console.error(
  `
Each test.describe block must carry a @PROJQUAY-#### or @QUAYIO-#### tag,
either directly or inherited from a parent describe.

Example:
  test.describe('My Suite', {tag: ['@QUAYIO-2183', '@api']}, () => {
    // All nested describes inherit @QUAYIO-2183 — no extra tag needed.
    test.describe('Nested', () => { ... });
  });`,
);
process.exit(1);
