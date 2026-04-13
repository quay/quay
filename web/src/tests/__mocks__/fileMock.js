// Stub for binary/static assets (SVG, images, CSS) in Jest tests.
// Returning an empty string keeps all tests that simply import these files
// from crashing; for tests that need to assert on a specific asset, use
// jest.mock('<path>', () => '<expected-value>') to override this stub.
module.exports = '';
