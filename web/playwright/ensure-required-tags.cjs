#!/usr/bin/env node

const fs = require('fs');
const path = require('path');
const ts = require('typescript');

const REQUIRED_TAG_RULES = [
  {
    tag: '@superuser',
    fixtures: new Set([
      'superuserApi',
      'superuserContext',
      'superuserPage',
      'superuserRequest',
      'freshUser',
    ]),
  },
  {
    tag: '@webhook',
    fixtures: new Set(['webhook']),
    constructors: new Set(['WebhookReceiver']),
  },
];
const FIXTURE_SOURCE_EXTENSIONS = new Set(['.ts', '.tsx']);
const SPEC_FILE_PATTERN = /\.spec\.tsx?$/;

const writeMode = process.argv.includes('--write');
const helpMode = process.argv.includes('--help') || process.argv.includes('-h');

if (helpMode) {
  console.log(`Usage: node playwright/ensure-required-tags.cjs [--write]

Checks that Playwright tests include required usage tags when they use tagged fixtures or helpers.

By default, this script only reports missing tags and exits non-zero.
Pass --write to add missing tags to existing test declarations.`);
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

function expressionMatches(expression, names) {
  const chain = expressionChain(expression);
  if (chain.length === 0) {
    return undefined;
  }

  const fullName = chain.join('.');
  if (names.has(fullName)) {
    return fullName;
  }

  const localName = chain[chain.length - 1];
  return names.has(localName) ? localName : undefined;
}

function addUsage(usagesByTag, tag, usage) {
  if (!usagesByTag.has(tag)) {
    usagesByTag.set(tag, new Set());
  }
  usagesByTag.get(tag).add(usage);
}

function mergeUsageMaps(...usageMaps) {
  const merged = new Map();
  for (const usageMap of usageMaps) {
    for (const [tag, usages] of usageMap) {
      for (const usage of usages) {
        addUsage(merged, tag, usage);
      }
    }
  }
  return merged;
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

function callExpressionFromNode(node) {
  if (ts.isCallExpression(node)) {
    return node;
  }
  if (ts.isExpressionStatement(node) && ts.isCallExpression(node.expression)) {
    return node.expression;
  }
  return undefined;
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

function collectLocalFixtureDefinitions(sourceFile) {
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
  return localFixtureDependencies;
}

function dependentFixturesForRule(rule, localFixtureDependencies) {
  const dependentFixtures = new Set(rule.fixtures || []);

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

  return dependentFixtures;
}

function collectFixtureUsages(fixtureNames, dependentFixturesByTag) {
  const usages = new Map();
  for (const rule of REQUIRED_TAG_RULES) {
    const dependentFixtures = dependentFixturesByTag.get(rule.tag);
    for (const fixtureName of fixtureNames) {
      if (dependentFixtures.has(fixtureName)) {
        addUsage(usages, rule.tag, fixtureName);
      }
    }
  }
  return usages;
}

function collectHelperUsages(node) {
  const usages = new Map();
  if (!node) {
    return usages;
  }

  function visit(current) {
    if (ts.isNewExpression(current)) {
      for (const rule of REQUIRED_TAG_RULES) {
        const constructor = expressionMatches(
          current.expression,
          rule.constructors || new Set(),
        );
        if (constructor) {
          addUsage(usages, rule.tag, constructor);
        }
      }
    }

    if (ts.isCallExpression(current)) {
      for (const rule of REQUIRED_TAG_RULES) {
        const fn = expressionMatches(
          current.expression,
          rule.functions || new Set(),
        );
        if (fn) {
          addUsage(usages, rule.tag, fn);
        }
      }
    }

    ts.forEachChild(current, visit);
  }

  visit(node);
  return usages;
}

function collectFunctionUsages(fn, dependentFixturesByTag) {
  if (!fn) {
    return new Map();
  }

  return mergeUsageMaps(
    collectFixtureUsages(fixtureNamesFromFunction(fn), dependentFixturesByTag),
    collectHelperUsages(fn.body),
  );
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
  const localFixtureDependencies = collectLocalFixtureDefinitions(sourceFile);
  const dependentFixturesByTag = new Map(
    REQUIRED_TAG_RULES.map((rule) => [
      rule.tag,
      dependentFixturesForRule(rule, localFixtureDependencies),
    ]),
  );

  const findings = [];

  function visitStatements(statements, inheritedTags, inheritedHookUsages) {
    const localHookUsages = [];

    for (const statement of statements) {
      const hookCall = callExpressionFromNode(statement);
      if (!hookCall || !isHookCall(hookCall)) {
        continue;
      }
      const hookUsages = collectFunctionUsages(
        callbackArgument(hookCall.arguments),
        dependentFixturesByTag,
      );
      localHookUsages.push(hookUsages);
    }

    const hookUsages = mergeUsageMaps(inheritedHookUsages, ...localHookUsages);

    for (const statement of statements) {
      visitNode(statement, inheritedTags, hookUsages);
    }
  }

  function visitNode(node, inheritedTags, inheritedHookUsages) {
    const callExpression = callExpressionFromNode(node);

    if (callExpression && isDescribeCall(callExpression)) {
      const detailsArg = tagDetailsArg(callExpression.arguments);
      const describeTags = tagsFromDetails(detailsArg);
      const describeCallback = callbackArgument(callExpression.arguments);
      if (describeCallback && ts.isBlock(describeCallback.body)) {
        visitStatements(
          describeCallback.body.statements,
          [...inheritedTags, ...describeTags],
          inheritedHookUsages,
        );
        return;
      }
    }

    if (callExpression && isTestCall(callExpression)) {
      const detailsArg = tagDetailsArg(callExpression.arguments);
      const testTags = tagsFromDetails(detailsArg);
      const effectiveTags = [...inheritedTags, ...testTags];
      const directUsages = collectFunctionUsages(
        callbackArgument(callExpression.arguments),
        dependentFixturesByTag,
      );
      const requiredUsages = mergeUsageMaps(inheritedHookUsages, directUsages);
      const missingRequirements = [];

      for (const rule of REQUIRED_TAG_RULES) {
        const usages = requiredUsages.get(rule.tag);
        if (usages && usages.size > 0 && !effectiveTags.includes(rule.tag)) {
          missingRequirements.push({
            tag: rule.tag,
            usages: [...usages],
          });
        }
      }

      if (missingRequirements.length > 0) {
        findings.push({
          callExpression,
          detailsArg,
          filePath,
          line: lineNumber(sourceFile, callExpression),
          missingRequirements,
          relativePath,
          source,
          sourceFile,
          title: testTitle(callExpression.arguments[0]),
        });
      }
      return;
    }

    ts.forEachChild(node, (child) =>
      visitNode(child, inheritedTags, inheritedHookUsages),
    );
  }

  visitStatements(sourceFile.statements, [], new Map());
  return findings;
}

function tagInitializerText(tags) {
  if (tags.length === 1) {
    return `'${tags[0]}'`;
  }
  return `[${tags.map((tag) => `'${tag}'`).join(', ')}]`;
}

function replaceTagInitializerOperation(sourceFile, tagValue, tags) {
  if (ts.isStringLiteral(tagValue)) {
    return {
      start: tagValue.getStart(sourceFile),
      end: tagValue.getEnd(),
      text: `[${tagValue.getText(sourceFile)}, ${tags
        .map((tag) => `'${tag}'`)
        .join(', ')}]`,
      tagCount: tags.length,
    };
  }

  if (ts.isArrayLiteralExpression(tagValue)) {
    const tagTexts = tagValue.elements.map((element) =>
      element.getText(sourceFile),
    );
    tagTexts.push(...tags.map((tag) => `'${tag}'`));
    return {
      start: tagValue.getStart(sourceFile),
      end: tagValue.getEnd(),
      text: `[${tagTexts.join(', ')}]`,
      tagCount: tags.length,
    };
  }

  return undefined;
}

function operationForFinding(finding) {
  const {callExpression, detailsArg, sourceFile} = finding;
  const tags = finding.missingRequirements.map(({tag}) => tag);
  const tagText = tagInitializerText(tags);

  if (!detailsArg) {
    if (!callExpression.arguments[0]) {
      return undefined;
    }
    return {
      start: callExpression.arguments[0].end,
      end: callExpression.arguments[0].end,
      text: `, {tag: ${tagText}}`,
      tagCount: tags.length,
    };
  }

  const property = tagProperty(detailsArg);
  if (property && ts.isPropertyAssignment(property)) {
    return replaceTagInitializerOperation(
      sourceFile,
      property.initializer,
      tags,
    );
  }

  const openBrace = detailsArg.getStart(sourceFile);
  return {
    start: openBrace + 1,
    end: openBrace + 1,
    text: `tag: ${tagText}, `,
    tagCount: tags.length,
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

function missingRequirementCount(findings) {
  return findings.reduce(
    (count, finding) => count + finding.missingRequirements.length,
    0,
  );
}

const allFindings = listSpecFiles(testRoot).flatMap(collectFindings);

if (allFindings.length === 0) {
  console.log('All Playwright tests include required usage tags.');
  process.exit(0);
}

if (writeMode) {
  const groupedFindings = groupByFile(allFindings);
  let appliedDeclarationCount = 0;
  let appliedTagCount = 0;

  for (const [filePath, findings] of groupedFindings) {
    const source = fs.readFileSync(filePath, 'utf8');
    const operations = findings.map(operationForFinding).filter(Boolean);
    appliedDeclarationCount += operations.length;
    appliedTagCount += operations.reduce(
      (count, operation) => count + operation.tagCount,
      0,
    );
    fs.writeFileSync(filePath, applyOperations(source, operations));
  }

  console.log(
    `Added ${appliedTagCount} required tags to ` +
      `${appliedDeclarationCount} test declarations in ` +
      `${groupedFindings.size} files.`,
  );

  if (appliedDeclarationCount < allFindings.length) {
    console.error(
      `Could not automatically update ` +
        `${allFindings.length - appliedDeclarationCount} test declarations.`,
    );
    process.exit(1);
  }

  process.exit(0);
}

console.error(
  `Missing ${missingRequirementCount(allFindings)} required usage tags on ` +
    `${allFindings.length} Playwright tests:`,
);
for (const finding of allFindings) {
  for (const requirement of finding.missingRequirements) {
    console.error(
      `  ${finding.relativePath}:${finding.line} ${requirement.tag} ` +
        `[${requirement.usages.join(', ')}] ${finding.title}`,
    );
  }
}
console.error(
  '\nRun "node playwright/ensure-required-tags.cjs --write" from web/ to ' +
    'add missing tags to existing tests.',
);
process.exit(1);
