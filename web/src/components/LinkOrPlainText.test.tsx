import {render, screen} from 'src/test-utils';
import LinkOrPlainText from './LinkOrPlainText';

describe('LinkOrPlainText', () => {
  it('renders as anchor when href is provided', () => {
    render(
      <LinkOrPlainText href="https://example.com">Click me</LinkOrPlainText>,
    );
    const link = screen.getByRole('link', {name: 'Click me'});
    expect(link).toBeInTheDocument();
    expect(link).toHaveAttribute('href', 'https://example.com');
  });

  it('renders children as plain text when href is undefined', () => {
    render(<LinkOrPlainText>Plain text</LinkOrPlainText>);
    expect(screen.getByText('Plain text')).toBeInTheDocument();
    expect(screen.queryByRole('link')).not.toBeInTheDocument();
  });

  it('renders children as plain text when href is null', () => {
    render(<LinkOrPlainText href={null}>No link</LinkOrPlainText>);
    expect(screen.getByText('No link')).toBeInTheDocument();
    expect(screen.queryByRole('link')).not.toBeInTheDocument();
  });
});
