import {render, screen} from 'src/test-utils';
import {QuayFooter} from './QuayFooter';

vi.mock('src/hooks/UseQuayConfig', () => ({
  useQuayConfig: vi.fn(),
}));

vi.mock('./ServiceStatus', () => ({
  ServiceStatus: () => <span>Service status</span>,
}));

import {useQuayConfig} from 'src/hooks/UseQuayConfig';

const mockUseQuayConfig = vi.mocked(useQuayConfig);

describe('QuayFooter', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  it('does not render documentation or version information after it moves to Help', () => {
    mockUseQuayConfig.mockReturnValue({
      config: {
        DOCUMENTATION_ROOT: 'https://docs.example.test/quay',
        FOOTER_LINKS: {
          TERMS_OF_SERVICE_URL: 'https://example.test/terms',
        },
      },
      features: {},
      version_number: '3.17.9-nightly',
    } as ReturnType<typeof useQuayConfig>);

    render(<QuayFooter />);

    expect(screen.getByText('Terms of Service')).toBeInTheDocument();
    expect(screen.queryByText('Documentation')).not.toBeInTheDocument();
    expect(screen.queryByText('3.17.9-nightly')).not.toBeInTheDocument();
  });

  it('does not render an empty footer when only documentation and version are configured', () => {
    mockUseQuayConfig.mockReturnValue({
      config: {DOCUMENTATION_ROOT: 'https://docs.example.test/quay'},
      features: {},
      version_number: '3.17.9-nightly',
    } as ReturnType<typeof useQuayConfig>);

    const {container} = render(<QuayFooter />);

    expect(container).toBeEmptyDOMElement();
  });
});
