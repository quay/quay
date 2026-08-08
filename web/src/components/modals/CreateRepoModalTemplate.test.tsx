import {render, screen, userEvent, waitFor} from 'src/test-utils';
import CreateRepoModalTemplate from './CreateRepoModalTemplate';
import {useCreateRepository} from 'src/hooks/UseCreateRepository';
import {useQuayConfig} from 'src/hooks/UseQuayConfig';

vi.mock('src/hooks/UseCreateRepository', () => ({
  useCreateRepository: vi.fn(),
}));

vi.mock('src/hooks/UseQuayConfig', () => ({
  useQuayConfig: vi.fn(),
}));

const mockUseCreateRepository = vi.mocked(useCreateRepository);
const mockUseQuayConfig = vi.mocked(useQuayConfig);

function makeProps(overrides = {}) {
  return {
    isModalOpen: true,
    handleModalToggle: vi.fn(),
    orgName: null as string | null,
    updateListHandler: vi.fn(),
    username: 'testuser',
    organizations: [{name: 'org1'}, {name: 'org2'}] as any[],
    ...overrides,
  };
}

beforeEach(() => {
  mockUseCreateRepository.mockReturnValue({
    createRepository: vi.fn().mockResolvedValue({}),
  } as any);
  mockUseQuayConfig.mockReturnValue({
    features: {EXTENDED_REPOSITORY_NAMES: false},
    config: {},
  } as any);
});

describe('CreateRepoModalTemplate', () => {
  it('returns null when isModalOpen is false', () => {
    const {container} = render(
      <CreateRepoModalTemplate {...makeProps({isModalOpen: false})} />,
    );
    expect(screen.queryByText('Create repository')).not.toBeInTheDocument();
  });

  it('renders form with namespace dropdown and repo name input', () => {
    render(<CreateRepoModalTemplate {...makeProps()} />);
    expect(screen.getByText('Create repository')).toBeInTheDocument();
    expect(screen.getByTestId('repository-name-input')).toBeInTheDocument();
    expect(
      screen.getByTestId('repository-description-input'),
    ).toBeInTheDocument();
  });

  it('defaults to username when no orgName provided', () => {
    render(<CreateRepoModalTemplate {...makeProps()} />);
    expect(screen.getByTestId('selected-namespace-dropdown')).toHaveTextContent(
      'testuser',
    );
  });

  it('defaults to orgName when provided', () => {
    render(<CreateRepoModalTemplate {...makeProps({orgName: 'org1'})} />);
    expect(screen.getByTestId('selected-namespace-dropdown')).toHaveTextContent(
      'org1',
    );
  });

  it('disables submit when repo name is empty', () => {
    render(<CreateRepoModalTemplate {...makeProps()} />);
    expect(screen.getByTestId('create-repository-submit-btn')).toBeDisabled();
  });

  it('validates repo name with regex', async () => {
    render(<CreateRepoModalTemplate {...makeProps()} />);
    await userEvent.type(
      screen.getByTestId('repository-name-input'),
      'INVALID_UPPER',
    );
    expect(screen.getByText(/Must contain only lowercase/)).toBeInTheDocument();
  });

  it('enables submit for valid repo name', async () => {
    render(<CreateRepoModalTemplate {...makeProps()} />);
    await userEvent.type(
      screen.getByTestId('repository-name-input'),
      'valid-repo',
    );
    expect(
      screen.getByTestId('create-repository-submit-btn'),
    ).not.toBeDisabled();
  });

  it('calls createRepository on submit', async () => {
    const createRepository = vi.fn().mockResolvedValue({});
    mockUseCreateRepository.mockReturnValue({createRepository} as any);
    render(<CreateRepoModalTemplate {...makeProps()} />);
    await userEvent.type(screen.getByTestId('repository-name-input'), 'myrepo');
    await userEvent.click(screen.getByTestId('create-repository-submit-btn'));
    await waitFor(() =>
      expect(createRepository).toHaveBeenCalledWith(
        expect.objectContaining({
          namespace: 'testuser',
          repository: 'myrepo',
          visibility: 'public',
          repo_kind: 'image',
        }),
      ),
    );
  });
});
