module.exports = {
  testEnvironment: 'node',
  roots: ['<rootDir>/test', '<rootDir>/snapshot_test'],
  testMatch: ['**/*.test.ts'],
  transform: {
    '^.+\\.tsx?$': 'ts-jest'
  }
};
