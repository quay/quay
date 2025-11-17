---
allowed-tools: Bash(jira:*), Bash(.claude/scripts/download-jira-attachments.sh:*), mcp__playwright__browser_navigate, mcp__playwright__browser_snapshot, mcp__playwright__browser_click, mcp__playwright__browser_type, mcp__playwright__browser_fill_form, mcp__playwright__browser_take_screenshot, mcp__playwright__browser_wait_for, mcp__playwright__browser_press_key, mcp__playwright__browser_console_messages, Read, Glob, Grep, TodoWrite
argument-hint: <issue-key>
description: Systematically plan a bug or feature based on a JIRA issue
---

# Create Plan from Issue

Systematically analyze a JIRA issue and create an actionable implementation plan. This command uses a **modular phase-based approach** that branches based on issue type (UI vs Backend).

## Issue Key

The JIRA issue to plan: `$ARGUMENTS`

---

## Phase 1: Discovery (All Issues)

### Step 1: Fetch Issue Details

Retrieve the full issue information from JIRA:

```bash
jira issue view $ARGUMENTS
```

**Extract key information:**
- Issue type (Bug, Story, Task, etc.)
- Summary and description
- Component (ui, api, data, etc.)
- Priority
- Labels
- Comments with additional context

### Step 2: Download Attachments

Download any attachments from the issue:

```bash
.claude/scripts/download-jira-attachments.sh $ARGUMENTS
```

This script will:
- Check if the issue has attachments
- Download them to `.claude/attachments/$ARGUMENTS/`
- Display file types to help identify their purpose

**Common attachment types:**
- Screenshots/Images: Visual bugs or mockups
- Architecture diagrams: Design documentation
- Log files: Error traces or debugging information
- Test files: Reproduction cases or examples

### Step 3: Classify the Issue

Analyze the issue to determine if it's **UI** or **Backend**, considering both description and attachments:

**UI Issue Indicators:**
- Component: `ui` or `web`
- Keywords: rendering, display, UI, interface, button, form, modal, table, layout, styling, visual, PatternFly, React, Angular
- Issue describes visual or interaction problems
- Has screenshot/mockup attachments

**Backend Issue Indicators:**
- Component: `api`, `data`, `auth`, `endpoints`, `workers`, `buildman`, `storage`
- Keywords: API, endpoint, database, authentication, background job, storage, worker, migration, ORM, SQL
- Has log files or stack traces attached
- Describes data processing, API behavior, or system operations

**Decision Point:** Based on classification, proceed to either **Phase 2-UI** or **Phase 2-Backend**.

---

## Phase 2: Type-Specific Preparation

### Phase 2-UI: UI Issue Preparation

**If the issue is UI-related**, prepare the UI development environment:

1. **Set Playwright Context:**
   - App URL: `http://localhost:9000`
   - Test credentials: `user1` / `password`
   - Be prepared to navigate UI, take screenshots, and check console

2. **Identify UI Scope:**
   - Which pages/routes are affected?
   - Which PatternFly components are involved?
   - Is this an Angular port or new feature?

**Proceed to Phase 3: UI Workflows**

### Phase 2-Backend: Backend Issue Preparation

**If the issue is backend-related**, prepare the backend investigation:

1. **Identify Affected Subsystems:**
   - **API Endpoints** (`endpoints/`): REST API routes
   - **Data Layer** (`data/`): Database models and queries
   - **Workers** (`workers/`): Background job processors
   - **Authentication** (`auth/`): Auth mechanisms
   - **Storage** (`storage/`): Storage backend operations
   - **Build System** (`buildman/`): Container build orchestration

2. **Prepare for Analysis:**
   - Review attached log files for stack traces
   - Identify error patterns or exceptions
   - Note database tables or models mentioned
   - Check if workers or background jobs are involved

3. **Locate Entry Points:**
   - API endpoint paths (e.g., `/api/v1/repository/`)
   - Worker class names
   - Database model classes
   - Configuration keys

**Proceed to Phase 3: Backend Workflows**

---

## Phase 3: Deep Planning (Type-Specific Workflows)

### Phase 3-UI: UI Workflows

Choose the appropriate UI workflow based on issue type:

#### 3A-UI: UI Bug Planning

**When to use:** Issue type is Bug and classified as UI

1. **Understand the Bug:**
   - What is the expected behavior?
   - What is the actual behavior?
   - Steps to reproduce (if provided)
   - Affected UI components or pages
   - Review attached screenshots to visualize the issue

2. **Create Reproduction Plan with Playwright:**
   - Navigate to `http://localhost:9000`
   - Login with `user1` / `password` if needed
   - Navigate to the affected page/component
   - Perform actions to reproduce the bug
   - Take screenshots and snapshots to document the issue
   - Check browser console for errors using `browser_console_messages`

3. **Locate Relevant Code:**
   - Search for related components in `web/src/`
   - Identify the route or component files
   - Look for related test files in `web/cypress/e2e/`
   - Check for API hooks in `web/src/hooks/`

4. **Create TodoList:**
   ```
   - Reproduce bug with Playwright
   - Locate source code for affected component
   - Identify root cause (state management, props, rendering, etc.)
   - Implement fix
   - Add or update Cypress tests
   - Verify fix with Playwright
   ```

**Proceed to Phase 4**

#### 3B-UI: Angular to React Port

**When to use:** Issue mentions Angular, port, migrate, or "new UI"

1. **Confirm Angular Port:**
   - Look for references to Angular UI in description/comments
   - Search for keywords: "port", "migrate", "current UI", "new UI", "Angular"
   - Locate the Angular component for reference (legacy codebase)
   - Review attached mockups or design screenshots if available

2. **Research PatternFly Components:**
   - Identify which PatternFly components are needed
   - Review existing usage in codebase for patterns
   - Check PatternFly documentation for component props and patterns

3. **Locate Similar React Components:**
   - Search for similar patterns in `web/src/routes/`
   - Identify reusable components in `web/src/components/`
   - Check existing tests for similar features in `web/cypress/e2e/`
   - Review API integration patterns in `web/src/hooks/`

4. **Create TodoList:**
   ```
   - Research Angular implementation (locate source code)
   - Identify PatternFly components needed
   - Design React component structure (pages, components, hooks)
   - Implement React components following frontend patterns
   - Add routing with TanStack Router (if new page)
   - Implement API integration with useSuspenseQuery
   - Write Cypress e2e tests
   - Verify with Playwright manual testing
   ```

**Proceed to Phase 4**

#### 3C-UI: New UI Feature

**When to use:** Issue is Story/Task for new UI functionality (not an Angular port)

1. **Design the Feature:**
   - Review attached mockups or design documents
   - What UI components are needed?
   - What user interactions are required?
   - What API endpoints are needed (if any)?
   - What state management is required?
   - Accessibility considerations?

2. **Locate Integration Points:**
   - Where does this fit in navigation/routing?
   - What existing components can be reused?
   - What API calls are needed?
   - What data transformations are required?

3. **Create TodoList:**
   ```
   - Identify PatternFly components needed
   - Design component architecture (pages, components, hooks)
   - Implement React components with TypeScript
   - Add routing/navigation with TanStack Router
   - Implement API integration with useSuspenseQuery
   - Add proper error boundaries and loading states
   - Write Cypress e2e tests
   - Manual testing with Playwright
   ```

**Proceed to Phase 4**

---

### Phase 3-Backend: Backend Workflows

Choose the appropriate backend workflow based on issue type:

#### 3A-Backend: Backend Bug Planning

**When to use:** Issue type is Bug and classified as Backend

1. **Analyze the Error:**
   - Review attached log files or stack traces
   - Identify error type (exception, timeout, data corruption, etc.)
   - Note affected endpoints, models, or workers
   - Check error frequency and conditions

2. **Locate Affected Code:**

   **For API bugs:**
   - Search for endpoint definitions in `endpoints/` (e.g., `endpoints/api/repository.py`)
   - Find blueprint registration in `endpoints/api/__init__.py`
   - Check authentication decorators and permissions

   **For data layer bugs:**
   - Locate database models in `data/database.py`
   - Find business logic in `data/model/`
   - Check query performance and indexes
   - Review caching layer in `data/cache/`

   **For worker bugs:**
   - Find worker class in `workers/` (e.g., `workers/repositorygcworker.py`)
   - Check queue operations and job handling
   - Review worker-specific configuration
   - Trace worker initialization in `workers/worker.py`

3. **Reproduce the Issue:**
   - Create minimal reproduction case
   - Check test coverage for affected code
   - Identify missing validation or edge cases
   - Review related configuration in `config.py`

4. **Create TodoList:**
   ```
   - Analyze error logs and stack traces
   - Locate affected code (endpoint/model/worker)
   - Create reproduction test case
   - Identify root cause (SQL query, auth logic, race condition, etc.)
   - Implement fix with proper error handling
   - Add unit tests for the fix
   - Add integration tests if multiple components involved
   - Test manually with local development environment
   - Verify no performance regression
   ```

**Proceed to Phase 4**

#### 3B-Backend: Backend Feature Planning

**When to use:** Issue is Story/Task for new backend functionality

1. **Design API/Data Changes:**

   **For new endpoints:**
   - Define API route and HTTP methods
   - Design request/response schemas
   - Plan authentication and authorization
   - Consider rate limiting and pagination

   **For data model changes:**
   - Design database schema changes
   - Plan migration strategy (Alembic)
   - Consider backward compatibility
   - Plan indexes for query performance

   **For new workers:**
   - Define worker responsibilities
   - Design job queue structure
   - Plan failure handling and retries
   - Consider worker scaling

2. **Locate Integration Points:**
   - Which existing endpoints interact with this feature?
   - What database tables/models are involved?
   - What storage operations are needed?
   - What authentication mechanisms apply?
   - What configuration is needed?
   - Does the config-tool schema need updates for validation?

3. **Plan Database Migrations:**
   - Identify schema changes needed
   - Plan migration steps (add columns, tables, indexes)
   - Consider data backfill requirements
   - Plan rollback strategy

4. **Create TodoList:**
   ```
   - Design API endpoints and request/response schemas
   - Design database schema changes
   - Update config-tool schema if new configuration options needed
   - Create Alembic migration for schema changes
   - Implement data models in data/database.py
   - Implement business logic in data/model/
   - Implement API endpoints in endpoints/
   - Add authentication and authorization checks
   - Implement worker if background processing needed
   - Add caching layer if needed
   - Write unit tests for models and business logic
   - Write API integration tests
   - Write worker tests if applicable
   - Test migration on clean database
   - Test config-tool validation with new configuration
   - Test manually with local development environment
   ```

**Proceed to Phase 4**

---

## Phase 4: Final Steps (All Issues)

### Step 4: Execute Research Phase

Based on your TodoList, gather context:

**For UI issues:**
- Read existing component implementations
- Check similar test patterns in Cypress
- Review routing structure
- Check existing PatternFly component usage

**For backend issues:**
- Read existing endpoint implementations
- Check database schema in `data/database.py`
- Review existing tests for patterns
- Check related configuration in `config.py`
- Review worker base class if applicable

### Step 5: Refine TodoList

After research, update your TodoList with:
- Specific file paths discovered during research
- Additional tasks uncovered
- Proper task ordering
- Dependencies between tasks

Ensure each task has both `content` and `activeForm`.

---

## Key Locations

### Frontend (UI Issues)
- **React UI source**: `web/src/`
- **Routes**: `web/src/routes/`
- **Reusable components**: `web/src/components/`
- **API hooks**: `web/src/hooks/`
- **Cypress tests**: `web/cypress/e2e/`
- **App URL**: `http://localhost:9000`
- **Test credentials**: `user1` / `password`

### Backend (API/Data Issues)
- **API endpoints**: `endpoints/` (versioned in `v1/`, `v2/`, etc.)
- **Data models**: `data/database.py`
- **Business logic**: `data/model/`
- **Workers**: `workers/`
- **Authentication**: `auth/`
- **Storage**: `storage/`
- **Build system**: `buildman/`
- **Configuration**: `config.py`
- **Config-tool schema**: `config-tool/` (validates configuration files)
- **Migrations**: `data/migrations/versions/`

---

## Tips

### General
- Always create a TodoList to track planning and implementation
- Update TodoList as you discover new information
- Mark tasks in_progress and completed promptly
- Include both unit tests and integration/e2e tests

### UI-Specific
- Use Playwright to verify UI bugs and test fixes
- Check existing similar features for patterns
- Consider accessibility (ARIA labels, keyboard nav)
- For Angular ports, find the Angular component first

### Backend-Specific
- Review log files carefully for stack traces
- Check database indexes for query performance
- Consider migration rollback strategy
- Test with both PostgreSQL and MySQL if applicable
- Review worker queue behavior for background jobs
- Check configuration in both code and deployment configs

---

## Example Usage

```
/create-plan-from-issue PROJQUAY-1234
```

This will:
1. Fetch PROJQUAY-1234 from JIRA
2. Download any attachments
3. Classify as UI or Backend issue
4. Follow the appropriate workflow branch
5. Create a systematic implementation plan
6. Set up a TodoList to track progress
