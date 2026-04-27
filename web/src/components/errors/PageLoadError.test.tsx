import {render, screen} from 'src/test-utils';
import PageLoadError from './PageLoadError';

describe('PageLoadError', () => {
  it('renders "Unable to reach server" heading', () => {
    render(<PageLoadError />);
    expect(screen.getByText('Unable to reach server')).toBeInTheDocument();
  });

  it('renders the body message', () => {
    render(<PageLoadError />);
    expect(screen.getByText('Page could not be loaded')).toBeInTheDocument();
  });

  it('renders a Retry button that triggers reload', () => {
    const reloadSpy = vi
      .spyOn(window.location, 'reload')
      .mockImplementation(vi.fn());
    render(<PageLoadError />);
    const btn = screen.getByRole('button', {name: /retry/i});
    btn.click();
    expect(reloadSpy).toHaveBeenCalledTimes(1);
    reloadSpy.mockRestore();
  });
});
