import {renderHook} from '@testing-library/react';
import React from 'react';
import {QueryClientProvider} from '@tanstack/react-query';
import {MemoryRouter} from 'react-router-dom';
import {createTestQueryClient} from 'src/test-utils';
import {useCreateAccount} from './UseCreateAccount';

vi.mock('src/resources/UserResource', () => ({
  createUser: vi.fn(),
  fetchUser: vi.fn(),
}));

vi.mock('src/resources/AuthResource', () => ({
  loginUser: vi.fn(),
  GlobalAuthState: {csrfToken: null, isLoggedIn: false},
  getCsrfToken: vi.fn(),
}));

vi.mock('src/resources/ErrorHandling', () => ({
  addDisplayError: vi.fn((msg: string) => msg),
}));

function wrapper({children}: {children: React.ReactNode}) {
  const [queryClient] = React.useState(() => createTestQueryClient());
  return React.createElement(
    MemoryRouter,
    null,
    React.createElement(QueryClientProvider, {client: queryClient}, children),
  );
}

describe('useCreateAccount', () => {
  it('returns initial state', () => {
    const {result} = renderHook(() => useCreateAccount(), {wrapper});
    expect(result.current.isLoading).toBe(false);
    expect(result.current.error).toBeNull();
    expect(typeof result.current.createAccountWithAutoLogin).toBe('function');
    expect(typeof result.current.setError).toBe('function');
  });
});
