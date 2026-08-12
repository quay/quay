import {render, screen, userEvent, waitFor} from 'src/test-utils';
import {ConfirmationModal} from './ConfirmationModal';
import {setRepositoryVisibility} from 'src/resources/RepositoryResource';

vi.mock('src/resources/RepositoryResource', () => ({
  setRepositoryVisibility: vi.fn(),
}));

const mockSetRepoVisibility = vi.mocked(setRepositoryVisibility);

function makeProps(overrides = {}) {
  return {
    title: 'Make repositories public',
    description: 'Are you sure you want to make these repositories public?',
    modalOpen: true,
    buttonText: 'Confirm',
    toggleModal: vi.fn(),
    selectedItems: ['org1/repo1', 'org1/repo2'],
    makePublic: true,
    selectAllRepos: vi.fn(),
    confirmButtonTestId: 'confirm-btn',
    ...overrides,
  };
}

beforeEach(() => {
  mockSetRepoVisibility.mockResolvedValue(undefined);
});

describe('ConfirmationModal', () => {
  it('renders title and description', () => {
    render(<ConfirmationModal {...makeProps()} />);
    expect(screen.getByText('Make repositories public')).toBeInTheDocument();
    expect(
      screen.getByText(
        'Are you sure you want to make these repositories public?',
      ),
    ).toBeInTheDocument();
  });

  it('calls handleModalConfirm when provided', async () => {
    const handleModalConfirm = vi.fn();
    render(<ConfirmationModal {...makeProps({handleModalConfirm})} />);
    await userEvent.click(screen.getByTestId('confirm-btn'));
    expect(handleModalConfirm).toHaveBeenCalled();
  });

  it('changes visibility for selected items when no handleModalConfirm', async () => {
    render(<ConfirmationModal {...makeProps()} />);
    await userEvent.click(screen.getByTestId('confirm-btn'));
    await waitFor(() => {
      expect(mockSetRepoVisibility).toHaveBeenCalledWith(
        'org1',
        'repo1',
        'public',
      );
      expect(mockSetRepoVisibility).toHaveBeenCalledWith(
        'org1',
        'repo2',
        'public',
      );
    });
  });
});
