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

function errorWithStatus(status, responseErrors, topLevelErrors) {
  const error = new Error('mock GitHub API error');
  error.status = status;
  if (responseErrors !== undefined) {
    error.response = { data: { errors: responseErrors } };
  }
  if (topLevelErrors !== undefined) {
    error.errors = topLevelErrors;
  }
  return error;
}

function errorFromOption(option) {
  if (typeof option === 'number') {
    return errorWithStatus(option);
  }
  return errorWithStatus(option.status, option.responseErrors, option.topLevelErrors);
}

async function runStatusLabeler(script, options) {
  const repositoryLabels = new Map((options.repositoryLabels || []).map((label) => [label.name, label]));
  const added = [];
  const removed = [];
  const created = [];
  const calls = [];
  let getLabelCalls = 0;
  const github = {
    graphql: async () => ({
      repository: {
        pullRequest: {
          reviewDecision: options.reviewDecision || null,
          mergeable: options.mergeable === undefined ? true : options.mergeable,
          mergeStateStatus: options.mergeStateStatus || 'CLEAN',
          baseRefName: options.branch,
          labels: { nodes: (options.currentLabels || []).map((name) => ({ name })) },
        },
      },
    }),
    rest: {
      issues: {
        getLabel: async ({ name }) => {
          calls.push({ type: 'getLabel', name });
          getLabelCalls += 1;
          if (options.getLabelError) {
            throw errorFromOption(options.getLabelError);
          }
          if (getLabelCalls > 1 && options.reReadLabelError) {
            throw errorFromOption(options.reReadLabelError);
          }
          const label = repositoryLabels.get(name);
          if (!label) {
            throw errorWithStatus(404);
          }
          return label;
        },
        createLabel: async ({ name, color, description }) => {
          calls.push({ type: 'createLabel', name, color, description });
          const label = { name, color, description };
          if (options.createLabelAlreadyExists) {
            repositoryLabels.set(name, label);
            throw errorWithStatus(422, [{
              resource: 'Label',
              field: 'name',
              code: 'already_exists',
            }]);
          }
          if (options.createLabelError) {
            throw errorFromOption(options.createLabelError);
          }
          repositoryLabels.set(name, label);
          created.push(label);
          return label;
        },
        addLabels: async ({ labels }) => {
          calls.push({ type: 'addLabels', labels });
          added.push(...labels);
        },
        removeLabel: async ({ name }) => {
          calls.push({ type: 'removeLabel', name });
          removed.push(name);
        },
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
  return { added, removed, created, calls };
}

async function main() {
  const script = extractGithubScript(statusWorkflow);
  const triggerBranches = extractTriggerBranches(backportWorkflow);
  assert.deepEqual(triggerBranches, ['redhat-*', 'mirror-registry-*']);
  const mirrorRegistryLabel = {
    name: 'backport/mirror-registry-3.0',
    color: '0E8A16',
    description: 'Backported to mirror-registry-3.0',
  };

  const cases = [
    {
      branch: 'redhat-3.17',
      currentLabels: ['backport/redhat-3.16'],
      added: ['backport/redhat-3.17'],
      removed: ['backport/redhat-3.16'],
      created: [],
      calls: [
        { type: 'addLabels', labels: ['backport/redhat-3.17'] },
        { type: 'removeLabel', name: 'backport/redhat-3.16' },
      ],
      trigger: true,
    },
    {
      branch: 'mirror-registry-3.0',
      currentLabels: ['backport/redhat-3.17'],
      added: ['backport/mirror-registry-3.0'],
      removed: ['backport/redhat-3.17'],
      created: [mirrorRegistryLabel],
      calls: [
        { type: 'getLabel', name: mirrorRegistryLabel.name },
        { type: 'createLabel', ...mirrorRegistryLabel },
        { type: 'addLabels', labels: [mirrorRegistryLabel.name] },
        { type: 'removeLabel', name: 'backport/redhat-3.17' },
      ],
      trigger: true,
    },
    {
      branch: 'mirror-registry-3.0',
      currentLabels: ['backport/redhat-3.17'],
      createLabelAlreadyExists: true,
      added: ['backport/mirror-registry-3.0'],
      removed: ['backport/redhat-3.17'],
      created: [],
      calls: [
        { type: 'getLabel', name: mirrorRegistryLabel.name },
        { type: 'createLabel', ...mirrorRegistryLabel },
        { type: 'getLabel', name: mirrorRegistryLabel.name },
        { type: 'addLabels', labels: [mirrorRegistryLabel.name] },
        { type: 'removeLabel', name: 'backport/redhat-3.17' },
      ],
      trigger: true,
    },
    {
      branch: 'mirror-registry-3.0',
      repositoryLabels: [mirrorRegistryLabel],
      added: [mirrorRegistryLabel.name],
      removed: [],
      created: [],
      calls: [
        { type: 'getLabel', name: mirrorRegistryLabel.name },
        { type: 'addLabels', labels: [mirrorRegistryLabel.name] },
      ],
      trigger: true,
    },
    {
      branch: 'mirror-registry-3.0',
      currentLabels: [mirrorRegistryLabel.name],
      added: [],
      removed: [],
      created: [],
      calls: [],
      trigger: true,
    },
    {
      branch: 'master',
      currentLabels: ['backport/redhat-3.17', mirrorRegistryLabel.name],
      added: [],
      removed: ['backport/redhat-3.17', mirrorRegistryLabel.name],
      created: [],
      calls: [
        { type: 'removeLabel', name: 'backport/redhat-3.17' },
        { type: 'removeLabel', name: mirrorRegistryLabel.name },
      ],
      trigger: false,
    },
    {
      branch: 'unknown-3.0',
      currentLabels: ['backport/redhat-3.17'],
      added: [],
      removed: ['backport/redhat-3.17'],
      created: [],
      calls: [{ type: 'removeLabel', name: 'backport/redhat-3.17' }],
      trigger: false,
    },
    {
      branch: 'mirror-registry-3',
      currentLabels: [mirrorRegistryLabel.name],
      added: [],
      removed: [mirrorRegistryLabel.name],
      created: [],
      calls: [{ type: 'removeLabel', name: mirrorRegistryLabel.name }],
      trigger: true,
    },
    {
      branch: 'mirror-registry-3.0',
      repositoryLabels: [mirrorRegistryLabel],
      reviewDecision: 'APPROVED',
      mergeable: false,
      mergeStateStatus: 'DIRTY',
      added: ['approved', 'needs-rebase', mirrorRegistryLabel.name],
      removed: [],
      created: [],
      calls: [
        { type: 'getLabel', name: mirrorRegistryLabel.name },
        { type: 'addLabels', labels: ['approved', 'needs-rebase', mirrorRegistryLabel.name] },
      ],
      trigger: true,
    },
  ];

  for (const testCase of cases) {
    const result = await runStatusLabeler(script, testCase);
    assert.deepEqual(result.added, testCase.added, testCase.branch + ' added labels');
    assert.deepEqual(result.removed, testCase.removed, testCase.branch + ' removed labels');
    assert.deepEqual(result.created, testCase.created, testCase.branch + ' created labels');
    assert.deepEqual(result.calls, testCase.calls, testCase.branch + ' GitHub API calls');
    assert.equal(triggerMatches(testCase.branch, triggerBranches), testCase.trigger,
      testCase.branch + ' trigger match');
  }

  await assert.rejects(
    runStatusLabeler(script, { branch: 'mirror-registry-3.0', getLabelError: 500 }),
    (error) => error.status === 500,
    'non-404 label lookups must fail'
  );
  await assert.rejects(
    runStatusLabeler(script, { branch: 'mirror-registry-3.0', createLabelError: 422 }),
    (error) => error.status === 422,
    'generic 422 label creation failures must fail'
  );
  await assert.rejects(
    runStatusLabeler(script, {
      branch: 'mirror-registry-3.0',
      createLabelError: {
        status: 422,
        responseErrors: [{ resource: 'Label', field: 'name', code: 'invalid' }],
      },
    }),
    (error) => error.status === 422,
    'invalid 422 diagnostics must fail'
  );
  await assert.rejects(
    runStatusLabeler(script, {
      branch: 'mirror-registry-3.0',
      createLabelError: {
        status: 422,
        responseErrors: [{ resource: 'Repository', field: 'name', code: 'already_exists' }],
      },
    }),
    (error) => error.status === 422,
    'other-resource 422 diagnostics must fail'
  );
  await assert.rejects(
    runStatusLabeler(script, {
      branch: 'mirror-registry-3.0',
      createLabelError: {
        status: 422,
        responseErrors: [
          { resource: 'Label', field: 'name', code: 'already_exists' },
          { resource: 'Label', field: 'name', code: 'invalid' },
        ],
      },
    }),
    (error) => error.status === 422,
    'mixed 422 diagnostics must fail'
  );
  await assert.rejects(
    runStatusLabeler(script, {
      branch: 'mirror-registry-3.0',
      createLabelError: {
        status: 422,
        responseErrors: { resource: 'Label', field: 'name', code: 'already_exists' },
      },
    }),
    (error) => error.status === 422,
    'malformed 422 diagnostics must fail'
  );
  await assert.rejects(
    runStatusLabeler(script, {
      branch: 'mirror-registry-3.0',
      createLabelError: {
        status: 500,
        responseErrors: [{ resource: 'Label', field: 'name', code: 'already_exists' }],
      },
    }),
    (error) => error.status === 500,
    'non-422 creation failures must fail'
  );
  await assert.rejects(
    runStatusLabeler(script, {
      branch: 'mirror-registry-3.0',
      createLabelError: {
        status: 422,
        topLevelErrors: [{ resource: 'Label', field: 'name', code: 'already_exists' }],
      },
    }),
    (error) => error.status === 422,
    'top-level-only diagnostics must fail'
  );
  await assert.rejects(
    runStatusLabeler(script, {
      branch: 'mirror-registry-3.0',
      createLabelAlreadyExists: true,
      reReadLabelError: 404,
    }),
    (error) => error.status === 404,
    '404 rereads after a competing creation must fail'
  );
  await assert.rejects(
    runStatusLabeler(script, {
      branch: 'mirror-registry-3.0',
      createLabelAlreadyExists: true,
      reReadLabelError: 500,
    }),
    (error) => error.status === 500,
    '500 rereads after a competing creation must fail'
  );

  console.log('all workflow branch labeling cases passed');
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
