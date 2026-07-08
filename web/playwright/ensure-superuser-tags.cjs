#!/usr/bin/env node

const fs = require('fs');
const path = require('path');
const ts = require('typescript');

const SUPERUSER_TAG = '@superuser';
const SUPERUSER_FIXTURES = new Set([
  'superuserApi',
  'superuserContext',
  'superuserPage',
  'superuserRequest',
  'freshUser',
]);
const FIXTURE_SOURCE_EXTENSIONS = new Set(['.ts', '.tsx']);
const SPEC_FILE_PATTERN = /\.spec\.tsx?$/;

const writeMode = process.argv.includes('--write');
const helpMode = process.argv.includes('--help') || process.argv.includes('-h');

if (helpMode) {
  console.log(`Usage: node playwright/ensure-superuser-tags.cjs [--write]

Checks that Playwright tests using superuser fixtures include ${SUPERUSER_TAG}.

By default, this script only reports missing tags and exits non-zero.
Pass --write to add ${SUPERUSER_TAG} to existing test declarations.`);
  process.exit(0);
}

const webRoot = path.resolve(__dirname, '..');
const testRoot = path.join(webRoot, 'playwright', 'e2e');

function listSpecFiles(dir) {
  const files = [];
  for (const entry of fs.readdirSync(dir, {withFileTypes: true})) {
    const fullPath = path.join(dir, entry.name);
    if (entry.isDirectory()) {
      files.push(...listSpecFiles(fullPath));
    } else if (
      entry.isFile() &&
      SPEC_FILE_PATTERN.test(entry.name) &&
      FIXTURE_SOURCE_EXTENSIONS.has(path.extname(entry.name))
    ) {
      files.push(fullPath);
    }
  }
  return files.sort();
}

function propertyNameText(name) {
  if (!name) {
    return undefined;
  }
  if (ts.isIdentifier(name) || ts.isStringLiteral(name)) {
    return name.text;
  }
  return undefined;
}

function expressionChain(expression) {
  if (ts.isIdentifier(expression)) {
    return [expression.text];
  }
  if (ts.isPropertyAccessExpression(expression)) {
    return [...expressionChain(expression.expression), expression.name.text];
  }
  return [];
}

function callbackArgument(args) {
  for (let i = args.length - 1; i >= 0; i -= 1) {
    const arg = args[i];
    if (ts.isArrowFunction(arg) || ts.isFunctionExpression(arg)) {
      return arg;
    }
  }
  return undefined;
}

function fixtureNamesFromBinding(name, names = []) {
  if (ts.isIdentifier(name)) {
    names.push(name.text);
  } else if (ts.isObjectBindingPattern(name)) {
    for (const element of name.elements) {
      if (!ts.isBindingElement(element)) {
        continue;
      }
      const propertyName = propertyNameText(element.propertyName);
      if (propertyName) {
        names.push(propertyName);
      } else {
        fixtureNamesFromBinding(element.name, names);
      }
    }
  } else if (ts.isArrayBindingPattern(name)) {
    for (const element of name.elements) {
      if (ts.isBindingElement(element)) {
        fixtureNamesFromBinding(element.name, names);
      }
    }
  }
  return names;
}

function fixtureNamesFromFunction(fn) {
  const firstParam = fn && fn.parameters[0];
  if (!firstParam) {
    return [];
  }
  return [...new Set(fixtureNamesFromBinding(firstParam.name))];
}

function tagProperty(detailsArg) {
  if (!detailsArg || !ts.isObjectLiteralExpression(detailsArg)) {
    return undefined;
  }
  return detailsArg.properties.find(
    (property) =>
      ts.isPropertyAssignment(property) &&
      propertyNameText(property.name) === 'tag',
  );
}

function tagsFromDetails(detailsArg) {
  const tags = [];
  const property = tagProperty(detailsArg);
  if (!property || !ts.isPropertyAssignment(property)) {
    return tags;
  }

  const value = property.initializer;
  if (ts.isStringLiteral(value)) {
    tags.push(value.text);
  } else if (ts.isArrayLiteralExpression(value)) {
    for (const element of value.elements) {
      if (ts.isStringLiteral(element)) {
        tags.push(element.text);
      }
    }
  }
  return tags;
}

function tagDetailsArg(args) {
  const secondArg = args[1];
  return secondArg && ts.isObjectLiteralExpression(secondArg)
    ? secondArg
    : undefined;
}

function testTitle(arg) {
  return arg && ts.isStringLiteralLike(arg) ? arg.text : '<dynamic title>';
}

function lineNumber(sourceFile, node) {
  return (
    sourceFile.getLineAndCharacterOfPosition(node.getStart(sourceFile)).line + 1
  );
}

function isTestCall(node) {
  if (!ts.isCallExpression(node)) {
    return false;
  }
  const chain = expressionChain(node.expression);
  if (chain[0] !== 'test') {
    return false;
  }
  if (chain.includes('describe')) {
    return false;
  }
  return !['beforeEach', 'afterEach', 'beforeAll', 'afterAll', 'use'].includes(
    chain[1],
  );
}

function isDescribeCall(node) {
  if (!ts.isCallExpression(node)) {
    return false;
  }
  const chain = expressionChain(node.expression);
  return chain[0] === 'test' && chain[1] === 'describe';
}

function isHookCall(node) {
  if (!ts.isCallExpression(node)) {
    return false;
  }
  const chain = expressionChain(node.expression);
  return (
    chain[0] === 'test' &&
    ['beforeEach', 'beforeAll', 'afterEach', 'afterAll'].includes(chain[1])
  );
}

function isExtendCall(node) {
  if (!ts.isCallExpression(node)) {
    return false;
  }
  const chain = expressionChain(node.expression);
  return chain[chain.length - 1] === 'extend';
}

function addRequiredFixtureNames(names, dependentFixtures) {
  return [...new Set(names.filter((name) => dependentFixtures.has(name)))];
}

function collectLocalFixtureDependencies(sourceFile, dependentFixtures) {
  const localFixtureDependencies = new Map();

  function recordFixtureDefinitions(node) {
    if (!isExtendCall(node)) {
      ts.forEachChild(node, recordFixtureDefinitions);
      return;
    }

    const fixturesArg = node.arguments[0];
    if (!fixturesArg || !ts.isObjectLiteralExpression(fixturesArg)) {
      return;
    }

    for (const property of fixturesArg.properties) {
      if (!ts.isPropertyAssignment(property)) {
        continue;
      }

      const fixtureName = propertyNameText(property.name);
      if (!fixtureName) {
        continue;
      }

      let fixtureFn = property.initializer;
      if (ts.isArrayLiteralExpression(fixtureFn)) {
        fixtureFn = fixtureFn.elements[0];
      }
      if (
        !ts.isArrowFunction(fixtureFn) &&
        !ts.isFunctionExpression(fixtureFn)
      ) {
        continue;
      }

      localFixtureDependencies.set(
        fixtureName,
        fixtureNamesFromFunction(fixtureFn),
      );
    }
  }

  recordFixtureDefinitions(sourceFile);

  let changed = true;
  while (changed) {
    changed = false;
    for (const [fixtureName, dependencies] of localFixtureDependencies) {
      if (dependentFixtures.has(fixtureName)) {
        continue;
      }
      if (
        dependencies.some((dependency) => dependentFixtures.has(dependency))
      ) {
        dependentFixtures.add(fixtureName);
        changed = true;
      }
    }
  }
}

function collectFindings(filePath) {
  const source = fs.readFileSync(filePath, 'utf8');
  const sourceFile = ts.createSourceFile(
    filePath,
    source,
    ts.ScriptTarget.Latest,
    true,
  );
  const relativePath = path.relative(webRoot, filePath);
  const dependentFixtures = new Set(SUPERUSER_FIXTURES);

  collectLocalFixtureDependencies(sourceFile, dependentFixtures);

  const findings = [];

  function visitStatements(statements, inheritedTags, inheritedHookFixtures) {
    const localHookFixtures = [];

    for (const statement of statements) {
      if (!isHookCall(statement)) {
        continue;
      }
      const hookFixtures = addRequiredFixtureNames(
        fixtureNamesFromFunction(callbackArgument(statement.arguments)),
        dependentFixtures,
      );
      localHookFixtures.push(...hookFixtures);
    }

    const hookFixtures = [
      ...new Set([...inheritedHookFixtures, ...localHookFixtures]),
    ];

    for (const statement of statements) {
      visitNode(statement, inheritedTags, hookFixtures);
    }
  }

  function visitNode(node, inheritedTags, inheritedHookFixtures) {
    if (isDescribeCall(node)) {
      const detailsArg = tagDetailsArg(node.arguments);
      const describeTags = tagsFromDetails(detailsArg);
      const describeCallback = callbackArgument(node.arguments);
      if (describeCallback && ts.isBlock(describeCallback.body)) {
        visitStatements(
          describeCallback.body.statements,
          [...inheritedTags, ...describeTags],
          inheritedHookFixtures,
        );
        return;
      }
    }

    if (isTestCall(node)) {
      const detailsArg = tagDetailsArg(node.arguments);
      const testTags = tagsFromDetails(detailsArg);
      const effectiveTags = [...inheritedTags, ...testTags];
      const directFixtures = addRequiredFixtureNames(
        fixtureNamesFromFunction(callbackArgument(node.arguments)),
        dependentFixtures,
      );
      const requiredFixtures = [
        ...new Set([...inheritedHookFixtures, ...directFixtures]),
      ];

      if (
        requiredFixtures.length > 0 &&
        !effectiveTags.includes(SUPERUSER_TAG)
      ) {
        findings.push({
          callExpression: node,
          detailsArg,
          filePath,
          fixtures: requiredFixtures,
          line: lineNumber(sourceFile, node),
          relativePath,
          source,
          sourceFile,
          title: testTitle(node.arguments[0]),
        });
      }
      return;
    }

    ts.forEachChild(node, (child) =>
      visitNode(child, inheritedTags, inheritedHookFixtures),
    );
  }

  visitStatements(sourceFile.statements, [], []);
  return findings;
}

function replaceTagInitializerOperation(sourceFile, tagValue) {
  if (ts.isStringLiteral(tagValue)) {
    return {
      start: tagValue.getStart(sourceFile),
      end: tagValue.getEnd(),
      text: `[${tagValue.getText(sourceFile)}, '${SUPERUSER_TAG}']`,
    };
  }

  if (ts.isArrayLiteralExpression(tagValue)) {
    const tagTexts = tagValue.elements.map((element) =>
      element.getText(sourceFile),
    );
    tagTexts.push(`'${SUPERUSER_TAG}'`);
    return {
      start: tagValue.getStart(sourceFile),
      end: tagValue.getEnd(),
      text: `[${tagTexts.join(', ')}]`,
    };
  }

  return undefined;
}

function operationForFinding(finding) {
  const {callExpression, detailsArg, sourceFile} = finding;

  if (!detailsArg) {
    return {
      start: callExpression.arguments[0].end,
      end: callExpression.arguments[0].end,
      text: `, {tag: '${SUPERUSER_TAG}'}`,
    };
  }

  const property = tagProperty(detailsArg);
  if (property && ts.isPropertyAssignment(property)) {
    return replaceTagInitializerOperation(sourceFile, property.initializer);
  }

  const openBrace = detailsArg.getStart(sourceFile);
  return {
    start: openBrace + 1,
    end: openBrace + 1,
    text: `tag: '${SUPERUSER_TAG}', `,
  };
}

function applyOperations(source, operations) {
  let output = source;
  const sorted = operations
    .filter(Boolean)
    .sort((left, right) => right.start - left.start);

  for (const operation of sorted) {
    output =
      output.slice(0, operation.start) +
      operation.text +
      output.slice(operation.end);
  }
  return output;
}

function groupByFile(findings) {
  const grouped = new Map();
  for (const finding of findings) {
    if (!grouped.has(finding.filePath)) {
      grouped.set(finding.filePath, []);
    }
    grouped.get(finding.filePath).push(finding);
  }
  return grouped;
}

const allFindings = listSpecFiles(testRoot).flatMap(collectFindings);

if (allFindings.length === 0) {
  console.log(`All superuser fixture tests include ${SUPERUSER_TAG}.`);
  process.exit(0);
}

if (writeMode) {
  const groupedFindings = groupByFile(allFindings);
  let appliedCount = 0;

  for (const [filePath, findings] of groupedFindings) {
    const source = fs.readFileSync(filePath, 'utf8');
    const operations = findings.map(operationForFinding).filter(Boolean);
    appliedCount += operations.length;
    fs.writeFileSync(filePath, applyOperations(source, operations));
  }

  console.log(
    `Added ${SUPERUSER_TAG} to ${appliedCount} test declarations in ` +
      `${groupedFindings.size} files.`,
  );

  if (appliedCount < allFindings.length) {
    console.error(
      `Could not automatically update ${allFindings.length - appliedCount} ` +
        'test declarations.',
    );
    process.exit(1);
  }

  process.exit(0);
}

console.error(
  `Missing ${SUPERUSER_TAG} on ${allFindings.length} Playwright tests using ` +
    'superuser fixtures:',
);
for (const finding of allFindings) {
  console.error(
    `  ${finding.relativePath}:${finding.line} ` +
      `[${finding.fixtures.join(', ')}] ${finding.title}`,
  );
}
console.error(
  `\nRun "node playwright/ensure-superuser-tags.cjs --write" from web/ to ` +
    `add ${SUPERUSER_TAG} to existing tests.`,
);
process.exit(1);
