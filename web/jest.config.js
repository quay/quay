/** @type {import('ts-jest').JestConfigWithTsJest} */
module.exports = {
  preset: 'ts-jest',
  testEnvironment: 'node',
  moduleNameMapper: {
    // Map src/ path alias to actual directory
    '^src/(.*)$': '<rootDir>/src/$1',
    // Stub out SVG, image, and CSS imports
    '\\.svg$': '<rootDir>/src/tests/__mocks__/fileMock.js',
    '\\.(css|less|scss|sass)$': '<rootDir>/src/tests/__mocks__/fileMock.js',
    '\\.(png|jpg|jpeg|gif|ico|webp)$':
      '<rootDir>/src/tests/__mocks__/fileMock.js',
  },
  transform: {
    '^.+\\.[tj]sx?$': [
      'ts-jest',
      {
        tsconfig: 'tsconfig.test.json',
        diagnostics: {ignoreCodes: [2307]},
      },
    ],
  },
  testMatch: [
    '<rootDir>/src/**/__tests__/**/*.[jt]s?(x)',
    '<rootDir>/src/**/?(*.)+(spec|test).[tj]s?(x)',
  ],
  testPathIgnorePatterns: ['/node_modules/', '/playwright/'],
  globals: {},
};
