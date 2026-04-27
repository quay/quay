import {render, screen, userEvent, waitFor} from 'src/test-utils';
import ImmutabilityPolicyForm from './ImmutabilityPolicyForm';

function makeProps(overrides = {}) {
  return {
    onSave: vi.fn(),
    policy: null,
    index: 0,
    successFetchingPolicies: true,
    ...overrides,
  };
}

describe('ImmutabilityPolicyForm', () => {
  it('renders the tag pattern text input', () => {
    render(<ImmutabilityPolicyForm {...makeProps()} />);
    expect(screen.getByTestId('immutability-tag-pattern')).toBeInTheDocument();
  });

  it('renders the pattern behavior select', () => {
    render(<ImmutabilityPolicyForm {...makeProps()} />);
    expect(
      screen.getByTestId('immutability-pattern-behavior'),
    ).toBeInTheDocument();
  });

  it('shows validation error when empty pattern is submitted', async () => {
    render(<ImmutabilityPolicyForm {...makeProps()} />);
    await userEvent.click(screen.getByTestId('save-immutability-policy-btn'));
    expect(screen.getByText('Tag pattern is required')).toBeInTheDocument();
  });

  it('shows error when pattern exceeds 256 characters', async () => {
    render(<ImmutabilityPolicyForm {...makeProps()} />);
    const input = screen.getByTestId('immutability-tag-pattern');
    await userEvent.type(input, 'a'.repeat(257));
    await userEvent.click(screen.getByTestId('save-immutability-policy-btn'));
    expect(
      screen.getByText('Tag pattern must be 256 characters or less'),
    ).toBeInTheDocument();
  });

  it('shows error for invalid regex pattern', async () => {
    render(<ImmutabilityPolicyForm {...makeProps()} />);
    const input = screen.getByTestId('immutability-tag-pattern');
    // Type an unclosed group — a regex that always fails to compile
    await userEvent.type(input, '(unclosed');
    await waitFor(() =>
      expect(
        screen.getByText('Invalid regular expression pattern'),
      ).toBeInTheDocument(),
    );
  });

  it('calls onSave with correct args for valid pattern', async () => {
    const onSave = vi.fn();
    render(<ImmutabilityPolicyForm {...makeProps({onSave})} />);
    await userEvent.type(screen.getByTestId('immutability-tag-pattern'), 'v.*');
    await userEvent.click(screen.getByTestId('save-immutability-policy-btn'));
    expect(onSave).toHaveBeenCalledWith(null, 'v.*', true);
  });

  it('shows compact view for saved policy with uuid', () => {
    render(
      <ImmutabilityPolicyForm
        {...makeProps({
          policy: {
            uuid: 'abc-123',
            tagPattern: 'v\\d+',
            tagPatternMatches: true,
          },
        })}
      />,
    );
    expect(
      screen.getByTestId('immutability-tag-pattern-display'),
    ).toBeInTheDocument();
    expect(
      screen.getByTestId('edit-immutability-policy-btn'),
    ).toBeInTheDocument();
  });

  it('switches from compact view to edit form on edit button click', async () => {
    render(
      <ImmutabilityPolicyForm
        {...makeProps({
          policy: {
            uuid: 'abc-123',
            tagPattern: 'v\\d+',
            tagPatternMatches: true,
          },
        })}
      />,
    );
    await userEvent.click(screen.getByTestId('edit-immutability-policy-btn'));
    expect(screen.getByTestId('immutability-tag-pattern')).toBeInTheDocument();
  });

  it('calls onDelete with uuid when delete button is clicked', async () => {
    const onDelete = vi.fn();
    render(
      <ImmutabilityPolicyForm
        {...makeProps({
          onDelete,
          policy: {
            uuid: 'abc-123',
            tagPattern: 'release.*',
            tagPatternMatches: false,
          },
        })}
      />,
    );
    await userEvent.click(screen.getByTestId('delete-immutability-policy-btn'));
    expect(onDelete).toHaveBeenCalledWith('abc-123');
  });

  it('shows warning alert for new (unsaved) policy', () => {
    render(<ImmutabilityPolicyForm {...makeProps()} />);
    expect(screen.getByText(/Immutability is permanent/i)).toBeInTheDocument();
  });

  it('renders inline (no card wrapper) when isInline is true', () => {
    const {container} = render(
      <ImmutabilityPolicyForm {...makeProps({isInline: true})} />,
    );
    expect(container.querySelector('.pf-v6-c-card')).not.toBeInTheDocument();
  });
});
