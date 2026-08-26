import {render, screen, userEvent} from 'src/test-utils';
import {Kebab} from './Kebab';
import {DropdownItem} from '@patternfly/react-core';

describe('Kebab', () => {
  it('renders the kebab menu toggle', () => {
    render(
      <Kebab isKebabOpen={false} setKebabOpen={vi.fn()} kebabItems={[]} />,
    );
    // Kebab uses ellipsis icon; toggle button is present
    expect(screen.getByRole('button')).toBeInTheDocument();
  });

  it('calls setKebabOpen when toggle is clicked', async () => {
    const setKebabOpen = vi.fn();
    render(
      <Kebab isKebabOpen={false} setKebabOpen={setKebabOpen} kebabItems={[]} />,
    );
    await userEvent.click(screen.getByRole('button'));
    expect(setKebabOpen).toHaveBeenCalledWith(true);
  });

  it('renders items when isKebabOpen is true', () => {
    render(
      <Kebab
        isKebabOpen={true}
        setKebabOpen={vi.fn()}
        kebabItems={[
          <DropdownItem key="edit">Edit</DropdownItem>,
          <DropdownItem key="delete">Delete</DropdownItem>,
        ]}
      />,
    );
    expect(screen.getByText('Edit')).toBeInTheDocument();
    expect(screen.getByText('Delete')).toBeInTheDocument();
  });
});
