import {render, screen} from 'src/test-utils';
import RegexMatchView from './RegexMatchView';
import {PlusCircleIcon} from '@patternfly/react-icons';

const items = [
  {icon: <PlusCircleIcon />, title: 'apple', value: 'apple'},
  {icon: <PlusCircleIcon />, title: 'banana', value: 'banana'},
  {icon: <PlusCircleIcon />, title: 'cherry', value: 'cherry'},
];

describe('RegexMatchView', () => {
  it('shows invalid message for invalid regex', () => {
    render(<RegexMatchView regex="[invalid" items={items} />);
    expect(screen.getByText('Invalid Regular Expression!')).toBeInTheDocument();
  });

  it('renders Matching and Not Matching sections', () => {
    render(<RegexMatchView regex="apple" items={items} />);
    expect(screen.getByText('Matching:')).toBeInTheDocument();
    expect(screen.getByText('Not Matching:')).toBeInTheDocument();
  });

  it('places matched items in Matching list', () => {
    render(<RegexMatchView regex="apple" items={items} />);
    const matching = screen.getByText('Matching:').closest('tr');
    expect(matching).toHaveTextContent('apple');
  });

  it('places non-matched items in Not Matching list', () => {
    render(<RegexMatchView regex="apple" items={items} />);
    const notMatching = screen.getByText('Not Matching:').closest('tr');
    expect(notMatching).toHaveTextContent('banana');
    expect(notMatching).toHaveTextContent('cherry');
  });

  it('matches all items when regex matches everything', () => {
    render(<RegexMatchView regex=".*" items={items} />);
    const matching = screen.getByText('Matching:').closest('tr');
    expect(matching).toHaveTextContent('apple');
    expect(matching).toHaveTextContent('banana');
    expect(matching).toHaveTextContent('cherry');
  });
});
