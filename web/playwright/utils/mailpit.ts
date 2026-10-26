/**
 * Mailpit: Local email testing utilities
 *
 * Requires mailpit to be running (docker-compose up -d mailpit).
 *
 * @example
 * ```typescript
 * import { mailpit } from './utils/mailpit';
 *
 * await mailpit.clearInbox();
 * const email = await mailpit.waitForEmail(msg => msg.Subject.includes('Verify'));
 * const link = await mailpit.extractLink(email.ID);
 * ```
 */

import {
  fetchJsonWithRetry,
  fetchWithRetry,
  FetchRetryExhaustedError,
} from './fetch-retry';

const MAILPIT_API =
  process.env.MAILPIT_API_URL || 'http://localhost:8025/api/v1';

/**
 * Email message from Mailpit API
 */
export interface MailpitMessage {
  ID: string;
  From: {Address: string; Name: string};
  To: {Address: string; Name: string}[];
  Subject: string;
  Snippet: string;
  Created: string;
}

/**
 * Response from Mailpit messages endpoint
 */
export interface MailpitMessagesResponse {
  messages: MailpitMessage[];
  total: number;
}

/**
 * Mailpit utilities for testing email functionality.
 */
export const mailpit = {
  /**
   * Get all emails in the inbox
   */
  async getEmails(): Promise<MailpitMessagesResponse> {
    return fetchJsonWithRetry<MailpitMessagesResponse>(
      'mailpit.getEmails',
      `${MAILPIT_API}/messages`,
    );
  },

  /**
   * Clear all emails from the inbox
   */
  async clearInbox(): Promise<void> {
    await fetchWithRetry('mailpit.clearInbox', `${MAILPIT_API}/messages`, {
      method: 'DELETE',
    });
  },

  /**
   * Wait for an email matching the predicate
   *
   * @param predicate - Function to match the desired email
   * @param timeout - Max wait time in ms (default: 10000)
   * @param interval - Poll interval in ms (default: 500)
   * @returns Matching email or null if not found within timeout
   */
  async waitForEmail(
    predicate: (msg: MailpitMessage) => boolean,
    timeout = 10000,
    interval = 500,
  ): Promise<MailpitMessage | null> {
    const start = Date.now();
    while (Date.now() - start < timeout) {
      const {messages} = await this.getEmails();
      const found = messages.find(predicate);
      if (found) return found;
      await new Promise((r) => setTimeout(r, interval));
    }
    return null;
  },

  /**
   * Get the full body of an email
   *
   * @param id - Email ID from MailpitMessage.ID
   * @returns Email body (plain text if available, otherwise HTML)
   */
  async getEmailBody(id: string): Promise<string> {
    const data = await fetchJsonWithRetry<{Text?: string; HTML?: string}>(
      'mailpit.getEmailBody',
      `${MAILPIT_API}/message/${id}`,
    );
    return data.Text || data.HTML;
  },

  /**
   * Check if Mailpit is available
   *
   * Retries transient failures, then splits on whether a response was ever
   * received: Mailpit answering but non-ok (whether fast-failed or retries
   * exhausted) is treated as "not available" (returns false, as before).
   * Never receiving a response at all (e.g. DNS/connect failure) is let to
   * throw instead of being
   * reported as "not available" — isAvailable is only consulted when
   * FEATURE_MAILING is on, so an unreachable Mailpit means the environment
   * itself is broken, and masking that as "absent" would silently skip
   * email verification and fail the run later with a 403 far from the
   * real cause.
   *
   * @returns true if Mailpit is running and accessible
   */
  async isAvailable(): Promise<boolean> {
    try {
      await fetchWithRetry(
        'mailpit.isAvailable',
        `${MAILPIT_API}/messages`,
        undefined,
        1000,
      );
      return true;
    } catch (err) {
      if (
        err instanceof Error &&
        'receivedResponse' in err &&
        (err as FetchRetryExhaustedError).receivedResponse
      ) {
        return false;
      }
      throw err;
    }
  },

  /**
   * Extract a confirmation/action link from an email body
   *
   * @param emailId - Email ID from MailpitMessage.ID
   * @param linkPattern - Regex pattern to match the link (default: URLs with code= parameter)
   * @returns The extracted URL or null if not found
   */
  async extractLink(
    emailId: string,
    linkPattern = /https?:\/\/[^\s\])]+[?&]code=[^\s\])]+/,
  ): Promise<string | null> {
    const body = await this.getEmailBody(emailId);
    const match = body.match(linkPattern);
    return match ? match[0] : null;
  },

  /**
   * Wait for a confirmation email and extract the confirmation link
   *
   * @param emailAddress - Email address to look for
   * @param timeout - Max wait time in ms (default: 10000)
   * @returns The confirmation URL or null if not found
   */
  async waitForConfirmationLink(
    emailAddress: string,
    timeout = 10000,
  ): Promise<string | null> {
    const email = await this.waitForEmail(
      (msg) =>
        msg.To.some((to) => to.Address === emailAddress) &&
        msg.Subject.includes('confirm'),
      timeout,
    );
    if (!email) return null;
    return this.extractLink(email.ID);
  },
};
