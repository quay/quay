import {render, screen} from 'src/test-utils';
import {GlobalMessages} from './GlobalMessages';

vi.mock('src/hooks/UseGlobalMessages', () => ({
  useGlobalMessages: vi.fn(),
}));

import {useGlobalMessages} from 'src/hooks/UseGlobalMessages';

const mockUseGlobalMessages = useGlobalMessages as ReturnType<typeof vi.fn>;

describe('GlobalMessages', () => {
  it('renders nothing while loading', () => {
    mockUseGlobalMessages.mockReturnValue({
      data: [],
      isLoading: true,
      error: null,
    });
    const {container} = render(<GlobalMessages />);
    expect(container).toBeEmptyDOMElement();
  });

  it('renders nothing when there is an error', () => {
    mockUseGlobalMessages.mockReturnValue({
      data: [],
      isLoading: false,
      error: new Error('fetch error'),
    });
    const {container} = render(<GlobalMessages />);
    expect(container).toBeEmptyDOMElement();
  });

  it('renders nothing when messages list is empty', () => {
    mockUseGlobalMessages.mockReturnValue({
      data: [],
      isLoading: false,
      error: null,
    });
    const {container} = render(<GlobalMessages />);
    expect(container).toBeEmptyDOMElement();
  });

  it('renders an info message', () => {
    mockUseGlobalMessages.mockReturnValue({
      data: [
        {
          uuid: 'msg-1',
          severity: 'info',
          media_type: 'text/plain',
          content: 'System maintenance tonight',
        },
      ],
      isLoading: false,
      error: null,
    });
    render(<GlobalMessages />);
    expect(screen.getByText('System maintenance tonight')).toBeInTheDocument();
  });

  it('renders a warning message with warning icon', () => {
    mockUseGlobalMessages.mockReturnValue({
      data: [
        {
          uuid: 'msg-2',
          severity: 'warning',
          media_type: 'text/plain',
          content: 'Service degraded',
        },
      ],
      isLoading: false,
      error: null,
    });
    render(<GlobalMessages />);
    expect(screen.getByText('Service degraded')).toBeInTheDocument();
  });

  it('renders multiple messages', () => {
    mockUseGlobalMessages.mockReturnValue({
      data: [
        {
          uuid: 'a',
          severity: 'info',
          media_type: 'text/plain',
          content: 'Info message',
        },
        {
          uuid: 'b',
          severity: 'error',
          media_type: 'text/plain',
          content: 'Error message',
        },
      ],
      isLoading: false,
      error: null,
    });
    render(<GlobalMessages />);
    expect(screen.getByText('Info message')).toBeInTheDocument();
    expect(screen.getByText('Error message')).toBeInTheDocument();
  });

  it('renders markdown content for text/markdown messages', () => {
    mockUseGlobalMessages.mockReturnValue({
      data: [
        {
          uuid: 'md-1',
          severity: 'info',
          media_type: 'text/markdown',
          content: '**Bold text**',
        },
      ],
      isLoading: false,
      error: null,
    });
    render(<GlobalMessages />);
    expect(screen.getByText('Bold text')).toBeInTheDocument();
  });
});
