const {test} = require('node:test');
const assert = require('node:assert/strict');
const {createHostedQuay} = require('./hosted-quay');

const token = 'test-only-not-a-real-token';
const headers = {
  host: 'localhost:9010',
  origin: 'https://localhost:9010',
  'x-requested-with': 'XMLHttpRequest',
  'sec-fetch-site': 'same-origin',
};

function check(options = {}, request = {}) {
  const hosted = createHostedQuay({token, ...options});
  let status;
  let message;
  let forwarded = false;
  hosted.guard(
    {url: '/api/v1/user/plan', method: 'GET', headers, ...request},
    {
      status(code) {
        status = code;
        return this;
      },
      json(body) {
        message = body.message;
      },
    },
    () => {
      forwarded = true;
    },
  );
  return {forwarded, status, message};
}

test('requires a token without including its contents in errors', () => {
  for (const invalid of ['', undefined, 'secret with spaces']) {
    assert.throws(
      () => createHostedQuay({token: invalid}),
      /^Error: Set QUAY_OAUTH_TOKEN locally/,
    );
  }
});

test('permits same-origin reads and local assets', () => {
  assert.equal(check().forwarded, true);
  assert.equal(check({}, {url: '/config'}).forwarded, true);
  assert.equal(
    check({}, {url: '/main.bundle.js', headers: {}}).forwarded,
    true,
  );
});

test('rejects foreign origins, DNS rebinding, browser navigation, and cross-site requests', () => {
  for (const changes of [
    {origin: 'https://attacker.example'},
    {host: 'attacker.example:9010'},
    {'x-requested-with': undefined},
    {'sec-fetch-site': 'cross-site'},
    {origin: 'null'},
  ]) {
    const result = check({}, {headers: {...headers, ...changes}});
    assert.equal(result.status, 403);
    assert.equal(result.forwarded, false);
  }
});

test('blocks all writes by default', () => {
  for (const method of ['POST', 'PUT', 'DELETE', 'PATCH', 'OPTIONS']) {
    const result = check({}, {method});
    assert.equal(result.forwarded, false);
    assert.equal(result.status, 403);
  }
});

test('write opt-in permits only plan creation, plan updates, and card setup', () => {
  for (const prefix of ['/api/v1/user', '/api/v1/organization/my-org']) {
    for (const [method, suffix] of [
      ['POST', 'plan'],
      ['PUT', 'plan'],
      ['POST', 'card'],
    ]) {
      assert.equal(
        check({allowBillingWrites: true}, {method, url: `${prefix}/${suffix}`})
          .forwarded,
        true,
      );
    }
    for (const [method, suffix] of [
      ['DELETE', 'plan'],
      ['PUT', 'card'],
      ['POST', 'marketplace'],
    ]) {
      assert.equal(
        check({allowBillingWrites: true}, {method, url: `${prefix}/${suffix}`})
          .status,
        403,
      );
    }
  }
  assert.equal(
    check({allowBillingWrites: true}, {method: 'PUT', url: '/api/v1/user/'})
      .status,
    403,
  );
});

test('uses the configured local port for origin verification', () => {
  assert.equal(check({port: 9020}).status, 403);
  assert.equal(
    check(
      {port: 9020},
      {
        headers: {
          ...headers,
          host: 'localhost:9020',
          origin: 'https://localhost:9020',
        },
      },
    ).forwarded,
    true,
  );
});

test('authenticates API requests at the fixed TLS-verified upstream and strips browser credentials', () => {
  const {proxy} = createHostedQuay({token});
  assert.equal(proxy.target, 'https://quay.io');
  assert.equal(proxy.secure, true);
  assert.equal(proxy.followRedirects, false);
  assert.equal(proxy.logLevel, 'silent');
  assert.equal(proxy.context('/api/v1/user/'), true);
  assert.equal(proxy.context('/oauth/authorize'), false);
  assert.equal(proxy.context('/api/v1evil'), false);
  for (const path of ['/api/v1/user/', '/config', '/csrf_token']) {
    const forwarded = new Map([
      ['cookie', 'browser-session'],
      ['authorization', 'browser-token'],
    ]);
    proxy.onProxyReq(
      {
        removeHeader: (name) => forwarded.delete(name.toLowerCase()),
        setHeader: (name, value) => forwarded.set(name.toLowerCase(), value),
      },
      {url: path},
    );
    assert.equal(forwarded.has('cookie'), false);
    assert.equal(
      forwarded.get('authorization'),
      path.startsWith('/api/v1/') ? `Bearer ${token}` : undefined,
    );
  }
});

test('strips upstream sessions and CORS headers from local responses', () => {
  const response = {
    headers: {
      'set-cookie': ['session=example'],
      'access-control-allow-origin': '*',
      'access-control-allow-credentials': 'true',
    },
  };
  createHostedQuay({token}).proxy.onProxyRes(response);
  assert.deepEqual(response.headers, {'cache-control': 'no-store'});
});

test('proxy errors never expose request headers or OAuth tokens', () => {
  let body;
  let status;
  createHostedQuay({token}).proxy.onError(
    new Error(token),
    {},
    {
      writeHead: (code) => {
        status = code;
      },
      end: (value) => {
        body = value;
      },
    },
  );
  assert.equal(status, 502);
  assert.equal(body.includes(token), false);
});

test('hosted build definitions contain only public settings and override mock defaults', () => {
  const before = {...process.env};
  try {
    process.env.QUAY_OAUTH_TOKEN = token;
    process.env.MOCK_API = 'true';
    const config = require('./webpack.hosted');
    const definitions = config.plugins.find(
      (plugin) => plugin.definitions,
    )?.definitions;
    assert.equal(definitions['process.env.MOCK_API'], '"false"');
    assert.equal(definitions['process.env.REACT_QUAY_APP_API_URL'], '""');
    assert.equal(JSON.stringify(definitions).includes(token), false);
    assert.equal(config.devServer.host, '127.0.0.1');
    assert.equal(config.devServer.server.type, 'https');
    assert.equal(
      config.plugins.some((plugin) => plugin.constructor.name === 'Dotenv'),
      false,
    );
  } finally {
    process.env = before;
  }
});
