import React from 'react';
import {render, screen} from 'src/test-utils';
import {SuspenseLoader} from './SuspenseLoader';

const pendingPromise = new Promise<never>(() => undefined);

const SuspendedContent: React.FC = (): React.ReactElement => {
  throw pendingPromise;
};

describe('SuspenseLoader', () => {
  beforeEach(() => {
    vi.resetAllMocks();
  });

  it('renders the loading page while its content is suspended', () => {
    render(
      <SuspenseLoader>
        <SuspendedContent />
      </SuspenseLoader>,
    );

    expect(screen.getByRole('heading', {name: 'Loading'})).toBeVisible();
  });
});
