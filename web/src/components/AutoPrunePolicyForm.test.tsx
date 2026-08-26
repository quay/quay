import {render, screen, userEvent, waitFor} from 'src/test-utils';
import AutoPrunePolicyForm from './AutoPrunePolicyForm';
import {AutoPruneMethod} from '../resources/NamespaceAutoPruneResource';

const defaultPolicy = null;

function makeProps(overrides = {}) {
  return {
    onSave: vi.fn(),
    policy: defaultPolicy,
    index: 0,
    successFetchingPolicies: true,
    ...overrides,
  };
}

describe('AutoPrunePolicyForm', () => {
  it('renders the method select dropdown', () => {
    render(<AutoPrunePolicyForm {...makeProps()} />);
    expect(screen.getByLabelText('auto-prune-method')).toBeInTheDocument();
  });

  it('shows None method selected by default', () => {
    render(<AutoPrunePolicyForm {...makeProps()} />);
    expect(screen.getByLabelText('auto-prune-method')).toHaveValue(
      AutoPruneMethod.NONE,
    );
  });

  it('shows tag count input when Tag Number method is selected', async () => {
    render(<AutoPrunePolicyForm {...makeProps()} />);
    await userEvent.selectOptions(
      screen.getByLabelText('auto-prune-method'),
      AutoPruneMethod.TAG_NUMBER,
    );
    expect(screen.getByLabelText('number of tags')).toBeInTheDocument();
  });

  it('hides tag count input for None method', () => {
    render(<AutoPrunePolicyForm {...makeProps()} />);
    expect(screen.queryByLabelText('number of tags')).not.toBeInTheDocument();
  });

  it('shows age value + unit inputs when Tag Creation Date method is selected', async () => {
    render(<AutoPrunePolicyForm {...makeProps()} />);
    await userEvent.selectOptions(
      screen.getByLabelText('auto-prune-method'),
      AutoPruneMethod.TAG_CREATION_DATE,
    );
    expect(
      screen.getByLabelText('tag creation date value'),
    ).toBeInTheDocument();
    expect(screen.getByLabelText('tag creation date unit')).toBeInTheDocument();
  });

  it('shows tag pattern section when method is not NONE', async () => {
    render(<AutoPrunePolicyForm {...makeProps()} />);
    expect(screen.queryByLabelText('tag pattern')).not.toBeInTheDocument();
    await userEvent.selectOptions(
      screen.getByLabelText('auto-prune-method'),
      AutoPruneMethod.TAG_NUMBER,
    );
    expect(screen.getByLabelText('tag pattern')).toBeInTheDocument();
  });

  it('syncs state from TAG_NUMBER policy prop', () => {
    render(
      <AutoPrunePolicyForm
        {...makeProps({
          policy: {
            method: AutoPruneMethod.TAG_NUMBER,
            value: 5,
            uuid: 'test-uuid',
            tagPattern: '',
            tagPatternMatches: true,
          },
        })}
      />,
    );
    expect(screen.getByLabelText('auto-prune-method')).toHaveValue(
      AutoPruneMethod.TAG_NUMBER,
    );
    // PatternFly NumberInput wraps the <input> in a div; use the spinbutton role
    expect(
      screen.getByRole('spinbutton', {name: 'number of tags'}),
    ).toHaveValue(5);
  });

  it('syncs state from TAG_CREATION_DATE policy prop', () => {
    render(
      <AutoPrunePolicyForm
        {...makeProps({
          policy: {
            method: AutoPruneMethod.TAG_CREATION_DATE,
            value: '14d',
            uuid: 'test-uuid-2',
            tagPattern: '',
            tagPatternMatches: true,
          },
        })}
      />,
    );
    expect(screen.getByLabelText('auto-prune-method')).toHaveValue(
      AutoPruneMethod.TAG_CREATION_DATE,
    );
    expect(
      screen.getByRole('spinbutton', {name: 'tag creation date value'}),
    ).toHaveValue(14);
    expect(
      screen.getByTestId('tag-auto-prune-creation-date-timeunit'),
    ).toHaveValue('d');
  });

  it('resets to defaults when policy is null after success', async () => {
    const {rerender} = render(
      <AutoPrunePolicyForm
        {...makeProps({
          policy: {
            method: AutoPruneMethod.TAG_NUMBER,
            value: 10,
            uuid: 'u1',
            tagPattern: '',
            tagPatternMatches: true,
          },
        })}
      />,
    );
    rerender(<AutoPrunePolicyForm {...makeProps({policy: null})} />);
    await waitFor(() =>
      expect(screen.getByLabelText('auto-prune-method')).toHaveValue(
        AutoPruneMethod.NONE,
      ),
    );
  });

  it('calls onSave with TAG_NUMBER args on submit', async () => {
    const onSave = vi.fn();
    render(<AutoPrunePolicyForm {...makeProps({onSave})} />);
    await userEvent.selectOptions(
      screen.getByLabelText('auto-prune-method'),
      AutoPruneMethod.TAG_NUMBER,
    );
    await userEvent.click(screen.getByRole('button', {name: /save/i}));
    expect(onSave).toHaveBeenCalledWith(
      AutoPruneMethod.TAG_NUMBER,
      20, // default count
      null, // uuid
      '', // tagPattern
      true, // tagPatternMatches
    );
  });

  it('calls onSave with TAG_CREATION_DATE args including duration string', async () => {
    const onSave = vi.fn();
    render(<AutoPrunePolicyForm {...makeProps({onSave})} />);
    await userEvent.selectOptions(
      screen.getByLabelText('auto-prune-method'),
      AutoPruneMethod.TAG_CREATION_DATE,
    );
    await userEvent.click(screen.getByRole('button', {name: /save/i}));
    expect(onSave).toHaveBeenCalledWith(
      AutoPruneMethod.TAG_CREATION_DATE,
      '7d', // default value + unit
      null,
      '',
      true,
    );
  });

  it('calls onSave with NONE and null value', async () => {
    const onSave = vi.fn();
    render(<AutoPrunePolicyForm {...makeProps({onSave})} />);
    await userEvent.click(screen.getByRole('button', {name: /save/i}));
    expect(onSave).toHaveBeenCalledWith(
      AutoPruneMethod.NONE,
      null,
      null,
      '',
      true,
    );
  });

  it('renders policy title with index', () => {
    render(<AutoPrunePolicyForm {...makeProps({index: 2})} />);
    expect(screen.getByText('Policy 3')).toBeInTheDocument();
  });
});
