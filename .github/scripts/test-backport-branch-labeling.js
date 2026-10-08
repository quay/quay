#!/usr/bin/env node
'use strict';

const assert = require('node:assert/strict');
const fs = require('node:fs');
const path = require('node:path');

const repositoryRoot = path.resolve(__dirname, '..', '..');
const statusWorkflow = path.join(repositoryRoot, '.github/workflows/pr-status-labeler.yaml');
const backportWorkflow = path.join(repositoryRoot, '.github/workflows/label-backported-pr.yml');

function extractGithubScript(workflowPath) {
  const lines = fs.readFileSync(workflowPath, 'utf8').split('\n');
  const scriptMarkers = lines
    .map((line, index) => (/^\s*script:\s*\|\s*$/.test(line) ? index : -1))
    .filter((index) => index !== -1);
  assert.equal(scriptMarkers.length, 1, 'expected exactly one github-script block');
  const start = scriptMarkers[0];
  const firstScriptLine = lines[start + 1];
  const scriptIndent = firstScriptLine.match(/^\s*/)[0].length;
  assert.ok(scriptIndent > 0, 'github-script block has no content');

  const scriptLines = [];
  for (let index = start + 1; index < lines.length; index += 1) {
    const line = lines[index];
    if (line.trim() === '') {
      scriptLines.push(line);
      continue;
    }
    const lineIndent = line.match(/^\s*/)[0].length;
    if (lineIndent < scriptIndent) {
      break;
    }
    scriptLines.push(line.slice(scriptIndent));
  }

  return scriptLines.join('\n');
}

function extractTriggerBranches(workflowPath) {
  const lines = fs.readFileSync(workflowPath, 'utf8').split('\n');
  const triggerStart = lines.findIndex((line) => /^\s*pull_request_target:\s*$/.test(line));
  assert.notEqual(triggerStart, -1, 'pull_request_target trigger not found');
  const start = lines.findIndex((line, index) => index > triggerStart && /^\s*branches:\s*$/.test(line));
  assert.notEqual(start, -1, 'trigger branches block not found');
  const branchIndent = lines[start].match(/^\s*/)[0].length;
  const branchPattern = new RegExp("^ {" + (branchIndent + 2) + "}- '([^']+)'$");

  const branches = [];
  for (let index = start + 1; index < lines.length; index += 1) {
    const match = lines[index].match(branchPattern);
    if (!match) {
      break;
    }
    branches.push(match[1]);
  }
  return branches;
}

function triggerMatches(branch, patterns) {
  return patterns.some((pattern) => new RegExp('^' + pattern.replace(/\*/g, '.*') + '$').test(branch));
}

async function runStatusLabeler(script, baseRefName, currentLabels) {
  const added = [];
  const removed = [];
  const github = {
    graphql: async () => ({
      repository: {
        pullRequest: {
          reviewDecision: null,
          mergeable: true,
          mergeStateStatus: 'CLEAN',
          baseRefName,
          labels: { nodes: currentLabels.map((name) => ({ name })) },
        },
      },
    }),
    rest: {
      issues: {
        addLabels: async ({ labels }) => added.push(...labels),
        removeLabel: async ({ name }) => removed.push(name),
      },
    },
  };
  const context = { repo: { owner: 'quay', repo: 'quay' } };
  const quietConsole = { log: () => {} };
  const AsyncFunction = Object.getPrototypeOf(async function () {}).constructor;
  const execute = new AsyncFunction('github', 'context', 'console', script);
  const previousPrNumber = process.env.PR_NUMBER;
  process.env.PR_NUMBER = '1';
  try {
    await execute(github, context, quietConsole);
  } finally {
    if (previousPrNumber === undefined) {
      delete process.env.PR_NUMBER;
    } else {
      process.env.PR_NUMBER = previousPrNumber;
    }
  }
  return { added, removed };
}

async function main() {
  const script = extractGithubScript(statusWorkflow);
  const triggerBranches = extractTriggerBranches(backportWorkflow);
  assert.deepEqual(triggerBranches, ['redhat-*', 'mirror-registry-*']);

  const cases = [
    {
      branch: 'redhat-3.17',
      labels: ['backport/redhat-3.16'],
      added: ['backport/redhat-3.17'],
      removed: ['backport/redhat-3.16'],
      trigger: true,
    },
    {
      branch: 'mirror-registry-3.0',
      labels: ['backport/redhat-3.17'],
      added: ['backport/mirror-registry-3.0'],
      removed: ['backport/redhat-3.17'],
      trigger: true,
    },
    {
      branch: 'master',
      labels: ['backport/redhat-3.17', 'backport/mirror-registry-3.0'],
      added: [],
      removed: ['backport/redhat-3.17', 'backport/mirror-registry-3.0'],
      trigger: false,
    },
    {
      branch: 'unknown-3.0',
      labels: ['backport/redhat-3.17'],
      added: [],
      removed: ['backport/redhat-3.17'],
      trigger: false,
    },
    {
      branch: 'mirror-registry-3',
      labels: ['backport/mirror-registry-3.0'],
      added: [],
      removed: ['backport/mirror-registry-3.0'],
      trigger: true,
    },
  ];

  for (const testCase of cases) {
    const result = await runStatusLabeler(script, testCase.branch, testCase.labels);
    assert.deepEqual(result.added, testCase.added, testCase.branch + ' added labels');
    assert.deepEqual(result.removed.sort(), testCase.removed.sort(), testCase.branch + ' removed labels');
    assert.equal(triggerMatches(testCase.branch, triggerBranches), testCase.trigger,
      testCase.branch + ' trigger match');
  }

  console.log('all workflow branch labeling cases passed');
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
