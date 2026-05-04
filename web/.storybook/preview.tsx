import React from 'react';
import type {Preview} from '@storybook/react';
import {RecoilRoot} from 'recoil';
import {UIProvider} from 'src/contexts/UIContext';
import {QueryClient, QueryClientProvider} from '@tanstack/react-query';
import {ThemeProvider, ThemePreference} from 'src/contexts/ThemeContext';
import {MemoryRouter} from 'react-router-dom';
import '@patternfly/patternfly/patternfly.css';

const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      retry: false,
      gcTime: 0,
    },
  },
});

const preview: Preview = {
  globalTypes: {
    theme: {
      description: 'PatternFly theme',
      toolbar: {
        title: 'Theme',
        icon: 'circlehollow',
        items: [
          {value: ThemePreference.LIGHT, title: 'Light'},
          {value: ThemePreference.DARK, title: 'Dark'},
        ],
        dynamicTitle: true,
      },
    },
  },
  initialGlobals: {
    theme: ThemePreference.LIGHT,
  },
  decorators: [
    (Story, context) => {
      const theme = context.globals.theme || ThemePreference.LIGHT;
      document.documentElement.classList.toggle(
        'pf-v6-theme-dark',
        theme === ThemePreference.DARK,
      );
      return (
        <RecoilRoot>
          <UIProvider>
            <QueryClientProvider client={queryClient}>
              <ThemeProvider>
                <MemoryRouter>
                  <Story />
                </MemoryRouter>
              </ThemeProvider>
            </QueryClientProvider>
          </UIProvider>
        </RecoilRoot>
      );
    },
  ],
};

export default preview;
