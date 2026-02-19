module.exports = {
  transform: { '^.+\\.tsx?$': ['ts-jest', { tsconfig: 'tsconfig.json', useESM: true }] },
  testEnvironment: 'node',
  testMatch: ['**/tests/**/*.test.ts'],
  moduleNameMapper: {
    '^(\\.{1,2}/.*)\\.js$': '$1',
  },
  extensionsToTreatAsEsm: ['.ts'],
};
