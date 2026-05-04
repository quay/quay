/**
 * Global configuration for Playwright tests
 */

// Backend API URL (registry + API)
export const API_URL =
  process.env.REACT_QUAY_APP_API_URL || 'http://localhost:8080';

// Frontend URL
export const BASE_URL =
  process.env.PLAYWRIGHT_BASE_URL || 'http://localhost:9000';
