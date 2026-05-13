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

const MAILPIT_API = 'http://localhost:8025/api/v1';

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
    const response = await fetch(`${MAILPIT_API}/messages`);
    if (!response.ok) {
      throw new Error(`Mailpit API error: ${response.status}`);
    }
    return response.json();
  },

  /**
   * Clear all emails from the inbox
   */
  async clearInbox(): Promise<void> {
    const response = await fetch(`${MAILPIT_API}/messages`, {method: 'DELETE'});
    if (!response.ok) {
      throw new Error(`Mailpit API error: ${response.status}`);
    }
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
    const response = await fetch(`${MAILPIT_API}/message/${id}`);
    if (!response.ok) {
      throw new Error(`Mailpit API error: ${response.status}`);
    }
    const data = await response.json();
    return data.Text || data.HTML;
  },

  /**
   * Check if Mailpit is available
   *
   * @returns true if Mailpit is running and accessible
   */
  async isAvailable(): Promise<boolean> {
    try {
      const response = await fetch(`${MAILPIT_API}/messages`, {
        signal: AbortSignal.timeout(1000),
      });
      return response.ok;
    } catch {
      return false;
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
