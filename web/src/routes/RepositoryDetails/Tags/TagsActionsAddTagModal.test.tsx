import {render, screen} from 'src/test-utils';
import {useCreateTag} from 'src/hooks/UseTags';
import AddTagModal from './TagsActionsAddTagModal';

vi.mock('src/hooks/UseTags', () => ({
  useCreateTag: vi.fn(),
}));

const mockUseCreateTag = vi.mocked(useCreateTag);

function makeProps(overrides = {}) {
  return {
    org: 'testorg',
    repo: 'testrepo',
    isOpen: true,
    manifest: 'sha256:abc123def456789012345678',
    setIsOpen: vi.fn(),
    loadTags: vi.fn(),
    ...overrides,
  };
}

describe('AddTagModal', () => {
  beforeEach(() => {
    mockUseCreateTag.mockReturnValue({
      createTag: vi.fn(),
      successCreateTag: false,
      errorCreateTag: false,
    });
  });

  it('uses a modal header for the manifest title', () => {
    render(<AddTagModal {...makeProps()} />);

    expect(
      screen.getByRole('heading', {
        name: 'Add tag to manifest sha256:abc123def456',
      }),
    ).toBeInTheDocument();
  });

  it('renders the primary create action before the link-style cancel action', () => {
    render(<AddTagModal {...makeProps()} />);

    const createButton = screen.getByRole('button', {name: 'Create tag'});
    const cancelButton = screen.getByRole('button', {name: 'Cancel'});

    expect(createButton).toHaveClass('pf-m-primary');
    expect(cancelButton).toHaveClass('pf-m-link');
    expect(
      createButton.compareDocumentPosition(cancelButton) &
        Node.DOCUMENT_POSITION_FOLLOWING,
    ).toBe(Node.DOCUMENT_POSITION_FOLLOWING);
  });
});
