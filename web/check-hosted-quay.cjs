// Read-only contract check. OAuth credentials remain in this Node process.
const {createHostedQuay} = require('./hosted-quay');

async function main() {
  const token = process.env.QUAY_OAUTH_TOKEN;
  createHostedQuay({token});
  const headers = {
    'X-Requested-With': 'XMLHttpRequest',
    Authorization: `Bearer ${token}`,
  };
  async function get(path) {
    const response = await fetch(`https://quay.io${path}`, {
      headers,
      redirect: 'error',
      signal: AbortSignal.timeout(30000),
    });
    if (!response.ok) throw new Error(`GET ${path}: HTTP ${response.status}`);
    if (!response.headers.get('content-type')?.includes('application/json')) {
      throw new Error(`GET ${path}: expected JSON`);
    }
    const data = await response.json();
    console.log(`PASS GET ${path}`);
    return data;
  }
  const config = await get('/config');
  if (!config.features?.BILLING)
    throw new Error('Hosted billing is not enabled for this deployment.');
  const user = await get('/api/v1/user/');
  if (!user.username || user.anonymous)
    throw new Error('The token did not authenticate a Quay user.');
  const catalog = await get('/api/v1/plans/');
  if (!Array.isArray(catalog.plans) || !catalog.plans.length) {
    throw new Error(
      'Hosted plan catalog does not match the expected API contract.',
    );
  }
  const namespace = process.env.QUAY_HOSTED_NAMESPACE || user.username;
  if (!/^[a-zA-Z0-9_-]+$/.test(namespace))
    throw new Error('Invalid QUAY_HOSTED_NAMESPACE.');
  const prefix =
    namespace === user.username
      ? '/api/v1/user'
      : `/api/v1/organization/${namespace}`;
  const subscription = await get(`${prefix}/plan`);
  if (
    typeof subscription.hasSubscription !== 'boolean' ||
    typeof subscription.plan !== 'string'
  ) {
    throw new Error(
      'Hosted subscription does not match the expected API contract.',
    );
  }
  const card = await get(`${prefix}/card`);
  if (!Object.hasOwn(card, 'card'))
    throw new Error(
      'Hosted card response does not match the expected API contract.',
    );
  console.log(
    'Hosted billing read checks passed. No billing changes were made.',
  );
}

main().catch((error) => {
  // Do not print fetch errors, headers, or upstream response bodies.
  console.error(
    error instanceof TypeError ? 'Unable to reach Quay.io.' : error.message,
  );
  process.exitCode = 1;
});
