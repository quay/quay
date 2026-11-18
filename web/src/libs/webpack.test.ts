import {createRequire} from 'node:module';
import path from 'node:path';
import {describe, expect, it} from 'vitest';

const requireFromWeb = createRequire(path.resolve('package.json'));
const Server = requireFromWeb('webpack-dev-server');
const {validate} = requireFromWeb('schema-utils');

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

  it('opens a target through the actual development server ESM consumer', async () => {
    await expect(
      Server.prototype.openBrowser.call(
        {
          options: {
            open: [
              {
                target: 'http://localhost:9000',
                options: {
                  app: {name: process.execPath, arguments: ['--version']},
                  wait: true,
                },
              },
            ],
          },
          logger: {warn: () => undefined},
        },
        'http://localhost:9000',
      ),
    ).resolves.toBeUndefined();
  });
});
