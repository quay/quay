import {render, screen} from 'src/test-utils';
import ManifestDigest from './ManifestDigest';

describe('ManifestDigest', () => {
  it('renders the algorithm as a label', () => {
    render(<ManifestDigest digest="sha256:abc123def456789012345678" />);
    expect(screen.getByText('sha256')).toBeInTheDocument();
  });

  it('renders the first 14 characters of the hash', () => {
    render(<ManifestDigest digest="sha256:abc123def456789012345678" />);
    expect(screen.getByText('abc123def45678')).toBeInTheDocument();
  });

  it('does not render the full hash', () => {
    render(<ManifestDigest digest="sha256:abc123def456789012345678" />);
    expect(
      screen.queryByText('abc123def456789012345678'),
    ).not.toBeInTheDocument();
  });
});
