import {render, screen, userEvent} from 'src/test-utils';
import {ExpandCollapseButton} from './ExpandCollapseButton';

describe('ExpandCollapseButton', () => {
  it('renders Expand and Collapse toggle buttons', () => {
    render(
      <ExpandCollapseButton expandTable={vi.fn()} collapseTable={vi.fn()} />,
    );
    expect(screen.getByRole('button', {name: 'Expand'})).toBeInTheDocument();
    expect(screen.getByRole('button', {name: 'Collapse'})).toBeInTheDocument();
  });

  it('starts with Collapse selected by default', () => {
    render(
      <ExpandCollapseButton expandTable={vi.fn()} collapseTable={vi.fn()} />,
    );
    expect(screen.getByRole('button', {name: 'Collapse'})).toHaveAttribute(
      'aria-pressed',
      'true',
    );
  });

  it('calls expandTable when Expand is clicked', async () => {
    const expandTable = vi.fn();
    render(
      <ExpandCollapseButton
        expandTable={expandTable}
        collapseTable={vi.fn()}
      />,
    );
    await userEvent.click(screen.getByRole('button', {name: 'Expand'}));
    expect(expandTable).toHaveBeenCalled();
  });

  it('calls collapseTable when Collapse is clicked after Expand', async () => {
    const collapseTable = vi.fn();
    render(
      <ExpandCollapseButton
        expandTable={vi.fn()}
        collapseTable={collapseTable}
      />,
    );
    await userEvent.click(screen.getByRole('button', {name: 'Expand'}));
    await userEvent.click(screen.getByRole('button', {name: 'Collapse'}));
    expect(collapseTable).toHaveBeenCalled();
  });
});
