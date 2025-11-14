import * as React from 'react';
import {createRoot} from 'react-dom/client';
import reportWebVitals from './reportWebVitals';
import {RecoilRoot} from 'recoil';
import {QueryClient, QueryClientProvider} from '@tanstack/react-query';
import {UIProvider} from './contexts/UIContext';

// Load App after patternfly so custom CSS that overrides patternfly doesn't require !important
import App from './App';
import {AppWithFreshLogin} from './AppWithFreshLogin';

const queryClient = new QueryClient({
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
