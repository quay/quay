import {fireEvent} from '@testing-library/react';
import {render, screen, userEvent} from 'src/test-utils';
import EditableLabel from './EditableLabel';

describe('EditableLabel', () => {
  it('renders "Add new label" when value is empty', () => {
    render(
      <EditableLabel value="" setValue={vi.fn()} onEditComplete={vi.fn()} />,
    );
    expect(screen.getByText('Add new label')).toBeInTheDocument();
  });

  it('renders the label text when value is set', () => {
    render(
      <EditableLabel
        value="env=prod"
        setValue={vi.fn()}
        onEditComplete={vi.fn()}
      />,
    );
    expect(screen.getByText('env=prod')).toBeInTheDocument();
  });

  it('switches to text input after clicking the label', async () => {
    render(
      <EditableLabel
        value="my=label"
        setValue={vi.fn()}
        onEditComplete={vi.fn()}
      />,
    );
    await userEvent.click(screen.getByText('my=label'));
    expect(screen.getByRole('textbox')).toBeInTheDocument();
  });

  it('calls setValue as user types in the input', async () => {
    const setValue = vi.fn();
    render(
      <EditableLabel value="" setValue={setValue} onEditComplete={vi.fn()} />,
    );
    await userEvent.click(screen.getByText('Add new label'));
    // fireEvent sends the full value at once; trim behavior is exercised by the whitespace
    fireEvent.change(screen.getByRole('textbox'), {target: {value: ' k=v '}});
    expect(setValue).toHaveBeenLastCalledWith('k=v');
  });

  it('shows error validation state when invalid is true', async () => {
    render(
      <EditableLabel
        value="bad"
        setValue={vi.fn()}
        onEditComplete={vi.fn()}
        invalid
      />,
    );
    await userEvent.click(screen.getByText('bad'));
    const input = screen.getByRole('textbox');
    expect(input).toHaveAttribute('aria-invalid', 'true');
  });
});
