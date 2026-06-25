import {render, screen} from 'src/test-utils';
import Empty from './Empty';
import {ExclamationTriangleIcon} from '@patternfly/react-icons';

describe('Empty', () => {
  it('renders the title', () => {
    render(
      <Empty
        icon={ExclamationTriangleIcon}
        title="Nothing here"
        body="No items found"
      />,
    );
    expect(screen.getByText('Nothing here')).toBeInTheDocument();
  });

  it('renders the body text', () => {
    render(
      <Empty
        icon={ExclamationTriangleIcon}
        title="Empty state"
        body="Try a different filter"
      />,
    );
    expect(screen.getByText('Try a different filter')).toBeInTheDocument();
  });

  it('renders a primary button when provided', () => {
    render(
      <Empty
        icon={ExclamationTriangleIcon}
        title="Empty"
        body="No data"
        button={<button>Create item</button>}
      />,
    );
    expect(
      screen.getByRole('button', {name: 'Create item'}),
    ).toBeInTheDocument();
  });

  it('renders secondary actions when provided', () => {
    render(
      <Empty
        icon={ExclamationTriangleIcon}
        title="Empty"
        body="No data"
        secondaryActions={[
          <button key="a">Secondary A</button>,
          <button key="b">Secondary B</button>,
        ]}
      />,
    );
    expect(
      screen.getByRole('button', {name: 'Secondary A'}),
    ).toBeInTheDocument();
    expect(
      screen.getByRole('button', {name: 'Secondary B'}),
    ).toBeInTheDocument();
  });
});
