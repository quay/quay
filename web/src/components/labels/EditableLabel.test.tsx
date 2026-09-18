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

  it('commits the current value on an outside click that reuses the listener registered before the value changed', async () => {
    const onEditComplete = vi.fn();
    const addEventListenerSpy = vi.spyOn(document, 'addEventListener');
    const {rerender} = render(
      <EditableLabel
        value=""
        setValue={vi.fn()}
        onEditComplete={onEditComplete}
      />,
    );
    await userEvent.click(screen.getByText('Add new label'));

    // The handler captured here is the one registered on mount, before the
    // parent's value update below. If it closes over a stale value, the
    // race this test guards against is back.
    const mousedownCalls = addEventListenerSpy.mock.calls.filter(
      ([eventName]) => eventName === 'mousedown',
    );
    const mousedownCall = mousedownCalls[mousedownCalls.length - 1];
    const mousedownHandler = mousedownCall[1] as (event: {
      target: EventTarget;
    }) => void;

    rerender(
      <EditableLabel
        value="fail=test"
        setValue={vi.fn()}
        onEditComplete={onEditComplete}
      />,
    );

    mousedownHandler({target: document.body});

    expect(onEditComplete).toHaveBeenCalledWith('fail=test');
    addEventListenerSpy.mockRestore();
  });

  it('calls the latest onEditComplete on an outside click that reuses the listener registered before the callback changed', async () => {
    const mountTimeOnEditComplete = vi.fn();
    const latestOnEditComplete = vi.fn();
    const addEventListenerSpy = vi.spyOn(document, 'addEventListener');
    const {rerender} = render(
      <EditableLabel
        value="k=v"
        setValue={vi.fn()}
        onEditComplete={mountTimeOnEditComplete}
      />,
    );
    await userEvent.click(screen.getByText('k=v'));

    // The handler captured here is the one registered on mount, before the
    // parent's onEditComplete update below. If it closes over the mount-time
    // callback, the stale-callback bug this test guards against is back.
    const mousedownCalls = addEventListenerSpy.mock.calls.filter(
      ([eventName]) => eventName === 'mousedown',
    );
    const mousedownCall = mousedownCalls[mousedownCalls.length - 1];
    const mousedownHandler = mousedownCall[1] as (event: {
      target: EventTarget;
    }) => void;

    rerender(
      <EditableLabel
        value="k=v"
        setValue={vi.fn()}
        onEditComplete={latestOnEditComplete}
      />,
    );

    mousedownHandler({target: document.body});

    expect(latestOnEditComplete).toHaveBeenCalledWith('k=v');
    expect(mountTimeOnEditComplete).not.toHaveBeenCalled();
    addEventListenerSpy.mockRestore();
  });
});
