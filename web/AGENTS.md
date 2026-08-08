# AGENTS.md

AI-optimized guide for working with Quay's React frontend.

## Project Overview

Quay container registry React UI - replaces legacy AngularJS interface. Runs as standalone SPA or OpenShift Console plugin.

**Stack:** React 18, TypeScript, PatternFly 5, React Query v4, React Router v6, Axios

**Legacy Migration:** Migrating from Recoil → React Query (server state) + Context API (UI state). Avoid Recoil for new code.

**Backend:** Flask API at `http://localhost:8080`, proxied via webpack-dev-server

**API Routes:** `/api/v1/*`, `/csrf_token`, `/config`, `/oauth` (NOT `/api/form/route` format)

## Directory Structure

```tree
web/
├── src/
│   ├── routes/              # Top-level page components (React Router v6)
│   │   ├── StandaloneMain.tsx    # Main layout + routing
│   │   ├── PluginMain.tsx        # OpenShift Console plugin entry
│   │   ├── NavigationPath.tsx    # Route path constants
│   │   ├── OrganizationsList/
│   │   ├── RepositoriesList/
│   │   ├── RepositoryDetails/
│   │   └── ...
│   ├── components/          # Reusable UI components
│   │   ├── header/          # QuayHeader
│   │   ├── sidebar/         # QuaySidebar
│   │   ├── footer/          # QuayFooter
│   │   ├── modals/          # Reusable modals
│   │   ├── toolbar/         # Table toolbars
│   │   └── errors/          # ErrorBoundary, error pages
│   ├── hooks/               # Custom React hooks (UseRepositories.ts, UseOrganizations.ts)
│   ├── resources/           # API client layer (Axios HTTP calls)
│   │   ├── RepositoryResource.ts
│   │   ├── OrganizationResource.ts
│   │   └── ErrorHandling.ts
│   ├── contexts/            # React Context providers (SidebarContext, AlertContext, AuthContext)
│   ├── atoms/               # Legacy Recoil atoms (avoid for new code)
│   ├── libs/                # Utilities
│   │   ├── axios.ts         # Configured Axios instance (CSRF tokens)
│   │   └── utils.ts         # Common utilities
│   └── assets/              # Static assets
├── webpack.dev.js           # Dev server + proxy config
├── webpack.prod.js          # Production build
└── webpack.plugin.js        # OpenShift Console plugin build
```

## Development Commands

```bash
# Local Development
pnpm install             # Install dependencies
pnpm start               # Dev server on http://localhost:9000 (hot-reload)
MOCK_API=true pnpm start # Mock API (no backend required)
pnpm run format          # Prettier formatting

# Unit Testing (Vitest + React Testing Library)
pnpm test                # Run all unit tests
pnpm run test:watch      # Watch mode for development
pnpm run test:coverage   # Run with coverage report
pnpm vitest run src/libs/utils.test.ts  # Single test file

# E2E Testing (Playwright)
pnpm run test:e2e        # Run all Playwright e2e tests
pnpm run test:e2e:ui     # Playwright UI mode
pnpm run test:api        # API-only tests

# Building
pnpm run build           # Production build → dist/
pnpm run build-plugin    # OpenShift Console plugin build
pnpm run start-plugin    # Plugin dev server
```

## Quay-Specific Patterns

### Data Flow

**Standard Pattern:**
```text
Component → Hook (src/hooks/UseX.ts) → Resource (src/resources/XResource.ts) → Axios → Quay API
```

Example:
```typescript
// Component uses hook
import { useRepositories } from 'src/hooks/UseRepositories';

// Hook uses React Query + Resource
const { data } = useQuery(['repos'], () => RepositoryResource.getRepositories());

// Resource makes HTTP call
export const RepositoryResource = {
  getRepositories: () => axios.get('/api/v1/repositories')
};
```

**Modern Pattern (New Code):**
- Use `useSuspenseQuery` directly in components
- Wrap component in `<SuspenseLoader>` boundary
- No manual `isLoading` checks

### Backend Integration

**API Client:** `src/libs/axios.ts`
- Configured Axios instance with CSRF token interceptor
- Auth interceptors for cookie/token handling
- Error handling middleware

**Proxy Routes (webpack.dev.js):**
- `/api/v1/*` → Backend (e.g., `http://localhost:8080`)
- `/csrf_token` → Backend
- `/config` → Backend
- `/oauth` → Backend

### Routing

**React Router v6** in `src/routes/StandaloneMain.tsx`:
- Nested routes with lazy loading
- Route paths in `NavigationPath.tsx`
- Breadcrumbs via `use-react-router-breadcrumbs`

Example:
```typescript
import { lazy } from 'react';
const RepositoriesList = lazy(() => import('./RepositoriesList'));

// In Routes
<Route path="/repository" element={<SuspenseLoader><RepositoriesList /></SuspenseLoader>} />
```

### State Management

**Server State:** React Query (`useSuspenseQuery`, `useMutation`)
- Repositories, organizations, users, tags
- Automatic caching, refetching, invalidation

**UI State:** React Context
- `SidebarContext`: Sidebar open/closed
- `AlertContext`: Toast notifications
- `AuthContext`: Current user

**Legacy:** Recoil atoms in `src/atoms/` (avoid for new code)

### Write Operation Authorization

Components that render mutation controls (create, update, delete buttons, kebab actions, forms that POST/PUT/DELETE) **must** gate those controls on the user's write authorization. Two conditions block writes: the user is a **global readonly superuser**, or the registry is in **readonly mode**.

> **Background:** See `agent_docs/global_readonly_superuser.md` for the backend implementation of global readonly superusers and how the API returns 403 for write operations.

**Standard `canManage` pattern:**

```typescript
import { useCurrentUser } from 'src/hooks/UseCurrentUser';
import { useQuayConfig } from 'src/hooks/UseQuayConfig';

// Inside the component:
const { user } = useCurrentUser();
const quayConfig = useQuayConfig();

const canManage =
  user != null &&
  quayConfig != null &&
  user.global_readonly_super_user !== true &&
  quayConfig.registry_state !== 'readonly';
```

**Rules:**

1. Every new component with mutation controls must derive `canManage` using the pattern above.
2. **Hide** mutation controls when `canManage` is `false` — do not merely disable them. The backend rejects these operations with 403, and disabled buttons produce confusing generic error messages.
3. Use conditional rendering to wrap mutation UI:
   ```typescript
   {canManage && (
     <Button onClick={handleDelete}>Delete</Button>
   )}
   ```
4. For table action columns, conditionally render the entire actions column header and cells:
   ```typescript
   {canManage && <Th screenReaderText="Actions" />}
   ```

**Required hooks:**

| Hook | Import | Provides |
|------|--------|----------|
| `useCurrentUser()` | `src/hooks/UseCurrentUser` | `user.global_readonly_super_user` flag |
| `useQuayConfig()` | `src/hooks/UseQuayConfig` | `quayConfig.registry_state` value |

## Critical Rules

1. **No Early Returns with Loading Spinners**
   ```typescript
   // ❌ WRONG - Causes layout shift
   if (isLoading) return <Spinner />;

   // ✅ CORRECT - Use Suspense
   <SuspenseLoader>
     <Component />  {/* Uses useSuspenseQuery */}
   </SuspenseLoader>
   ```

2. **PatternFly Components**
   - Use PatternFly 5 components (not MUI, not custom)
   - Alert, Card, Button, Table, Modal, Toolbar, etc.
   - Follow PatternFly design patterns

3. **TypeScript Standards**
   - `React.FC<Props>` for components
   - Explicit return types on functions
   - Type imports: `import type { User } from 'src/types/user'`
   - No `any` types

4. **React Query Patterns**
   - New code: `useSuspenseQuery` (no loading states)
   - Legacy code: `useQuery` with `isLoading` checks
   - Mutations: `useMutation` with cache invalidation
   - Query keys: `['resource', ...params]`

## Quick Reference

### Common Imports

```typescript
import React, { useState, useCallback, useMemo } from 'react';
import { useSuspenseQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { useNavigate } from 'react-router-dom';
import {
  Card, CardBody, Button, Alert, Toolbar, ToolbarContent,
  Table, Thead, Tbody, Tr, Th, Td
} from '@patternfly/react-core';
import { SuspenseLoader } from 'src/components/SuspenseLoader';
import type { Repository } from 'src/types/Repository';
```

### Component Checklist

- [ ] Use `React.FC<Props>` with TypeScript
- [ ] Lazy load if heavy: `React.lazy(() => import())`
- [ ] Wrap in `<SuspenseLoader>` for loading states
- [ ] Use `useSuspenseQuery` for data fetching
- [ ] Use `useCallback` for event handlers passed to children
- [ ] Use `useMemo` for expensive computations
- [ ] Derive `canManage` and hide mutation controls for readonly users (see Write Operation Authorization)
- [ ] Default export at bottom

### Testing

**Unit Tests:** Vitest + React Testing Library + happy-dom
- Co-located with source files: `Component.test.tsx` next to `Component.tsx`
- Config: `vitest.config.ts`, setup: `vitest.setup.ts`
- Custom render wrapper: `src/test-utils.tsx` (provides QueryClient, RecoilRoot, UIProvider)
- Mock API calls with `axios-mock-adapter` (already in devDependencies)
- Use `getByRole` queries for accessibility-focused testing
- See `agent_docs/web-unit-test-roadmap.md` for coverage roadmap

**What to unit test (priority order):**
1. Pure utility functions (`src/libs/`)
2. Data transformation logic (`src/resources/` helpers)
3. Custom hooks (`src/hooks/`) with `renderHook`
4. Components with branching/validation logic

**What NOT to unit test (use Playwright E2E instead):**
- Routing, page layouts, auth flows, CSS

**E2E Tests:** Playwright
- Located in `playwright/e2e/`
- Config: `playwright.config.ts`
- Fixtures: `playwright/fixtures.ts`
- Requires running Quay stack (see CI workflow)

### Environment Variables

- `MOCK_API=true`: Use mocked API
- `REACT_QUAY_APP_API_URL`: Override backend URL
- `NODE_ENV`: development/production (set by webpack)

### Performance Tips

- Lazy load routes and heavy components
- Use `useMemo` for filter/sort/map operations on large arrays
- Use `useCallback` for event handlers passed as props
- Debounce search inputs (300-500ms)
- Clean up effects to prevent memory leaks
