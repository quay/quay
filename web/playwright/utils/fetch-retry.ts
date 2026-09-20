/**
 * Shared fetch-with-retry helper for Playwright global-setup network calls.
 *
 * Retries 3 times with 500ms/1000ms backoff between attempts, applies a
 * per-attempt timeout via AbortSignal.timeout, and logs each failed attempt
 * (including err.cause when present). Both a thrown fetch error and a
 * non-ok response count as a failed attempt. On final failure it throws a
 * single error naming the call site and attempt count, with `cause` set to
 * the last error and `receivedResponse` set to true if any attempt received
 * a non-ok HTTP response — callers that need to distinguish "server
 * answered but errored" from "never reached the server" (e.g. DNS/connect
 * failure) can check that flag.
 *
 * The per-attempt AbortSignal.timeout always replaces `init.signal`; no
 * caller passes one today, so this is latent, not broken. Callers that
 * read the response body (e.g. `.json()`) do so after this function
 * returns, outside the attempt's timeout window — a slow or truncated
 * body will not be retried.
 */

const ATTEMPTS = 3;
const BACKOFF_MS = [500, 1000];
const DEFAULT_TIMEOUT_MS = 5000;

export interface FetchRetryExhaustedError extends Error {
  cause: unknown;
  receivedResponse: boolean;
}

export async function fetchWithRetry(
  callSite: string,
  url: string,
  init?: RequestInit,
  timeoutMs = DEFAULT_TIMEOUT_MS,
): Promise<Response> {
  let lastError: unknown;
  let receivedResponse = false;

  for (let attempt = 1; attempt <= ATTEMPTS; attempt++) {
    try {
      const response = await fetch(url, {
        ...init,
        signal: AbortSignal.timeout(timeoutMs),
      });
      if (response.ok) {
        return response;
      }
      receivedResponse = true;
      lastError = new Error(`${callSite}: HTTP ${response.status}`);
    } catch (err) {
      lastError = err;
    }

    const cause =
      lastError instanceof Error && 'cause' in lastError
        ? lastError.cause
        : undefined;
    console.error(
      `${callSite} attempt ${attempt}/${ATTEMPTS} failed:`,
      lastError,
      cause !== undefined ? `cause: ${cause}` : '',
    );

    if (attempt < ATTEMPTS) {
      await new Promise((r) => setTimeout(r, BACKOFF_MS[attempt - 1]));
    }
  }

  const exhaustedError = new Error(
    `${callSite} exhausted ${ATTEMPTS} attempts`,
  ) as FetchRetryExhaustedError;
  exhaustedError.cause = lastError;
  exhaustedError.receivedResponse = receivedResponse;
  throw exhaustedError;
}
