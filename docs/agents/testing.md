# Testing - Agent Context

For general testing commands and setup, see `TESTING.md` at the repo root.

This document covers patterns for writing tests.

## Backend Test Patterns

### Basic Test with Database

```python
import pytest
from test.fixtures import *

def test_example(initialized_db):
    """Test with database fixture."""
    from data.model.user import get_user_by_username
    user = get_user_by_username("devtable")
    assert user is not None
```

See: `test/fixtures.py`

### E2E Test Marker

```python
@pytest.mark.e2e
def test_e2e_example():
    """End-to-end test (excluded from unit-test target)."""
    pass
```

### Parametrized Tests

```python
@pytest.mark.parametrize("input,expected", [
    ("a", 1),
    ("b", 2),
])
def test_parametrized(input, expected):
    pass
```

### Mocking

```python
from unittest.mock import patch, MagicMock

@patch('data.model.repository.get_repository')
def test_with_mock(mock_get_repo):
    mock_get_repo.return_value = MagicMock(name='test-repo')
    # test code here
```

### Mocking Feature Flags

```python
from features import FeatureNameValue
from unittest.mock import patch

def test_with_feature():
    with patch('features.QUOTA_MANAGEMENT', FeatureNameValue('QUOTA_MANAGEMENT', True)):
        # test with feature enabled
        pass
```

### Common Fixtures

| Fixture | Purpose |
|---------|---------|
| `initialized_db` | Database with schema, no data |
| `app` | Flask test app |
| `app_config` | Test configuration dict |
| `client` | Flask test client |

See: `test/fixtures.py`

## Frontend Test Patterns

### React Component Test

```tsx
import { render, screen } from '@testing-library/react';
import { Component } from './Component';

test('renders correctly', () => {
  render(<Component />);
  expect(screen.getByText('Expected Text')).toBeInTheDocument();
});
```

### With User Interaction

```tsx
import { render, screen } from '@testing-library/react';
import userEvent from '@testing-library/user-event';

test('handles click', async () => {
  const user = userEvent.setup();
  render(<Button onClick={mockFn} />);

  await user.click(screen.getByRole('button'));
  expect(mockFn).toHaveBeenCalled();
});
```

### Mocking API Calls

```tsx
import { rest } from 'msw';
import { setupServer } from 'msw/node';

const server = setupServer(
  rest.get('/api/v1/user/', (req, res, ctx) => {
    return res(ctx.json({ username: 'testuser' }));
  })
);

beforeAll(() => server.listen());
afterEach(() => server.resetHandlers());
afterAll(() => server.close());
```

## Cypress E2E Patterns

### Basic Test

```typescript
describe('Feature', () => {
  beforeEach(() => {
    cy.visit('/');
  });

  it('should display element', () => {
    cy.get('[data-testid="element"]').should('be.visible');
  });
});
```

### With API Interception

```typescript
it('handles API response', () => {
  cy.intercept('GET', '/api/v1/repository/*', {
    fixture: 'repository.json'
  }).as('getRepo');

  cy.visit('/repository/org/repo');
  cy.wait('@getRepo');
  cy.get('.repo-name').should('contain', 'repo');
});
```

### Login Helper

```typescript
Cypress.Commands.add('login', (username, password) => {
  cy.session([username, password], () => {
    cy.visit('/signin');
    cy.get('#username').type(username);
    cy.get('#password').type(password);
    cy.get('button[type="submit"]').click();
    cy.url().should('not.include', '/signin');
  });
});
```

See: `web/cypress/support/`, `web/cypress/e2e/`

## Test File Locations

| Component | Test Location |
|-----------|---------------|
| API endpoints | `endpoints/api/test/` |
| V2 registry | `endpoints/v2/test/` |
| Data models | `data/model/test/` |
| Registry model | `data/registry_model/test/` |
| Authentication | `auth/test/` |
| Build manager | `buildman/test/` |
| Registry protocol | `test/registry/` |
| Integration | `test/integration/` |
| Frontend components | `web/src/**/*.test.tsx` |
| Frontend e2e | `web/cypress/e2e/` |
