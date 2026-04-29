import {render, screen} from 'src/test-utils';
import {StatusDisplay} from './StatusDisplay';

describe('StatusDisplay', () => {
  const items = [
    {label: 'Name', value: 'my-repo'},
    {label: 'Status', value: 'Active'},
  ];

  it('renders all item labels and values', () => {
    render(<StatusDisplay items={items} />);
    expect(screen.getByText('Name')).toBeInTheDocument();
    expect(screen.getByText('my-repo')).toBeInTheDocument();
    expect(screen.getByText('Status')).toBeInTheDocument();
    expect(screen.getByText('Active')).toBeInTheDocument();
  });

  it('renders title when provided', () => {
    render(<StatusDisplay title="Repository Details" items={items} />);
    expect(screen.getByText('Repository Details')).toBeInTheDocument();
  });

  it('does not render title when not provided', () => {
    const {container} = render(<StatusDisplay items={items} />);
    expect(container.querySelector('h3')).not.toBeInTheDocument();
  });

  it('renders item action alongside value', () => {
    const itemsWithAction = [
      {label: 'Token', value: 'abc123', action: <button>Copy</button>},
    ];
    render(<StatusDisplay items={itemsWithAction} />);
    expect(screen.getByRole('button', {name: 'Copy'})).toBeInTheDocument();
    expect(screen.getByText('abc123')).toBeInTheDocument();
  });
});
