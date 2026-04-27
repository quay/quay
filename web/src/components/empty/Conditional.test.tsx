import {render, screen} from 'src/test-utils';
import Conditional from './Conditional';

describe('Conditional', () => {
  it('renders children when condition is true', () => {
    render(
      <Conditional if={true}>
        <span>Visible</span>
      </Conditional>,
    );
    expect(screen.getByText('Visible')).toBeInTheDocument();
  });

  it('returns null when condition is false', () => {
    const {container} = render(
      <Conditional if={false}>
        <span>Hidden</span>
      </Conditional>,
    );
    expect(container).toBeEmptyDOMElement();
  });

  it('updates when condition changes', () => {
    const {rerender} = render(
      <Conditional if={false}>
        <span>Content</span>
      </Conditional>,
    );
    expect(screen.queryByText('Content')).not.toBeInTheDocument();
    rerender(
      <Conditional if={true}>
        <span>Content</span>
      </Conditional>,
    );
    expect(screen.getByText('Content')).toBeInTheDocument();
  });
});
