module.exports = {
  env: {
    browser: true,
    node: true,
    es2021: true,
    jest: true,
  },
  extends: [
    'eslint:recommended',
    'plugin:@typescript-eslint/recommended',
    'plugin:react/recommended',
    'prettier',
  ],
  parser: '@typescript-eslint/parser',
  parserOptions: {
    ecmaFeatures: {
      jsx: true,
    },
  },
  plugins: ['import', 'react', '@typescript-eslint', 'prettier'],
  ignorePatterns: ['*.md', '**/*.css', '**/*.scss', '*.svg', '*.png', '*.html'],
  rules: {
    'react/react-in-jsx-scope': 'off',
    'prettier/prettier': ['error'],
    '@typescript-eslint/no-var-requires': 'off',
    'import/no-unresolved': 'error',
    'import/prefer-default-export': 'off',
    'import/extensions': [
      'error',
      'ignorePackages',
      {ts: 'never', tsx: 'never'},
    ],
    'react/jsx-filename-extension': [
      2,
      {extensions: ['.js', '.jsx', '.ts', '.tsx']},
    ],
  },
  settings: {
    'import/resolver': {
      typescript: {
        alwaysTryTypes: true,
        project: `${__dirname}/tsconfig.json`,
      },
    },
    react: {
      version: 'detect',
    },
  },
};
