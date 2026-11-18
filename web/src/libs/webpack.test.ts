import childProcess, {type ChildProcess} from 'node:child_process';
import {createRequire} from 'node:module';
import path from 'node:path';
import {clearTimeout, setImmediate, setTimeout} from 'node:timers';
import {describe, expect, it, vi} from 'vitest';

const requireFromWeb = createRequire(path.resolve('package.json'));
const Server = requireFromWeb('webpack-dev-server');
const {validate} = requireFromWeb('schema-utils');

type LaunchOutcome = {
  code: number | null;
  signal: NodeJS.Signals | null;
  warnings: unknown[][];
};

async function launchTarget(
  script: string,
  command = process.execPath,
  timeoutMs = 3_000,
): Promise<LaunchOutcome> {
  const warn = vi.fn();
  const spawn = childProcess.spawn;
  const spawnSpy = vi.spyOn(childProcess, 'spawn');
  let child: ChildProcess;
  let closed = Promise.resolve();
  let timer: ReturnType<typeof setTimeout>;
  const completed = new Promise<LaunchOutcome>((resolve, reject) => {
    timer = setTimeout(
      () => reject(new Error('Browser launcher timed out')),
      timeoutMs,
    );
    spawnSpy.mockImplementation((...args) => {
      try {
        child = spawn(...args);
      } catch (error) {
        reject(error);
        throw error;
      }
      closed = new Promise<void>((resolveClose) => {
        child.once('close', (code, signal) => {
          resolveClose();
          resolve({code, signal, warnings: warn.mock.calls});
        });
      });
      child.once('error', reject);
      return child;
    });
  });

  try {
    const [, outcome] = await Promise.all([
      Server.prototype.openBrowser.call(
        {
          options: {
            open: [
              {
                target: 'http://localhost:9000',
                options: {
                  app: {name: command, arguments: ['-e', script]},
                  wait: true,
                },
              },
            ],
          },
          logger: {warn},
        },
        'http://localhost:9000',
      ),
      completed,
    ]);
    await new Promise<void>((resolve) => setImmediate(resolve));
    expect(spawnSpy).toHaveBeenCalledTimes(1);
    return outcome;
  } finally {
    clearTimeout(timer);
    spawnSpy.mockRestore();
    if (child?.pid && child.exitCode === null && child.signalCode === null) {
      child.kill('SIGKILL');
    }
    await closed;
  }
}

function expectSuccessfulLaunch(outcome: LaunchOutcome): void {
  expect(outcome).toEqual({code: 0, signal: null, warnings: []});
}

describe('webpack development server configuration', () => {
  it.each(['./webpack.dev.js', './webpack.plugin.js'])(
    'accepts %s with the ESM-compatible server',
    (filename) => {
      const config = requireFromWeb(filename);
      expect(() => validate(Server.schema, config.devServer)).not.toThrow();
    },
  );

  it('preserves the standalone backend proxy routes', () => {
    const {devServer} = requireFromWeb('./webpack.dev.js');
    expect(devServer.open).toBe(true);
    expect(devServer.proxy).toEqual([
      {
        context: ['/api/v1', '/csrf_token', '/config', '/static', '/oauth'],
        target: 'http://localhost:8080',
        logLevel: 'debug',
      },
    ]);
  });

  it('observes successful child completion through the actual ESM consumer', async () => {
    expectSuccessfulLaunch(await launchTarget('process.exit(0)'));
  });

  it('rejects a failed launch with the same success assertion', async () => {
    const outcome = await launchTarget('process.exit(1)');
    expect(outcome).toEqual({
      code: 1,
      signal: null,
      warnings: [[expect.stringContaining('Unable to open')]],
    });
    expect(() => expectSuccessfulLaunch(outcome)).toThrow();
  });

  it('handles spawn errors and restores the real spawn function', async () => {
    const spawn = childProcess.spawn;
    await expect(
      launchTarget('process.exit(0)', path.join(process.execPath, 'missing')),
    ).rejects.toMatchObject({
      code: expect.stringMatching(/^(ENOENT|ENOTDIR)$/),
    });
    expect(childProcess.spawn).toBe(spawn);
  });

  it('kills and awaits a timed-out child and restores the real spawn function', async () => {
    const spawn = childProcess.spawn;
    await expect(
      launchTarget('setInterval(() => {}, 1000)', process.execPath, 500),
    ).rejects.toThrow('Browser launcher timed out');
    expect(childProcess.spawn).toBe(spawn);
  });
});
