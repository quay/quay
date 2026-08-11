import {AxiosError} from 'axios';

// Collects multiple error responses from a bulk operation
// with error response being mapped to some key
export class BulkOperationError<T> extends Error {
  responses: Map<string, T>;
  constructor(message: string) {
    super(message);
    this.responses = new Map<string, T>();
    Object.setPrototypeOf(this, BulkOperationError.prototype);
  }
  addError(key: string, error: T) {
    this.responses.set(key, error);
  }
  getErrors() {
    return this.responses;
  }
}

export class ResourceError extends Error {
  error: Error;
  resource: string;
  constructor(message: string, resource: string, error: AxiosError) {
    super(message);
    this.resource = resource;
    this.error = error;
    Object.setPrototypeOf(this, ResourceError.prototype);
  }
}

export function throwIfError(
  responses: PromiseSettledResult<void>[],
  message?: string,
) {
  // Aggregate failed responses
  const errResponses = responses.filter(
    (r) => r.status == 'rejected',
  ) as PromiseRejectedResult[];

  // If errors, collect and throw
  if (errResponses.length > 0) {
    const bulkDeleteError = new BulkOperationError<ResourceError>(message);
    for (const response of errResponses) {
      const reason = response.reason as ResourceError;
      bulkDeleteError.addError(reason.resource, reason);
    }
    throw bulkDeleteError;
  }
}

// Convert error to human readble output
export function addDisplayError(message: string, error: Error | AxiosError) {
  const errorDetails =
    error instanceof AxiosError ? getErrorMessage(error) : error.message;
  return message + ', ' + errorDetails + '.';
}

interface ErrorResponse {
  detail?: string; // Standard API error field (checked first)
  error_message?: string; // Standard error message field
  message?: string; // Legacy error format (backward compatibility)
  error_description?: string; // OAuth/OpenID error format
}

// Only handling the codes related to network errors. HTTP based errors
// will be read from error.response.status. Axios codes left out of list:
// ERR_BAD_OPTION_VALUE
// ERR_BAD_OPTION
// ERR_BAD_RESPONSE
// ERR_BAD_REQUEST
// ERR_DEPRECATED
enum AxiosErrorCode {
  ERR_FR_TOO_MANY_REDIRECTS = 'ERR_FR_TOO_MANY_REDIRECTS',
  ERR_NETWORK = 'ERR_NETWORK',
  ERR_CANCELED = 'ERR_CANCELED',
  ECONNABORTED = 'ECONNABORTED',
  ETIMEDOUT = 'ETIMEDOUT',
}

export function getErrorMessage(error: AxiosError<ErrorResponse>) {
  // PRIORITY 1: Check if server sent a response
  if (error.response) {
    // Check all possible error message fields in priority order
    const serverMessage =
      error.response.data?.detail ||
      error.response.data?.error_message ||
      error.response.data?.message ||
      error.response.data?.error_description ||
      (typeof error.response.data === 'string' ? error.response.data : null);

    // For 5xx errors, ALWAYS return generic message for security
    // This runs even if response body is empty
    if (
      error.response.status &&
      error.response.status >= 500 &&
      error.response.status < 600
    ) {
      return 'an unexpected issue occurred. Please try again or contact support';
    }

    // For 4xx and other status codes, return specific message if available
    if (serverMessage) {
      return serverMessage;
    }
  }

  // PRIORITY 2: Check for network-level errors (no response from server)
  // Only use network error codes when there's truly NO response from server
  if (
    !error.response &&
    error.code &&
    Object.values(AxiosErrorCode).includes(error.code as AxiosErrorCode)
  ) {
    return getNetworkError(error.code as AxiosErrorCode);
  }

  // PRIORITY 3: Generic fallback
  return 'unable to make request';
}

function getNetworkError(code: AxiosErrorCode) {
  switch (code) {
    case AxiosErrorCode.ERR_FR_TOO_MANY_REDIRECTS:
      return 'too many redirects';
    case AxiosErrorCode.ERR_NETWORK:
      return 'connection cannot be made';
    case AxiosErrorCode.ERR_CANCELED:
      return 'request cancelled';
    case AxiosErrorCode.ECONNABORTED:
      return 'connection aborted';
    case AxiosErrorCode.ETIMEDOUT:
      return 'connection timed out';
  }
}

export function assertHttpCode(got: number, expected: number) {
  if (expected !== got) {
    throw new Error(`Unexpected HTTP status code: ${got}`);
  }
}

export function isErrorString(err: string) {
  return typeof err === 'string' && err.length > 0;
}

// Utility function to get user-friendly error message from any error type
// Use this instead of error.message when displaying errors to users
export function getErrorMessageFromUnknown(error: unknown): string {
  if (error instanceof AxiosError) {
    return getErrorMessage(error);
  }
  if (error instanceof Error) {
    return error.message;
  }
  return String(error);
}
