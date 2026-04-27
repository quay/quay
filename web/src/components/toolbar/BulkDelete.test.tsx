import {render, screen, userEvent} from 'src/test-utils';
import {BulkDelete} from './BulkDelete';

describe('BulkDelete', () => {
  it('renders the delete button', () => {
    render(<BulkDelete setClicked={vi.fn()} />);
    expect(
      screen.getByRole('button', {name: /delete selected items/i}),
    ).toBeInTheDocument();
  });

  it('calls setClicked(true) when clicked', async () => {
    const setClicked = vi.fn();
    render(<BulkDelete setClicked={setClicked} />);
    await userEvent.click(
      screen.getByRole('button', {name: /delete selected items/i}),
    );
    expect(setClicked).toHaveBeenCalledWith(true);
  });
});
