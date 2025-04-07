module.exports = {
  testEnvironment: 'node',
  roots: ['<rootDir>/snapshot_test'],
  testMatch: ['**/*.test.ts'],
  transform: {
    '^.+\\.tsx?$': 'ts-jest'
  }
};
