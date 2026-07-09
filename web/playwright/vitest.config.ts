import {defineConfig} from 'vitest/config';

export default defineConfig({
  test: {
    environment: 'node',
    include: ['playwright/utils/**/*.test.ts'],
  },
});
