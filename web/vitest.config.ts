import {defineConfig} from 'vitest/config';
import path from 'path';

export default defineConfig({
  plugins: [
    {
      name: 'stub-assets',
      transform(_code: string, id: string) {
        if (/\.(svg|png|jpe?g|gif|webp|ico|ttf|eot|woff2?)(\?.*)?$/i.test(id)) {
          return {code: 'export default ""', map: null};
        }
      },
    },
  ],
  resolve: {
    alias: {
      src: path.resolve(__dirname, './src'),
    },
  },
  test: {
    environment: 'happy-dom',
    globals: true,
    setupFiles: ['./vitest.setup.ts'],
    include: ['src/**/*.test.{ts,tsx}'],
    exclude: ['node_modules', 'dist', 'cypress', 'playwright'],
    css: false,
    clearMocks: true,
    restoreMocks: true,
    coverage: {
      provider: 'v8',
      reporter: ['text', 'lcov', 'json-summary'],
      include: ['src/**/*.{ts,tsx}'],
      exclude: ['src/**/*.test.{ts,tsx}', 'src/tests/**', 'src/index.tsx'],
    },
  },
});
