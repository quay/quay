/**
 * Shared fetch-with-retry helper for Playwright global-setup network calls.
 *
 * Retries 3 times with 500ms/1000ms backoff between attempts, applies a
 * per-attempt timeout via AbortSignal.timeout, and logs each failed attempt
 * (including err.cause when present). A thrown fetch error (network
 * failure, AbortSignal timeout), any 5xx response, 408, and 429 count as
 * failed attempts and are retried. Any other non-ok status (403, 404, 400,
 * ...) is not retryable: the loop stops immediately and throws.
 * `fetchJsonWithRetry` parses the response body inside the same per-attempt
 * try as the fetch itself, so a truncated or malformed 200 body also counts
 * as a failed attempt and is retried with the normal backoff.
 *
 * On failure (fast-fail or exhaustion) it throws a single
 * FetchRetryExhaustedError naming the call site, with `cause` set to the
 * last error and `receivedResponse` set to true if any attempt received an
 * HTTP response (including one whose body failed to parse) — callers that
 * need to distinguish "server answered but errored" from "never reached the
 * server" (e.g. DNS/connect failure) can check that flag.
 *
 * The per-attempt AbortSignal.timeout always replaces `init.signal`; no
 * caller passes one today, so this is latent, not broken.
 *
 * The backoff schedule between attempts defaults to BACKOFF_MS but can be
 * overridden per call (e.g. a boot-wait caller that needs a longer window
 * than a steady-state health probe).
 */

const ATTEMPTS = 3;
const BACKOFF_MS = [500, 1000];
const DEFAULT_TIMEOUT_MS = 5000;

export interface FetchRetryExhaustedError extends Error {
  cause: unknown;
  receivedResponse: boolean;
}

function isRetryableStatus(status: number): boolean {
  return status === 408 || status === 429 || (status >= 500 && status <= 599);
}

function toFetchRetryError(
  message: string,
  cause: unknown,
  receivedResponse: boolean,
): FetchRetryExhaustedError {
  const error = new Error(message) as FetchRetryExhaustedError;
  error.cause = cause;
  error.receivedResponse = receivedResponse;
  return error;
}

async function fetchWithRetryInternal<T>(
  callSite: string,
  url: string,
  init: RequestInit | undefined,
  timeoutMs: number,
  handleResponse: (response: Response) => Promise<T>,
  backoffMs: number[] = BACKOFF_MS,
): Promise<T> {
  let lastError: unknown;
  let receivedResponse = false;

  for (let attempt = 1; attempt <= ATTEMPTS; attempt++) {
    let nonRetryable = false;

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
        nonRetryable = !isRetryableStatus(response.status);
      }
    } catch (err) {
      lastError = err;
    }

    const cause =
      lastError instanceof Error && 'cause' in lastError
        ? lastError.cause
        : undefined;

    if (nonRetryable) {
      console.error(
        `${callSite} failed with non-retryable status:`,
        lastError,
        cause !== undefined ? `cause: ${cause}` : '',
      );
      throw toFetchRetryError(
        `${(lastError as Error).message} is not retryable`,
        lastError,
        true,
      );
    }

    console.error(
      `${callSite} attempt ${attempt}/${ATTEMPTS} failed:`,
      lastError,
      cause !== undefined ? `cause: ${cause}` : '',
    );

    if (attempt < ATTEMPTS) {
      await new Promise((r) => setTimeout(r, backoffMs[attempt - 1]));
    }
  }

  throw toFetchRetryError(
    `${callSite} exhausted ${ATTEMPTS} attempts`,
    lastError,
    receivedResponse,
  );
}

export async function fetchWithRetry(
  callSite: string,
  url: string,
  init?: RequestInit,
  timeoutMs = DEFAULT_TIMEOUT_MS,
  backoffMs: number[] = BACKOFF_MS,
): Promise<Response> {
  return fetchWithRetryInternal(
    callSite,
    url,
    init,
    timeoutMs,
    async (response) => response,
    backoffMs,
  );
}

export async function fetchJsonWithRetry<T>(
  callSite: string,
  url: string,
  init?: RequestInit,
  timeoutMs = DEFAULT_TIMEOUT_MS,
  backoffMs: number[] = BACKOFF_MS,
): Promise<T> {
  return fetchWithRetryInternal(
    callSite,
    url,
    init,
    timeoutMs,
    (response) => response.json() as Promise<T>,
    backoffMs,
  );
}
