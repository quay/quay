import {render, screen} from 'src/test-utils';
import SystemStatusBanner from './SystemStatusBanner';

vi.mock('src/hooks/UseQuayState', () => ({
  useQuayState: vi.fn(),
}));
vi.mock('src/hooks/UseQuayConfig', () => ({
  useQuayConfig: vi.fn(),
}));

import {useQuayState} from 'src/hooks/UseQuayState';
import {useQuayConfig} from 'src/hooks/UseQuayConfig';

const mockUseQuayState = useQuayState as ReturnType<typeof vi.fn>;
const mockUseQuayConfig = useQuayConfig as ReturnType<typeof vi.fn>;

describe('SystemStatusBanner', () => {
  beforeEach(() => {
    mockUseQuayConfig.mockReturnValue({config: {REGISTRY_TITLE: 'TestReg'}});
  });

  it('renders nothing when not in any special mode', () => {
    mockUseQuayState.mockReturnValue({
      inReadOnlyMode: false,
      inAccountRecoveryMode: false,
    });
    const {container} = render(<SystemStatusBanner />);
    expect(container).toBeEmptyDOMElement();
  });

  it('renders read-only mode banner', () => {
    mockUseQuayState.mockReturnValue({
      inReadOnlyMode: true,
      inAccountRecoveryMode: false,
    });
    render(<SystemStatusBanner />);
    expect(screen.getByTestId('readonly-mode-banner')).toBeInTheDocument();
    expect(screen.getByText('TestReg')).toBeInTheDocument();
    expect(screen.getByText(/currently in read-only mode/)).toBeInTheDocument();
  });

  it('renders account recovery mode banner', () => {
    mockUseQuayState.mockReturnValue({
      inReadOnlyMode: false,
      inAccountRecoveryMode: true,
    });
    render(<SystemStatusBanner />);
    expect(
      screen.getByTestId('account-recovery-mode-banner'),
    ).toBeInTheDocument();
    expect(
      screen.getByText(/currently in account recovery mode/),
    ).toBeInTheDocument();
  });

  it('renders both banners when both modes are active', () => {
    mockUseQuayState.mockReturnValue({
      inReadOnlyMode: true,
      inAccountRecoveryMode: true,
    });
    render(<SystemStatusBanner />);
    expect(screen.getByTestId('readonly-mode-banner')).toBeInTheDocument();
    expect(
      screen.getByTestId('account-recovery-mode-banner'),
    ).toBeInTheDocument();
  });

  it('falls back to "Quay" when registry title is not configured', () => {
    mockUseQuayConfig.mockReturnValue({config: {}});
    mockUseQuayState.mockReturnValue({
      inReadOnlyMode: true,
      inAccountRecoveryMode: false,
    });
    render(<SystemStatusBanner />);
    expect(screen.getByText('Quay')).toBeInTheDocument();
  });
});
