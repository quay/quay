import {render, screen, userEvent} from 'src/test-utils';
import {ToolbarButton} from './ToolbarButton';

describe('ToolbarButton', () => {
  it('renders button with provided text', () => {
    render(
      <ToolbarButton
        id="create-btn"
        buttonValue="Create"
        Modal={<div />}
        isModalOpen={false}
        setModalOpen={vi.fn()}
      />,
    );
    expect(screen.getByRole('button', {name: 'Create'})).toBeInTheDocument();
  });

  it('calls setModalOpen(true) when clicked', async () => {
    const setModalOpen = vi.fn();
    render(
      <ToolbarButton
        id="create-btn"
        buttonValue="Create"
        Modal={<div />}
        isModalOpen={false}
        setModalOpen={setModalOpen}
      />,
    );
    await userEvent.click(screen.getByRole('button', {name: 'Create'}));
    expect(setModalOpen).toHaveBeenCalledWith(true);
  });

  it('renders as disabled when isDisabled is true', () => {
    render(
      <ToolbarButton
        id="create-btn"
        buttonValue="Create"
        Modal={<div />}
        isModalOpen={false}
        setModalOpen={vi.fn()}
        isDisabled
      />,
    );
    expect(screen.getByRole('button', {name: 'Create'})).toBeDisabled();
  });
});
