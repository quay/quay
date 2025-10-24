import {Tooltip} from '@patternfly/react-core';
import {formatSize} from './utils';

export interface IQuotaReport {
  quota_bytes: number;
  configured_quota?: number;
  percent_consumed?: number;
  backfill_status?: 'waiting' | 'running' | null;
}

export interface QuotaDisplayOptions {
  showPercentage?: boolean;
  showTotal?: boolean;
  showBackfill?: boolean;
}

/**
 * Renders quota consumed information with optional percentage, total, and backfill status
 *
 * This utility can be used for both Repository and Organization quota displays.
 * It provides a consistent way to show quota information across the application.
 *
 * @param quotaReport - The quota report data from the API
 * @param options - Display options for what information to show
 * @returns JSX element with quota display or empty string if no data
 *
 * @example
 * // Organization usage
 * renderQuotaConsumed(organization.quota_report, {
 *   showPercentage: true,
 *   showTotal: true,
 *   showBackfill: true
 * })
 * // Output: "15.23 GiB (65%) of 25.00 GiB Backfill Running ⓘ"
 *
 * @example
 * // Repository usage
 * renderQuotaConsumed(repository.quota_report, {
 *   showPercentage: false,
 *   showTotal: false,
 *   showBackfill: false
 * })
 * // Output: "15.23 GiB"
 */
export function renderQuotaConsumed(
  quotaReport: IQuotaReport | null | undefined,
  options: QuotaDisplayOptions = {
    showPercentage: true,
    showTotal: true,
    showBackfill: true,
  },
): JSX.Element | string {
  if (!quotaReport) {
    return '—';
  }

  const {quota_bytes, configured_quota, backfill_status} = quotaReport;

  // Format consumed bytes
  let consumedDisplay = '';
  if (quota_bytes) {
    consumedDisplay = formatSize(quota_bytes);

    // Add percentage if configured quota exists and option enabled
    if (options.showPercentage && configured_quota) {
      const percentage = Math.round((quota_bytes / configured_quota) * 100);
      consumedDisplay += ` (${percentage}%)`;
    }
  } else if (configured_quota) {
    // Show 0 if quota is configured but nothing consumed yet
    consumedDisplay = '0';
  }

  // Add total if configured quota exists and option enabled
  let totalDisplay = '';
  if (options.showTotal && configured_quota) {
    totalDisplay = ` of ${formatSize(configured_quota)}`;
  }

  // Render backfill status if option enabled
  let backfillElement = null;
  if (options.showBackfill && backfill_status) {
    if (backfill_status === 'waiting') {
      backfillElement = (
        <Tooltip content="A task to total the pre-existing images is currently queued.">
          <span>
            {' '}
            Backfill Queued <i className="fa fa-info-circle" />
          </span>
        </Tooltip>
      );
    } else if (backfill_status === 'running') {
      backfillElement = (
        <Tooltip content="A task to total the pre-existing images is currently running.">
          <span>
            {' '}
            Backfill Running <i className="fa fa-info-circle" />
          </span>
        </Tooltip>
      );
    }
  }

  return (
    <>
      {consumedDisplay}
      {totalDisplay}
      {backfillElement}
    </>
  );
}
