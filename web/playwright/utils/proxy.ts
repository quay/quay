/**
 * Proxy support for the Playwright suite.
 *
 * When Quay is only reachable through a proxy (e.g. bare-metal OpenShift CI,
 * where the cluster apps route is not directly resolvable from the test
 * runner), both the browser/API traffic (via `use.proxy` in playwright.config)
 * and the global-setup network calls must be routed through it. Node's native
 * `fetch` (undici) deliberately ignores HTTP_PROXY / HTTPS_PROXY / NO_PROXY,
 * so global-setup instead issues its requests through a Playwright
 * APIRequestContext configured with the proxy returned here.
 *
 * All helpers return undefined when no proxy env var is set, so local-dev
 * behaviour is unchanged.
 */

export interface ProxyOption {
  server: string;
  bypass?: string;
  username?: string;
  password?: string;
}

function targetSchemeIsHttps(): boolean {
  // Every proxy consumer here (browser, request contexts, config fetch) targets
  // the same Quay deployment, so one scheme determination suffices. Default
  // (no explicit target set) is http://localhost.
  const target =
    process.env.REACT_QUAY_APP_API_URL || process.env.PLAYWRIGHT_BASE_URL || '';
  return /^https:\/\//i.test(target);
}

export function proxyServerFromEnv(): string | undefined {
  // Honor the per-scheme convention: HTTPS_PROXY for https targets, HTTP_PROXY
  // for http targets, each falling back to the other when only one is set.
  if (targetSchemeIsHttps()) {
    return (
      process.env.HTTPS_PROXY ||
      process.env.https_proxy ||
      process.env.HTTP_PROXY ||
      process.env.http_proxy ||
      undefined
    );
  }
  return (
    process.env.HTTP_PROXY ||
    process.env.http_proxy ||
    process.env.HTTPS_PROXY ||
    process.env.https_proxy ||
    undefined
  );
}

export function noProxyFromEnv(): string | undefined {
  return process.env.NO_PROXY || process.env.no_proxy || undefined;
}

/**
 * Expand plain hostname bypass entries so they match the exact host AND its
 * subdomains under Chromium's --proxy-bypass-list, which otherwise treats a
 * bare "example.com" as exact-match only. Playwright's API-request bypass
 * already matches subdomains for a bare hostname, so adding the leading-dot
 * ("*." in Chromium) variant makes both paths consistent and leaves the API
 * path unchanged. Wildcards, dot-prefixed entries, IPs, host:port/IPv6, single-
 * label hosts, and the all/loopback tokens are passed through untouched.
 */
function expandBypassForSubdomains(bypass: string): string {
  const out: string[] = [];
  for (const rawEntry of bypass.split(',')) {
    const entry = rawEntry.trim();
    if (!entry) continue;
    out.push(entry);
    const isPlainHostname =
      !entry.startsWith('.') &&
      !entry.startsWith('*') &&
      entry !== '<-loopback>' &&
      !entry.includes(':') &&
      !entry.includes('/') &&
      entry.includes('.') &&
      !/^\d{1,3}(\.\d{1,3}){3}$/.test(entry);
    if (isPlainHostname) out.push(`.${entry}`);
  }
  return out.join(',');
}

/**
 * Proxy option suitable for `request.newContext({proxy})` / browser launches,
 * or undefined when no proxy env var is set.
 *
 * Credentials embedded in the proxy URL (http://user:pass@host:port) are split
 * out into Playwright's separate username/password fields — Chromium's
 * `--proxy-server` ignores credentials in the server string.
 */
export function proxyOptionFromEnv(): ProxyOption | undefined {
  const raw = proxyServerFromEnv();
  if (!raw) return undefined;

  const rawBypass = noProxyFromEnv();
  // NO_PROXY=* means bypass the proxy for every host — omit the proxy entirely
  // rather than configure one with an all-hosts bypass.
  if (rawBypass?.trim() === '*') return undefined;
  const bypass = rawBypass ? expandBypassForSubdomains(rawBypass) : undefined;
  let server = raw;
  let username: string | undefined;
  let password: string | undefined;

  // Short form like "myproxy.com:3128" has no scheme; add one so URL parses.
  const hasScheme = /^[a-z][a-z0-9+.-]*:\/\//i.test(raw);
  try {
    const url = new URL(hasScheme ? raw : `http://${raw}`);
    if (url.username || url.password) {
      username = decodeURIComponent(url.username);
      password = decodeURIComponent(url.password);
      // Rebuild server without credentials (and without a trailing path).
      server = hasScheme ? `${url.protocol}//${url.host}` : url.host;
    }
  } catch {
    // Not a parseable URL — pass the raw value through unchanged.
  }

  return {
    server,
    ...(bypass ? {bypass} : {}),
    ...(username ? {username} : {}),
    ...(password ? {password} : {}),
  };
}

/**
 * When a proxy is configured, Playwright forces Chromium to route loopback
 * (localhost) traffic through the proxy by adding `<-loopback>` to the bypass
 * list. On CI the local webserver/mailpit run on localhost and must stay
 * direct, so set PLAYWRIGHT_DISABLE_FORCED_CHROMIUM_PROXIED_LOOPBACK (unless the
 * caller already set it) before any Chromium launch. No-op without a proxy.
 */
export function applyChromiumLoopbackBypass(): void {
  if (
    proxyServerFromEnv() &&
    !process.env.PLAYWRIGHT_DISABLE_FORCED_CHROMIUM_PROXIED_LOOPBACK
  ) {
    process.env.PLAYWRIGHT_DISABLE_FORCED_CHROMIUM_PROXIED_LOOPBACK = '1';
  }
}
