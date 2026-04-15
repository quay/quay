import {AxiosError, AxiosResponse, InternalAxiosRequestConfig} from 'axios';
import {
  BulkOperationError,
  ResourceError,
  throwIfError,
  addDisplayError,
  getErrorMessage,
  assertHttpCode,
  isErrorString,
  getErrorMessageFromUnknown,
} from './ErrorHandling';

const emptyConfig = {} as InternalAxiosRequestConfig;

function createMockAxiosError(
  opts: {
    message?: string;
    code?: string;
    status?: number;
    data?: unknown;
  } = {},
): AxiosError {
  const {message = 'Request failed', code, status, data} = opts;

  const response =
    status != null
      ? ({
          status,
          data: data ?? {},
          statusText: '',
          headers: {},
          config: emptyConfig,
        } as AxiosResponse)
      : undefined;

  return new AxiosError(message, code, emptyConfig, {}, response);
}

describe('BulkOperationError', () => {
  it('is an instance of Error with correct message', () => {
    const err = new BulkOperationError('bulk failed');
    expect(err).toBeInstanceOf(Error);
    expect(err).toBeInstanceOf(BulkOperationError);
    expect(err.message).toBe('bulk failed');
  });

  it('starts with an empty responses map', () => {
    const err = new BulkOperationError('test');
    expect(err.getErrors()).toBeInstanceOf(Map);
    expect(err.getErrors().size).toBe(0);
  });

  it('addError/getErrors stores and retrieves key-value pairs', () => {
    const err = new BulkOperationError<string>('test');
    err.addError('key1', 'val1');
    err.addError('key2', 'val2');
    const errors = err.getErrors();
    expect(errors.size).toBe(2);
    expect(errors.get('key1')).toBe('val1');
    expect(errors.get('key2')).toBe('val2');
  });
});

describe('ResourceError', () => {
  it('is an instance of Error and stores resource + error properties', () => {
    const axiosErr = createMockAxiosError({status: 500});
    const err = new ResourceError('res failed', 'myResource', axiosErr);
    expect(err).toBeInstanceOf(Error);
    expect(err).toBeInstanceOf(ResourceError);
    expect(err.message).toBe('res failed');
    expect(err.resource).toBe('myResource');
    expect(err.error).toBe(axiosErr);
  });
});

describe('throwIfError', () => {
  it('does not throw when all promises are fulfilled', () => {
    const responses: PromiseSettledResult<void>[] = [
      {status: 'fulfilled', value: undefined},
      {status: 'fulfilled', value: undefined},
    ];
    expect(() => throwIfError(responses)).not.toThrow();
  });

  it('throws BulkOperationError with collected errors when promises rejected', () => {
    const axiosErr1 = createMockAxiosError({status: 400});
    const axiosErr2 = createMockAxiosError({status: 404});
    const resErr1 = new ResourceError('fail1', 'repo1', axiosErr1);
    const resErr2 = new ResourceError('fail2', 'repo2', axiosErr2);

    const responses: PromiseSettledResult<void>[] = [
      {status: 'fulfilled', value: undefined},
      {status: 'rejected', reason: resErr1},
      {status: 'rejected', reason: resErr2},
    ];

    try {
      throwIfError(responses, 'bulk delete failed');
      expect.unreachable('should have thrown');
    } catch (e) {
      expect(e).toBeInstanceOf(BulkOperationError);
      const bulkErr = e as BulkOperationError<ResourceError>;
      expect(bulkErr.getErrors().size).toBe(2);
      expect(bulkErr.getErrors().get('repo1')).toBe(resErr1);
      expect(bulkErr.getErrors().get('repo2')).toBe(resErr2);
    }
  });
});

describe('addDisplayError', () => {
  it('formats AxiosError using getErrorMessage with comma and trailing period', () => {
    const err = createMockAxiosError({
      status: 404,
      data: {detail: 'not found'},
    });
    expect(addDisplayError('Something failed', err)).toBe(
      'Something failed, not found.',
    );
  });

  it('formats plain Error using error.message', () => {
    const err = new Error('boom');
    expect(addDisplayError('Operation failed', err)).toBe(
      'Operation failed, boom.',
    );
  });
});

describe('getErrorMessage', () => {
  it('returns generic message for 5xx even when response body has detail', () => {
    const err = createMockAxiosError({
      status: 500,
      data: {detail: 'secret db error'},
    });
    expect(getErrorMessage(err)).toBe(
      'an unexpected issue occurred. Please try again or contact support',
    );
  });

  it('returns detail field for 4xx (highest priority)', () => {
    const err = createMockAxiosError({
      status: 400,
      data: {detail: 'invalid input', error_message: 'should not use this'},
    });
    expect(getErrorMessage(err)).toBe('invalid input');
  });

  it('falls back through error_message, message, error_description, string body', () => {
    expect(
      getErrorMessage(
        createMockAxiosError({status: 400, data: {error_message: 'err msg'}}),
      ),
    ).toBe('err msg');

    expect(
      getErrorMessage(
        createMockAxiosError({status: 400, data: {message: 'legacy msg'}}),
      ),
    ).toBe('legacy msg');

    expect(
      getErrorMessage(
        createMockAxiosError({
          status: 400,
          data: {error_description: 'oauth err'},
        }),
      ),
    ).toBe('oauth err');

    expect(
      getErrorMessage(
        createMockAxiosError({status: 400, data: 'plain string body'}),
      ),
    ).toBe('plain string body');
  });

  it('returns fallback for 4xx with null data', () => {
    const err = createMockAxiosError({status: 400, data: null});
    expect(getErrorMessage(err)).toBe('unable to make request');
  });

  it('returns network error message when no response and known error code', () => {
    expect(getErrorMessage(createMockAxiosError({code: 'ERR_NETWORK'}))).toBe(
      'connection cannot be made',
    );

    expect(getErrorMessage(createMockAxiosError({code: 'ETIMEDOUT'}))).toBe(
      'connection timed out',
    );

    expect(getErrorMessage(createMockAxiosError({code: 'ERR_CANCELED'}))).toBe(
      'request cancelled',
    );

    expect(getErrorMessage(createMockAxiosError({code: 'ECONNABORTED'}))).toBe(
      'connection aborted',
    );

    expect(
      getErrorMessage(
        createMockAxiosError({code: 'ERR_FR_TOO_MANY_REDIRECTS'}),
      ),
    ).toBe('too many redirects');
  });

  it('returns fallback for unknown error shape', () => {
    const err = createMockAxiosError({});
    expect(getErrorMessage(err)).toBe('unable to make request');
  });
});

describe('assertHttpCode', () => {
  it('does not throw when codes match', () => {
    expect(() => assertHttpCode(200, 200)).not.toThrow();
  });

  it('throws with descriptive message when codes differ', () => {
    expect(() => assertHttpCode(404, 200)).toThrow(
      'Unexpected HTTP status code: 404',
    );
  });
});

describe('isErrorString', () => {
  it('returns true for non-empty string, false otherwise', () => {
    expect(isErrorString('error occurred')).toBe(true);
    expect(isErrorString('')).toBe(false);
    expect(isErrorString(null as unknown as string)).toBe(false);
    expect(isErrorString(undefined as unknown as string)).toBe(false);
  });
});

describe('getErrorMessageFromUnknown', () => {
  it('delegates to getErrorMessage for AxiosError', () => {
    const err = createMockAxiosError({
      status: 400,
      data: {detail: 'bad request'},
    });
    expect(getErrorMessageFromUnknown(err)).toBe('bad request');
  });

  it('returns message for plain Error', () => {
    expect(getErrorMessageFromUnknown(new Error('plain error'))).toBe(
      'plain error',
    );
  });

  it('returns String(value) for non-Error values', () => {
    expect(getErrorMessageFromUnknown(42)).toBe('42');
    expect(getErrorMessageFromUnknown(null)).toBe('null');
    expect(getErrorMessageFromUnknown(undefined)).toBe('undefined');
  });
});
