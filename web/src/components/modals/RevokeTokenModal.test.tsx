import {render, screen, userEvent, waitFor} from 'src/test-utils';
import RevokeTokenModal from './RevokeTokenModal';
import {useRevokeApplicationToken} from 'src/hooks/UseApplicationTokens';

vi.mock('src/hooks/UseApplicationTokens', () => ({
  useRevokeApplicationToken: vi.fn(),
}));

const mockUseRevokeApplicationToken = vi.mocked(useRevokeApplicationToken);

function makeProps(overrides = {}) {
  return {
    isOpen: true,
    onClose: vi.fn(),
    token: {uuid: 'token-uuid-123', title: 'My App Token'} as any,
    ...overrides,
  };
}

beforeEach(() => {
  mockUseRevokeApplicationToken.mockReturnValue({
    mutateAsync: vi.fn().mockResolvedValue({}),
    isLoading: false,
  } as any);
});

describe('RevokeTokenModal', () => {
  it('renders warning and token title', () => {
    render(<RevokeTokenModal {...makeProps()} />);
    expect(screen.getByText('Revoke Application Token')).toBeInTheDocument();
    expect(screen.getByText(/My App Token/)).toBeInTheDocument();
    expect(screen.getByText(/cannot be undone/)).toBeInTheDocument();
  });

  it('returns null when token is null', () => {
    const {container} = render(
      <RevokeTokenModal {...makeProps({token: null})} />,
    );
    expect(
      screen.queryByText('Revoke Application Token'),
    ).not.toBeInTheDocument();
  });

  it('calls mutateAsync with token uuid on confirm', async () => {
    const mutateAsync = vi.fn().mockResolvedValue({});
    mockUseRevokeApplicationToken.mockReturnValue({
      mutateAsync,
      isLoading: false,
    } as any);
    render(<RevokeTokenModal {...makeProps()} />);
    await userEvent.click(screen.getByTestId('revoke-token-confirm'));
    await waitFor(() =>
      expect(mutateAsync).toHaveBeenCalledWith('token-uuid-123'),
    );
  });
});
