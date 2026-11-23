// Server-side development configuration. Never pass the OAuth token to DefinePlugin.
const UPSTREAM = 'https://quay.io';
const BILLING_PATH =
  /^\/api\/v1\/(?:user|organization\/[a-zA-Z0-9_-]+)\/(?:plan|card)$/;

function createHostedQuay({token, port = 9010, allowBillingWrites = false}) {
  if (!token || /\s/.test(token)) {
    throw new Error(
      'Set QUAY_OAUTH_TOKEN locally before starting the hosted profile.',
    );
  }
  const origins = new Set([
    `https://localhost:${port}`,
    `https://127.0.0.1:${port}`,
  ]);
  const hosts = new Set([`localhost:${port}`, `127.0.0.1:${port}`]);
  const contexts = ['/api/v1', '/config', '/csrf_token'];
  const isProxied = (path) =>
    contexts.some((prefix) => path === prefix || path.startsWith(`${prefix}/`));

  function guard(req, res, next) {
    const path = req.url.split('?')[0];
    if (!isProxied(path)) return next();
    const fail = (message) => res.status(403).json({message});
    if (
      !hosts.has(req.headers.host) ||
      (req.headers.origin && !origins.has(req.headers.origin)) ||
      (req.headers['sec-fetch-site'] &&
        !['same-origin', 'none'].includes(req.headers['sec-fetch-site'])) ||
      req.headers['x-requested-with'] !== 'XMLHttpRequest'
    ) {
      return fail(
        'Hosted API requests must come from this local development UI.',
      );
    }
    if (['GET', 'HEAD'].includes(req.method)) return next();
    if (
      allowBillingWrites &&
      BILLING_PATH.test(path) &&
      (req.method === 'POST' ||
        (req.method === 'PUT' && path.endsWith('/plan')))
    ) {
      return next();
    }
    return fail(
      'This hosted development session allows read-only API access. Enable QUAY_BILLING_WRITES=true locally to change plans or payment methods.',
    );
  }

  return {
    guard,
    proxy: {
      context: isProxied,
      target: UPSTREAM,
      changeOrigin: true,
      secure: true,
      followRedirects: false,
      logLevel: 'silent',
      proxyTimeout: 30000,
      onProxyReq(proxyReq, req) {
        // Authenticate only API calls. Browser cookies and credentials never go upstream.
        proxyReq.removeHeader('cookie');
        proxyReq.removeHeader('authorization');
        if (req.url.startsWith('/api/v1/')) {
          proxyReq.setHeader('Authorization', `Bearer ${token}`);
        }
      },
      onProxyRes(proxyRes) {
        delete proxyRes.headers['set-cookie'];
        delete proxyRes.headers['access-control-allow-origin'];
        delete proxyRes.headers['access-control-allow-credentials'];
        proxyRes.headers['cache-control'] = 'no-store';
      },
      onError(_error, _req, res) {
        res.writeHead(502, {'Content-Type': 'application/json'});
        res.end(
          JSON.stringify({message: 'Unable to reach the hosted Quay.io API.'}),
        );
      },
    },
  };
}

module.exports = {createHostedQuay};
