import {render, screen, userEvent, waitFor} from 'src/test-utils';
import EditableLabels from './LabelsEditable';
import {useLabels} from 'src/hooks/UseTagLabels';

vi.mock('src/hooks/UseTagLabels', () => ({
  useLabels: vi.fn(),
}));

const mockUseLabels = vi.mocked(useLabels);

function defaultHookReturn(overrides = {}) {
  return {
    labels: [],
    setLabels: vi.fn(),
    initialLabels: [],
    loading: false,
    error: false,
    createLabels: vi.fn(),
    successCreatingLabels: false,
    errorCreatingLabels: false,
    errorCreatingLabelsDetails: null,
    loadingCreateLabels: false,
    resetCreateLabels: vi.fn(),
    deleteLabels: vi.fn(),
    successDeletingLabels: false,
    errorDeletingLabels: false,
    errorDeletingLabelsDetails: null,
    loadingDeleteLabels: false,
    resetDeleteLabels: vi.fn(),
    ...overrides,
  };
}

function makeProps(overrides = {}) {
  return {
    org: 'myorg',
    repo: 'myrepo',
    digest: 'sha256:abc',
    onComplete: vi.fn(),
    ...overrides,
  };
}

beforeEach(() => {
  mockUseLabels.mockReturnValue(defaultHookReturn());
});

describe('EditableLabels', () => {
  it('renders loading skeleton when loading is true', () => {
    mockUseLabels.mockReturnValue(defaultHookReturn({loading: true}));
    const {container} = render(<EditableLabels {...makeProps()} />);
    expect(container.querySelector('.pf-v6-c-skeleton')).toBeInTheDocument();
  });

  it('renders error message when error is true', () => {
    mockUseLabels.mockReturnValue(defaultHookReturn({error: true}));
    render(<EditableLabels {...makeProps()} />);
    expect(screen.getByText('Unable to get labels')).toBeInTheDocument();
  });

  it('renders read-only labels section', () => {
    render(<EditableLabels {...makeProps()} />);
    expect(screen.getByText('Read-only labels')).toBeInTheDocument();
  });

  it('renders "No labels found" when no read-only labels', () => {
    render(<EditableLabels {...makeProps()} />);
    expect(screen.getByText('No labels found')).toBeInTheDocument();
  });

  it('displays existing read-only labels', () => {
    mockUseLabels.mockReturnValue(
      defaultHookReturn({
        labels: [
          {
            id: '1',
            key: 'env',
            value: 'prod',
            source_type: 'manifest',
            media_type: null,
          },
        ],
      }),
    );
    render(<EditableLabels {...makeProps()} />);
    expect(screen.getByText(/env = prod/)).toBeInTheDocument();
  });

  it('displays existing mutable labels', () => {
    mockUseLabels.mockReturnValue(
      defaultHookReturn({
        labels: [
          {
            id: 'k=v',
            key: 'k',
            value: 'v',
            source_type: 'api',
            media_type: null,
          },
        ],
      }),
    );
    render(<EditableLabels {...makeProps()} />);
    expect(screen.getByText(/k=v/)).toBeInTheDocument();
  });

  it('disables Save Labels button when no changes made', () => {
    render(<EditableLabels {...makeProps()} />);
    expect(screen.getByRole('button', {name: /save labels/i})).toBeDisabled();
  });

  it('calls onComplete when Cancel is clicked', async () => {
    const onComplete = vi.fn();
    render(<EditableLabels {...makeProps({onComplete})} />);
    await userEvent.click(screen.getByRole('button', {name: /cancel/i}));
    expect(onComplete).toHaveBeenCalled();
  });
});
