import {writeFile} from 'fs/promises';
import {test} from '@playwright/test';
import {suiteStartFile} from '../../utils/health-gate';

test('record suite start for the health gate', async () => {
  const testInfo = test.info();
  await writeFile(
    suiteStartFile(testInfo.project.outputDir),
    String(Date.now() * 1000),
  );
});
