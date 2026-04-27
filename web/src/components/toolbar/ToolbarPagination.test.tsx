import {render, screen, userEvent} from 'src/test-utils';
import {ToolbarPagination} from './ToolbarPagination';

describe('ToolbarPagination', () => {
  const defaultProps = {
    perPage: 10,
    page: 1,
    setPage: vi.fn(),
    setPerPage: vi.fn(),
  };

  it('renders pagination when total is provided', () => {
    render(<ToolbarPagination {...defaultProps} total={50} />);
    expect(screen.getAllByText(/1 - 10/).length).toBeGreaterThan(0);
  });

  it('uses itemsList length when total is not provided', () => {
    render(
      <ToolbarPagination
        {...defaultProps}
        itemsList={Array.from({length: 25})}
      />,
    );
    expect(screen.getAllByText(/1 - 10/).length).toBeGreaterThan(0);
  });

  it('calls setPage when next page button is clicked', async () => {
    const setPage = vi.fn();
    render(
      <ToolbarPagination {...defaultProps} total={50} setPage={setPage} />,
    );
    await userEvent.click(
      screen.getAllByRole('button', {name: /next page/i})[0],
    );
    expect(setPage).toHaveBeenCalledWith(2);
  });

  it('resets to page 1 when per-page dropdown selection changes', async () => {
    const setPage = vi.fn();
    const setPerPage = vi.fn();
    render(
      <ToolbarPagination
        {...defaultProps}
        total={50}
        setPage={setPage}
        setPerPage={setPerPage}
      />,
    );
    // Open per-page dropdown - button label shows current range
    const toggleButtons = screen.getAllByRole('button', {name: /1 - 10/});
    await userEvent.click(toggleButtons[0]);
    await userEvent.click(screen.getByText('20 per page'));
    expect(setPage).toHaveBeenCalledWith(1);
    expect(setPerPage).toHaveBeenCalledWith(20);
  });
});
