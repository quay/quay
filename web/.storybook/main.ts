import type {StorybookConfig} from '@storybook/react-vite';
import tsconfigPaths from 'vite-tsconfig-paths';

const config: StorybookConfig = {
  stories: ['../src/**/*.stories.@(ts|tsx)'],
  addons: [
    '@storybook/addon-essentials',
    '@storybook/addon-a11y',
    '@storybook/addon-interactions',
  ],
  framework: {
    name: '@storybook/react-vite',
    options: {},
  },
  viteFinal(config) {
    config.plugins = [...(config.plugins || []), tsconfigPaths()];
    config.define = {
      ...config.define,
      'process.env.MOCK_API': JSON.stringify('false'),
      'process.env.REACT_QUAY_APP_API_URL': JSON.stringify(
        'http://localhost:8080',
      ),
      'process.env.REACT_APP_QUAY_DOMAIN': JSON.stringify('localhost'),
    };
    return config;
  },
};

export default config;
