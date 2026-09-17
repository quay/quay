/**
 * Global configuration for Playwright tests
 */

// Backend API URL (registry + API)
export const API_URL =
  process.env.REACT_QUAY_APP_API_URL || 'http://localhost:8080';

// Frontend URL
export const BASE_URL =
  process.env.PLAYWRIGHT_BASE_URL || 'http://localhost:8080';

// Bearer token for stage/production validation (set by Prow from QE secret).
// Bearer mode activates only when BOTH this and QUAY_BEARER_AUTH=1 are set.
export const QUAY_API_TOKEN = process.env.QUAY_API_TOKEN || '';

// Registry credentials for skopeo push/pull in stage validation.
export const QUAY_USER = process.env.QUAY_USER || '';
export const QUAY_PASSWORD = process.env.QUAY_PASSWORD || '';
