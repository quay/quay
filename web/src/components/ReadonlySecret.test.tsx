import {render, screen} from 'src/test-utils';
import userEvent from '@testing-library/user-event';
import ReadonlySecret from './ReadonlySecret';

describe('ReadonlySecret', () => {
  it('renders the label', () => {
    render(<ReadonlySecret label="Token" secret="my-secret-value" />);
    expect(screen.getByText(/Token/)).toBeInTheDocument();
  });

  it('hides secret by default (type=password)', () => {
    render(<ReadonlySecret label="Token" secret="my-secret-value" />);
    expect(screen.getByLabelText('secret input')).toHaveAttribute(
      'type',
      'password',
    );
  });

  it('shows secret after clicking the show button', async () => {
    render(<ReadonlySecret label="Token" secret="my-secret-value" />);
    await userEvent.click(screen.getByLabelText('Show secret'));
    expect(screen.getByLabelText('secret input')).toHaveAttribute(
      'type',
      'text',
    );
  });

  it('hides secret again after clicking show then hide', async () => {
    render(<ReadonlySecret label="Token" secret="my-secret-value" />);
    await userEvent.click(screen.getByLabelText('Show secret'));
    await userEvent.click(screen.getByLabelText('Hide secret'));
    expect(screen.getByLabelText('secret input')).toHaveAttribute(
      'type',
      'password',
    );
  });

  it('renders the secret value in the input', () => {
    render(<ReadonlySecret label="Token" secret="my-secret-value" />);
    expect(screen.getByLabelText('secret input')).toHaveValue(
      'my-secret-value',
    );
  });
});
