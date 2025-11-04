import * as React from 'react';
import {createRoot} from 'react-dom/client';
import reportWebVitals from './reportWebVitals';
import {RecoilRoot} from 'recoil';
import {
  QueryClient,
  QueryClientProvider,
  QueryCache,
} from '@tanstack/react-query';
import {UIProvider} from './contexts/UIContext';
import {AxiosError} from 'axios';

// Load App after patternfly so custom CSS that overrides patternfly doesn't require !important
import App from './App';
import {AppWithFreshLogin} from './AppWithFreshLogin';

const queryClient = new QueryClient({
  queryCache: new QueryCache({
    onError: (error) => {
      // Check if this is a fresh login required error
      const axiosError = error as AxiosError;
      if (axiosError?.response?.status === 401) {
        const data = axiosError.response?.data as Record<string, unknown>;
        const isFreshLoginRequired =
          data?.title === 'fresh_login_required' ||
          data?.error_type === 'fresh_login_required';

        if (isFreshLoginRequired) {
          // Trigger fresh login modal via custom event
          window.dispatchEvent(new CustomEvent('freshLoginRequired'));
        }
      }
    },
  }),
  defaultOptions: {
    queries: {
      retry: false,
      refetchOnWindowFocus: false,
    },
  },
});

const container = document.getElementById('root');
const root = createRoot(container);

root.render(
  <React.StrictMode>
    <RecoilRoot>
      <UIProvider>
        <QueryClientProvider client={queryClient}>
          <AppWithFreshLogin>
            <App />
          </AppWithFreshLogin>
        </QueryClientProvider>
      </UIProvider>
    </RecoilRoot>
  </React.StrictMode>,
);

// If you want to start measuring performance in your app, pass a function
// to log results (for example: reportWebVitals(console.log))
// or send to an analytics endpoint. Learn more: https://bit.ly/CRA-vitals
reportWebVitals();
