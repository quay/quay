import React, {ReactElement} from 'react';
import {render, RenderOptions, RenderResult} from '@testing-library/react';
import {QueryClient, QueryClientProvider} from '@tanstack/react-query';
import {RecoilRoot} from 'recoil';
import {UIProvider} from 'src/contexts/UIContext';

function createTestQueryClient(): QueryClient {
  return new QueryClient({
    defaultOptions: {
      queries: {
        retry: false,
        cacheTime: 0,
      },
      mutations: {
        retry: false,
      },
    },
    logger: {
      log: console.log,
      warn: console.warn,
      // eslint-disable-next-line @typescript-eslint/no-empty-function
      error: () => {},
    },
  });
}

interface CustomRenderOptions extends Omit<RenderOptions, 'wrapper'> {
  queryClient?: QueryClient;
}

function customRender(
  ui: ReactElement,
  options: CustomRenderOptions = {},
): RenderResult & {queryClient: QueryClient} {
  const {queryClient = createTestQueryClient(), ...renderOptions} = options;

  function Wrapper({
    children,
  }: {
    children: React.ReactNode;
  }): React.ReactElement {
    return (
      <RecoilRoot>
        <UIProvider>
          <QueryClientProvider client={queryClient}>
            {children}
          </QueryClientProvider>
        </UIProvider>
      </RecoilRoot>
    );
  }

  return {
    ...render(ui, {wrapper: Wrapper, ...renderOptions}),
    queryClient,
  };
}

export {customRender as render};
export {createTestQueryClient};
export {screen, within, waitFor} from '@testing-library/react';
export {default as userEvent} from '@testing-library/user-event';
