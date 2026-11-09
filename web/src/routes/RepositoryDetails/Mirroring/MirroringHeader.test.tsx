import {render, screen} from '@testing-library/react';
import {MemoryRouter} from 'react-router-dom';
import {MirroringHeader} from './MirroringHeader';

function renderHeader(isConfigured: boolean) {
  return render(
    <MemoryRouter initialEntries={['/repository/myorg/myrepo?tab=mirroring']}>
      <MirroringHeader
        namespace="myorg"
        repoName="myrepo"
        isConfigured={isConfigured}
      />
    </MemoryRouter>,
  );
}

describe('MirroringHeader', () => {
  it('links the repository name to the repository page when not configured', () => {
    renderHeader(false);
    expect(screen.getByRole('link', {name: 'myorg/myrepo'})).toHaveAttribute(
      'href',
      '/repository/myorg/myrepo?tab=information',
    );
  });

  it('renders no repository link when configured', () => {
    renderHeader(true);
    expect(
      screen.queryByRole('link', {name: 'myorg/myrepo'}),
    ).not.toBeInTheDocument();
  });
});
