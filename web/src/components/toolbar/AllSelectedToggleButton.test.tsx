import {render, screen, userEvent} from 'src/test-utils';
import {AllSelectedToggleButton} from './AllSelectedToggleButton';

describe('AllSelectedToggleButton', () => {
  it('renders All and Selected toggle buttons', () => {
    render(
      <AllSelectedToggleButton
        showAllItems={vi.fn()}
        showSelectedItems={vi.fn()}
      />,
    );
    expect(screen.getByRole('button', {name: 'All'})).toBeInTheDocument();
    expect(screen.getByRole('button', {name: 'Selected'})).toBeInTheDocument();
  });

  it('starts with All selected by default', () => {
    render(
      <AllSelectedToggleButton
        showAllItems={vi.fn()}
        showSelectedItems={vi.fn()}
      />,
    );
    expect(screen.getByRole('button', {name: 'All'})).toHaveAttribute(
      'aria-pressed',
      'true',
    );
  });

  it('calls showAllItems when All is clicked', async () => {
    const showAllItems = vi.fn();
    render(
      <AllSelectedToggleButton
        showAllItems={showAllItems}
        showSelectedItems={vi.fn()}
      />,
    );
    await userEvent.click(screen.getByRole('button', {name: 'Selected'}));
    await userEvent.click(screen.getByRole('button', {name: 'All'}));
    expect(showAllItems).toHaveBeenCalled();
  });

  it('calls showSelectedItems when Selected is clicked', async () => {
    const showSelectedItems = vi.fn();
    render(
      <AllSelectedToggleButton
        showAllItems={vi.fn()}
        showSelectedItems={showSelectedItems}
      />,
    );
    await userEvent.click(screen.getByRole('button', {name: 'Selected'}));
    expect(showSelectedItems).toHaveBeenCalled();
  });
});
