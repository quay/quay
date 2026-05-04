import {render, screen, userEvent, waitFor} from 'src/test-utils';
import {useQuayConfig} from 'src/hooks/UseQuayConfig';
import {useRobotToken} from 'src/hooks/useRobotAccounts';
import path from 'path';
import Module from 'module';

const origResolve = (Module as any)._resolveFilename;
(Module as any)._resolveFilename = function (
  request: string,
  parent: any,
  isMain: boolean,
  options: any,
) {
  if (/\.(svg|png|css)$/i.test(request) && request.startsWith('src/')) {
    return path.resolve(__dirname, '../../../../', request);
  }
  return origResolve.call(this, request, parent, isMain, options);
};

vi.mock('src/hooks/UseQuayConfig', () => ({
  useQuayConfig: vi.fn(),
}));

vi.mock('src/hooks/useRobotAccounts', () => ({
  useRobotToken: vi.fn(),
}));

const mockUseQuayConfig = vi.mocked(useQuayConfig);
const mockUseRobotToken = vi.mocked(useRobotToken);

function makeProps(overrides = {}) {
  return {
    namespace: 'testorg',
    name: 'testorg+myrobot',
    ...overrides,
  };
}

let RobotTokensModal: any;

beforeAll(async () => {
  const mod = await import('./RobotTokensModal');
  RobotTokensModal = mod.default;
});

beforeEach(() => {
  mockUseQuayConfig.mockReturnValue({
    config: {SERVER_HOSTNAME: 'quay.example.com'},
    features: {},
  } as any);
  mockUseRobotToken.mockReturnValue({
    regenerateRobotToken: vi.fn().mockResolvedValue({}),
  } as any);
});

describe('RobotTokensModal', () => {
  it('renders Robot Account tab by default with username', () => {
    render(<RobotTokensModal {...makeProps()} />);
    expect(
      screen.getByRole('tab', {name: /Robot Account/}),
    ).toBeInTheDocument();
    expect(screen.getByText('Username & Robot account')).toBeInTheDocument();
  });

  it('shows regenerate token warning and button', () => {
    render(<RobotTokensModal {...makeProps()} />);
    expect(screen.getByText(/once you regenerate token/)).toBeInTheDocument();
    expect(
      screen.getByRole('button', {name: /regenerate token now/i}),
    ).toBeInTheDocument();
  });

  it('calls regenerateRobotToken on button click', async () => {
    const regenerateRobotToken = vi.fn().mockResolvedValue({});
    mockUseRobotToken.mockReturnValue({regenerateRobotToken} as any);
    render(<RobotTokensModal {...makeProps()} />);
    await userEvent.click(
      screen.getByRole('button', {name: /regenerate token now/i}),
    );
    await waitFor(() =>
      expect(regenerateRobotToken).toHaveBeenCalledWith({
        namespace: 'testorg',
        robotName: 'testorg+myrobot',
      }),
    );
  });

  it('renders all tab titles', () => {
    render(<RobotTokensModal {...makeProps()} />);
    const tabs = screen.getAllByRole('tab');
    expect(tabs).toHaveLength(5);
    expect(tabs[0]).toHaveTextContent('Robot Account');
    expect(tabs[1]).toHaveTextContent('Kubernetes');
    expect(tabs[2]).toHaveTextContent('Podman');
    expect(tabs[3]).toHaveTextContent('Docker Login');
    expect(tabs[4]).toHaveTextContent('Docker Configuration');
  });

  it('shows Kubernetes content when Kubernetes tab is clicked', async () => {
    render(<RobotTokensModal {...makeProps()} />);
    await userEvent.click(screen.getByRole('tab', {name: /Kubernetes/}));
    expect(
      screen.getByText('Step 1: Select the scope of the secret'),
    ).toBeInTheDocument();
    expect(screen.getByText('Step 2: Download secret')).toBeInTheDocument();
  });

  it('shows Podman content when Podman tab is clicked', async () => {
    render(<RobotTokensModal {...makeProps()} />);
    await userEvent.click(screen.getByRole('tab', {name: /Podman/}));
    expect(screen.getByText('Podman Login')).toBeInTheDocument();
  });

  it('shows Docker config when Docker Configuration tab is clicked', async () => {
    render(<RobotTokensModal {...makeProps()} />);
    await userEvent.click(
      screen.getByRole('tab', {name: /Docker Configuration/}),
    );
    expect(
      screen.getByText('Step 1: Download Docker configuration file'),
    ).toBeInTheDocument();
  });

  it('displays robot name in clipboard copy', () => {
    render(<RobotTokensModal {...makeProps()} />);
    expect(
      screen.getByText((_, el) => {
        return (
          el?.tagName?.toLowerCase() === 'input' &&
          (el as HTMLInputElement).value === 'testorg+myrobot'
        );
      }),
    ).toBeInTheDocument();
  });
});
