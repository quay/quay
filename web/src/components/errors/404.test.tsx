import {render, screen} from 'src/test-utils';
import NotFound from './404';

describe('NotFound', () => {
  it('renders 404 heading', () => {
    render(<NotFound />);
    expect(screen.getByText('404 Page not found')).toBeInTheDocument();
  });

  it('renders descriptive body text', () => {
    render(<NotFound />);
    expect(screen.getByText(/didn't find a page/i)).toBeInTheDocument();
  });
});
