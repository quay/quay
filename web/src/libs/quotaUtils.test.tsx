import {renderQuotaConsumed, IQuotaReport} from './quotaUtils';
import {render, screen} from 'src/test-utils';

describe('renderQuotaConsumed', () => {
  it('returns em-dash string for null/undefined quotaReport', () => {
    expect(renderQuotaConsumed(null)).toBe('\u2014');
    expect(renderQuotaConsumed(undefined)).toBe('\u2014');
  });

  it('renders consumed bytes with percentage and total', () => {
    const report: IQuotaReport = {
      quota_bytes: 1073741824, // 1 GiB
      configured_quota: 2147483648, // 2 GiB
    };
    const result = renderQuotaConsumed(report, {
      showPercentage: true,
      showTotal: true,
      showBackfill: false,
    });
    render(<>{result}</>);
    expect(screen.getByText(/1\.00 GiB/)).toBeInTheDocument();
    expect(screen.getByText(/50%/)).toBeInTheDocument();
    expect(screen.getByText(/2\.00 GiB/)).toBeInTheDocument();
  });

  it('renders zero bytes without percentage when quota_bytes is 0', () => {
    const report: IQuotaReport = {
      quota_bytes: 0,
      configured_quota: 1073741824,
    };
    const result = renderQuotaConsumed(report, {
      showPercentage: true,
      showTotal: false,
      showBackfill: false,
    });
    render(<>{result}</>);
    expect(screen.getByText(/0\.00 KiB/)).toBeInTheDocument();
    // No percentage shown because quota_bytes is not > 0
    expect(screen.queryByText(/%/)).not.toBeInTheDocument();
  });

  it('renders backfill running status text', () => {
    const report: IQuotaReport = {
      quota_bytes: 500,
      backfill_status: 'running',
    };
    const result = renderQuotaConsumed(report, {
      showPercentage: false,
      showTotal: false,
      showBackfill: true,
    });
    render(<>{result}</>);
    expect(screen.getByText(/Backfill Running/)).toBeInTheDocument();
  });

  it('shows 0.00 KiB when quota configured but quota_bytes is null', () => {
    const report: IQuotaReport = {
      quota_bytes: null as unknown as number,
      configured_quota: 1073741824,
    };
    const result = renderQuotaConsumed(report, {
      showPercentage: false,
      showTotal: false,
      showBackfill: false,
    });
    render(<>{result}</>);
    expect(screen.getByText('0.00 KiB')).toBeInTheDocument();
  });
});
