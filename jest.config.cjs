module.exports = {
  transform: { '^.+\\.tsx?$': ['ts-jest', { tsconfig: 'tsconfig.json' }] },
  testEnvironment: 'node',
  testMatch: ['**/tests/**/*.test.ts']
};
