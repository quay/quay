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
// When set, tests use bearer auth instead of CSRF session auth.
export const QUAY_API_TOKEN = process.env.QUAY_API_TOKEN || '';

// Registry credentials for skopeo push/pull in stage validation.
export const QUAY_USER = process.env.QUAY_USER || '';
export const QUAY_PASSWORD = process.env.QUAY_PASSWORD || '';
