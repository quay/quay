/**
 * Shared fetch-with-retry helper for Playwright global-setup network calls.
 *
 * Retries 3 times with 500ms/1000ms backoff between attempts, applies a
 * per-attempt timeout via AbortSignal.timeout, and logs each failed attempt
 * (including err.cause when present). Both a thrown fetch error and a
 * non-ok response count as a failed attempt. `fetchJsonWithRetry` parses
 * the response body inside the same per-attempt try as the fetch itself, so
 * a truncated or malformed 200 body also counts as a failed attempt and is
 * retried with the normal backoff, and is logged like any other failed
 * attempt.
 *
 * On final failure it throws a single error naming the call site and
 * attempt count, with `cause` set to the last error and `receivedResponse`
 * set to true if any attempt received a non-ok HTTP response, or an ok
 * response whose body failed to parse — callers that need to distinguish
 * "server answered but errored" from "never reached the server" (e.g.
 * DNS/connect failure) can check that flag.
 *
 * The per-attempt AbortSignal.timeout always replaces `init.signal`; no
 * caller passes one today, so this is latent, not broken.
 */

const ATTEMPTS = 3;
const BACKOFF_MS = [500, 1000];
const DEFAULT_TIMEOUT_MS = 5000;

export interface FetchRetryExhaustedError extends Error {
  cause: unknown;
  receivedResponse: boolean;
}

async function fetchWithRetryInternal<T>(
  callSite: string,
  url: string,
  init: RequestInit | undefined,
  timeoutMs: number,
  handleResponse: (response: Response) => Promise<T>,
): Promise<T> {
  let lastError: unknown;
  let receivedResponse = false;

  for (let attemptNum = 1; attemptNum <= ATTEMPTS; attemptNum++) {
    try {
      const response = await fetch(url, {
        ...init,
        signal: AbortSignal.timeout(timeoutMs),
      });

      if (response.ok) {
        try {
          return await handleResponse(response);
        } catch (parseErr) {
          receivedResponse = true;
          lastError = parseErr;
        }
      } else {
        receivedResponse = true;
        lastError = new Error(`${callSite}: HTTP ${response.status}`);
      }
    } catch (err) {
      lastError = err;
    }

    const cause =
      lastError instanceof Error && 'cause' in lastError
        ? lastError.cause
        : undefined;
    console.error(
      `${callSite} attempt ${attemptNum}/${ATTEMPTS} failed:`,
      lastError,
      cause !== undefined ? `cause: ${cause}` : '',
    );

    if (attemptNum < ATTEMPTS) {
      await new Promise((r) => setTimeout(r, BACKOFF_MS[attemptNum - 1]));
    }
  }

  const exhaustedError = new Error(
    `${callSite} exhausted ${ATTEMPTS} attempts`,
  ) as FetchRetryExhaustedError;
  exhaustedError.cause = lastError;
  exhaustedError.receivedResponse = receivedResponse;
  throw exhaustedError;
}

export async function fetchWithRetry(
  callSite: string,
  url: string,
  init?: RequestInit,
  timeoutMs = DEFAULT_TIMEOUT_MS,
): Promise<Response> {
  return fetchWithRetryInternal(
    callSite,
    url,
    init,
    timeoutMs,
    async (response) => response,
  );
}

export async function fetchJsonWithRetry<T>(
  callSite: string,
  url: string,
  init?: RequestInit,
  timeoutMs = DEFAULT_TIMEOUT_MS,
): Promise<T> {
  return fetchWithRetryInternal(
    callSite,
    url,
    init,
    timeoutMs,
    (response) => response.json() as Promise<T>,
  );
}
