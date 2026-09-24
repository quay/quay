import {render, screen} from 'src/test-utils';
import AddTagModal from './TagsActionsAddTagModal';
import {createHash} from 'crypto';
import {fireEvent} from '@testing-library/react';

export const genSha256 = (input: string): string => {
  const hash = createHash('sha256').update(input).digest('hex');
  return `sha256:${hash}`;
};

const mockCreateTag = vi.fn();

vi.mock('src/hooks/UseTags', () => ({
  useCreateTag: () => ({
    createTag: mockCreateTag,
    successCreateTag: false,
    errorCreateTag: false,
  }),
}));

function makeProps(overrides = {}) {
  return {
    org: 'org-test-tag-creation',
    repo: 'repo-with-tags',
    isOpen: true,
    manifest: genSha256('random string'),
    setIsOpen: vi.fn(),
    loadTags: vi.fn(),
    ...overrides,
  };
}

const errorMessage = `Must start with a letter, digit or underscore. Only letters, digits, underscores, hyphens and periods allowed. Max 128 characters.`;

describe('AddTagModal', () => {
  beforeEach(() => {
    mockCreateTag.mockClear();
  });

  it('renders the modal dialog', () => {
    render(<AddTagModal {...makeProps()} />);
    expect(
      screen.getByRole('dialog', {name: 'Add tag modal'}),
    ).toBeInTheDocument();
  });

  it('verifies that create tag button is disabled when input is empty', () => {
    render(<AddTagModal {...makeProps()} />);
    const createButton = screen.getByRole('button', {name: 'Create tag'});

    expect(createButton).toBeDisabled();
  });

  it('verifies that create tag button is enabled if proper input is set', () => {
    render(<AddTagModal {...makeProps()} />);
    const createButton = screen.getByRole('button', {name: 'Create tag'});
    const tagInput = screen.getByRole('textbox', {name: 'new tag name'});

    fireEvent.change(tagInput, {target: {value: 'propertag-123'}});
    expect(screen.queryByText(errorMessage)).not.toBeInTheDocument();
    expect(createButton).toBeEnabled();
  });

  it('verifies that create tag button is disabled if improper tag is set', () => {
    render(<AddTagModal {...makeProps()} />);
    const createButton = screen.getByRole('button', {name: 'Create tag'});
    const tagInput = screen.getByRole('textbox', {name: 'new tag name'});

    fireEvent.change(tagInput, {target: {value: '*$%&improper-tag123_'}});
    expect(screen.getByText(errorMessage)).toBeInTheDocument();
    expect(createButton).toBeDisabled();
  });

  it('verifies that create tag button is not enabled if tag name is too long', () => {
    render(<AddTagModal {...makeProps()} />);
    const createButton = screen.getByRole('button', {name: 'Create tag'});
    const tagInput = screen.getByRole('textbox', {name: 'new tag name'});

    fireEvent.change(tagInput, {target: {value: 'a'.repeat(129)}});
    expect(screen.getByText(errorMessage)).toBeInTheDocument();
    expect(createButton).toBeDisabled();
  });

  it('verifies that create tag button is enabled if tag length is exactly 128 characters', () => {
    render(<AddTagModal {...makeProps()} />);
    const createButton = screen.getByRole('button', {name: 'Create tag'});
    const tagInput = screen.getByRole('textbox', {name: 'new tag name'});

    fireEvent.change(tagInput, {target: {value: 'b'.repeat(128)}});
    expect(screen.queryByText(errorMessage)).not.toBeInTheDocument();
    expect(createButton).toBeEnabled();
  });

  it('verifies that the error helper gets removed when tag name is corrected', () => {
    render(<AddTagModal {...makeProps()} />);
    const createButton = screen.getByRole('button', {name: 'Create tag'});
    const tagInput = screen.getByRole('textbox', {name: 'new tag name'});

    // fill tag name with improper tag
    fireEvent.change(tagInput, {target: {value: '*!"#asdfgh123'}});

    // verify that the helper text is present
    expect(screen.getByText(errorMessage)).toBeInTheDocument();
    expect(createButton).toBeDisabled();

    // now replace the tag name with a proper tag
    fireEvent.change(tagInput, {target: {value: 'abcd1234'}});

    // verify that the message is removed and the button is enabled
    expect(screen.queryByText(errorMessage)).not.toBeInTheDocument();
    expect(createButton).toBeEnabled();
  });

  it('calls createTag with correct tag name and manifest when Create tag button is clicked', () => {
    render(<AddTagModal {...makeProps()} />);
    const createButton = screen.getByRole('button', {name: 'Create tag'});
    const tagInput = screen.getByRole('textbox', {name: 'new tag name'});

    // set proper tag
    fireEvent.change(tagInput, {target: {value: 'abcd1234'}});
    expect(screen.queryByText(errorMessage)).not.toBeInTheDocument();
    expect(createButton).toBeEnabled();

    // send the request
    createButton.click();

    expect(mockCreateTag).toHaveBeenCalledWith({
      tag: 'abcd1234',
      manifest: makeProps().manifest,
    });
  });
});
