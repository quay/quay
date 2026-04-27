import {render, screen, userEvent, waitFor} from 'src/test-utils';
import TypeAheadSelect from './TypeAheadSelect';

const initialOptions = [
  {value: 'apple', children: 'apple'},
  {value: 'banana', children: 'banana'},
  {value: 'cherry', children: 'cherry'},
];

function makeProps(overrides = {}) {
  return {
    initialSelectOptions: initialOptions,
    value: '',
    onChange: vi.fn(),
    placeholder: 'Select a fruit',
    ...overrides,
  };
}

describe('TypeAheadSelect', () => {
  it('renders the text input with placeholder', () => {
    render(<TypeAheadSelect {...makeProps()} />);
    expect(screen.getByPlaceholderText('Select a fruit')).toBeInTheDocument();
  });

  it('opens dropdown and shows all options when toggle is clicked', async () => {
    render(<TypeAheadSelect {...makeProps()} />);
    await userEvent.click(screen.getByRole('button'));
    expect(screen.getByText('apple')).toBeInTheDocument();
    expect(screen.getByText('banana')).toBeInTheDocument();
    expect(screen.getByText('cherry')).toBeInTheDocument();
  });

  it('filters options as user types', async () => {
    render(<TypeAheadSelect {...makeProps()} />);
    const input = screen.getByPlaceholderText('Select a fruit');
    await userEvent.type(input, 'ban');
    expect(screen.getByText('banana')).toBeInTheDocument();
    expect(screen.queryByText('apple')).not.toBeInTheDocument();
  });

  it('shows no-results message when filter matches nothing', async () => {
    render(<TypeAheadSelect {...makeProps()} />);
    const input = screen.getByPlaceholderText('Select a fruit');
    await userEvent.type(input, 'xyz');
    await waitFor(() =>
      expect(screen.getByText('no results')).toBeInTheDocument(),
    );
  });

  it('calls onChange when an option is selected', async () => {
    const onChange = vi.fn();
    render(<TypeAheadSelect {...makeProps({onChange})} />);
    await userEvent.click(screen.getByRole('button'));
    await userEvent.click(screen.getByText('cherry'));
    expect(onChange).toHaveBeenCalledWith('cherry');
  });

  it('shows clear button when value is non-empty and clears on click', async () => {
    const onChange = vi.fn();
    render(<TypeAheadSelect {...makeProps({value: 'apple', onChange})} />);
    const clearBtn = screen.getByRole('button', {name: /clear input value/i});
    expect(clearBtn).toBeInTheDocument();
    await userEvent.click(clearBtn);
    expect(onChange).toHaveBeenCalledWith('');
  });
});
