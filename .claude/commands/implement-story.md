# Implement JIRA Story

**EXECUTE IMMEDIATELY**: Implement JIRA story `$ARGUMENTS`. Do NOT print examples or describe what you will do - actually DO each step.

**⚠️ CRITICAL**: Tests are MANDATORY for all story implementations unless explicitly exempted.

---

## EXECUTE THESE STEPS NOW FOR: $ARGUMENTS

**START NOW**: Run `jira issue view $ARGUMENTS` immediately. Do not describe what you will do.

### Step 1: Fetch Story from JIRA

Run this command NOW:

```bash
jira issue view $ARGUMENTS
```

**Extract from JIRA output:**
- **Story Title** - The summary field
- **Story Description** - The description section (should contain implementation details)
- **Story Type** - The issue type
- **Parent Epic** - The epic link field (if present)
- **Status** - Current status
- **Assignee** - Who it's assigned to

**Save story content:**
Create `.claude/implementation/<story-key>-context.md` with:
- Story title as H1
- Full story description from JIRA
- Link to JIRA issue: `https://issues.redhat.com/browse/<story-key>`

### Step 2: Fetch Parent Epic (if exists)

If the story has a parent epic, fetch it:

```bash
jira issue view <epic-key>
```

**Save epic content:**
Append to `.claude/implementation/<story-key>-context.md`:
- Epic title
- Epic description
- Epic scope (in-scope and out-of-scope)
- Link to epic

This provides broader context for implementation.

### Step 3: Analyze Requirements and Detect Story Type

**First, determine if this is a UI story by checking for these indicators:**

**UI Story Indicators:**
- Story title contains: `[UI]`, `[Frontend]`, `UI Component`, `User Interface`
- Files to create/modify include paths like:
  - `web/src/`, `frontend/`, `ui/`, `static/js/`
  - Files ending in `.tsx`, `.jsx`, `.vue`, `.svelte`
  - Component files, routes, pages
- Acceptance criteria mention:
  - "User can click/see/interact"
  - "Form validation", "Button", "Dialog", "Modal"
  - "Responsive design", "Mobile view"
  - "E2E tests", "Playwright tests", "Cypress tests"
- Technology mentions: React, Vue, Angular, TypeScript, PatternFly, Material-UI

**If UI story detected:**
- Set `STORY_TYPE = "UI"`
- Follow the **UI-Specific Workflow** (see Section: UI Story Workflow below)
- Use UI testing frameworks (Playwright, Cypress, React Testing Library)

**If backend/API story:**
- Set `STORY_TYPE = "BACKEND"`
- Follow standard workflow with Python/pytest testing

**If full-stack story (both UI and backend):**
- Set `STORY_TYPE = "FULLSTACK"`
- Implement backend first, then UI
- Create tests for both layers

From the story description, extract:

1. **Summary** - What needs to be implemented
2. **Acceptance Criteria** - Specific testable requirements
3. **Technical Requirements** - Files to create/modify, patterns to follow
4. **Implementation Notes** - Specific guidance and patterns
5. **Dependencies** - Other stories that must be completed first
6. **Testing Requirements** - Unit tests, integration tests needed
7. **Definition of Done** - Checklist for completion
8. **Story Type** - UI, Backend, or Fullstack

### Step 4: Check Dependencies

If the story has dependencies on other stories:
1. Verify those stories are completed in JIRA
2. If dependencies are not complete, ask user:
   - "Story <story-key> depends on <dependency-keys>. These are not yet complete. Do you want to:"
     - "Continue anyway (may require manual fixes later)"
     - "Implement dependencies first"
     - "Cancel"

### Step 5: Create Implementation Plan

Based on the story requirements, create an implementation plan:

1. **List all files to create** - With file paths from story
2. **List all files to modify** - With specific changes needed
3. **List all tests to create** - **MANDATORY** - Unit tests, integration tests, E2E tests
4. **Identify patterns to follow** - Reference files from story AND existing test files
5. **Note any migrations needed** - Database migrations, config changes
6. **Estimate scope** - Number of files, complexity

**Plan MUST include test files:**
- For each new model: List specific test files and test cases
- For each new API endpoint: List endpoint tests (happy path + error cases)
- For each new worker: List worker execution tests
- For each new UI component: List interaction tests
- Search for similar existing tests to use as patterns

**Save plan:**
Write the plan to `.claude/implementation/<story-key>-plan.md`

The plan is NOT complete without a detailed test section.

### Step 6: Get User Approval

Display the implementation plan to the user with:
- Summary of changes
- Files to be created
- Files to be modified
- Tests to be added
- Any risks or considerations

Ask user:
- "Ready to implement this story?"
  - "Yes, proceed with implementation"
  - "No, let me review the plan first"
  - "Modify the plan (I'll specify changes)"

### Step 7: Implement Changes

Execute the implementation following the plan:

1. **Create directory structures** - If new directories needed
2. **Create new files** - Following patterns from story
3. **Modify existing files** - Make precise edits based on requirements
4. **Create database migrations** - If required by story
5. **CREATE TEST FILES** - **MANDATORY** - Unit and integration tests (see Testing Requirements below)
6. **Update configuration** - If feature flags or config changes needed

**Use TodoWrite tool** to track progress:
- Break down implementation into tasks from acceptance criteria
- Mark tasks as in_progress and completed as you work
- Ensure all acceptance criteria are addressed

**Implementation Guidelines:**
- Follow patterns referenced in the story (specific file paths)
- Use existing code conventions from the codebase
- Add comprehensive tests as specified in story
- Follow the story's technical requirements exactly
- Reference the epic context for broader architectural decisions

**CRITICAL - Testing Requirements:**

Tests are **MANDATORY** for all story implementations. You MUST create tests unless one of these rare exceptions applies:
- The story is purely documentation (README, guides)
- The story only modifies configuration files (no code changes)
- The story is a pure deletion of deprecated code

**What tests to create:**

1. **For new models/database changes:**
   - Create tests that verify model constraints
   - Test foreign key relationships
   - Test unique constraints
   - Test field validations
   - Test enum values
   - Location: `test/` directory following existing patterns

2. **For new API endpoints:**
   - Create tests for all HTTP methods (GET, POST, PUT, DELETE)
   - Test authentication/authorization
   - Test error cases (400, 401, 403, 404, 500)
   - Test request validation
   - Test response format
   - Location: `test/` directory, often `test_endpoints.py` or endpoint-specific files

3. **For new worker/background jobs:**
   - Create tests for job execution
   - Test error handling and retries
   - Test state transitions
   - Mock external dependencies
   - Location: `test/` directory, worker-specific test files

4. **For new UI components:**
   - Create Playwright or Cypress tests for user interactions
   - Test rendering and state management
   - Test form validation
   - Location: `web/src/` for component tests, `test/` for E2E

5. **For business logic/utilities:**
   - Create unit tests for all public functions
   - Test edge cases and error conditions
   - Test input validation
   - Location: `test/` directory

**How to find test patterns:**
- Search for similar existing tests: `grep -r "test_.*<feature>" test/`
- Look at test files for similar components
- Check `test/conftest.py` for fixtures and test utilities
- Follow the same import patterns and assertion styles

**Before moving to Step 8:**
- ✅ Verify test files have been created
- ✅ Verify tests cover the acceptance criteria
- ✅ Verify tests follow existing patterns
- ❌ DO NOT proceed to Step 8 without creating tests

### Step 8: Run Tests

**MANDATORY STEP** - Do not skip or mark as complete without running tests.

After implementation, run the tests you created:

```bash
# Run the specific tests you created for this story
pytest <test-file-paths> -v

# Example for model tests
pytest test/test_orgmirror_models.py -v

# Example for API endpoint tests
pytest test/test_orgmirror_api.py -v

# Run with coverage to ensure your code is tested
pytest <test-file-paths> --cov=<module-path> --cov-report=term-missing
```

**Test execution is REQUIRED:**
- ✅ All new tests MUST pass
- ✅ All existing tests MUST still pass (run broader test suite if needed)
- ✅ Coverage should be reasonable for new code (aim for >80%)
- ❌ DO NOT mark implementation complete with failing tests
- ❌ DO NOT skip test execution

**If tests fail:**
1. Read the error messages carefully
2. Fix the implementation or test code
3. Re-run tests
4. Repeat until ALL tests pass
5. If tests cannot pass due to environmental issues, document this clearly and ask the user

**If no test framework exists:**
- This is extremely rare for modern projects
- Document this clearly in the summary
- Verify the code works through manual testing
- Recommend setting up a test framework as a follow-up story

### Step 9: Verify Acceptance Criteria

Go through each acceptance criterion from the story:
- [ ] Criterion 1 - Verify implemented
- [ ] Criterion 2 - Verify implemented
- [ ] ...
- [ ] **Tests created** - MANDATORY unless exception applies
- [ ] **All tests passing** - MANDATORY verification

**Verification checklist:**
1. ✅ All story acceptance criteria met
2. ✅ Tests created for new functionality
3. ✅ All new tests passing
4. ✅ Existing tests still passing (no regressions)
5. ✅ Code follows project conventions
6. ✅ No compiler/linter errors

Report any acceptance criteria that could not be met and why.

**If "tests created" or "tests passing" cannot be checked:**
- This is a BLOCKER - implementation is NOT complete
- You must either create/fix the tests OR
- Clearly document why tests cannot be created (very rare exceptions only)
- Get explicit user approval to proceed without tests

### Step 10: Create Summary

Create a summary of the implementation:

**Files Created:**
- List all created files with brief description

**Files Modified:**
- List all modified files with what changed

**Tests Added:** ⭐ **REQUIRED SECTION**
- List all test files created (MUST be present unless rare exception)
- Describe what each test file covers
- Include test execution results (passed/failed counts)
- Include coverage metrics if available
- **If no tests:** Explicitly document why and get user approval

**Test Results:** ⭐ **REQUIRED SECTION**
- Show pytest output or test runner results
- Confirm all tests passing
- Note any skipped tests and why
- Show coverage percentage if available

**Database Changes:**
- List any migrations created

**Configuration Changes:**
- List any config changes

**Acceptance Criteria Met:**
- Checklist of all criteria with status
- **Include "Tests created and passing" as a criterion**

**Next Steps:**
- Any follow-up work needed
- Related stories that should be implemented next
- Any issues encountered that need attention

Save summary to `.claude/implementation/<story-key>-summary.md`

**Summary MUST include test information** - this is not optional.

### Step 11: Update Story Status (Optional)

Ask user if they want to update the JIRA story status:
- "Implementation complete. Update JIRA story status?"
  - "Yes, mark as In Progress → Done"
  - "Yes, mark as In Progress (not quite done yet)"
  - "No, I'll update manually"

If yes:
```bash
jira issue move <story-key> "Done"
```

---

## UI Story Workflow

**This section applies when `STORY_TYPE = "UI"` is detected.**

### UI Story Analysis

When a UI story is detected, perform additional analysis:

1. **Identify UI Framework:**
   - Check `package.json` for React, Vue, Angular, Svelte
   - Check for TypeScript configuration
   - Identify component library (PatternFly, Material-UI, Ant Design, etc.)

2. **Check Existing UI Structure:**
   - Look for similar components to use as patterns
   - Find the routing structure
   - Identify state management approach (Redux, Context, MobX, etc.)
   - Find API integration patterns (hooks, services, etc.)

3. **Verify UI Testing Setup:**
   - Check for Playwright, Cypress, or other E2E framework
   - Check for component testing (React Testing Library, Vue Test Utils)
   - Find existing test patterns for similar components

### UI Implementation Plan

Create a UI-focused implementation plan including:

1. **Component Architecture:**
   - List of React/Vue/Angular components to create
   - Component hierarchy and relationships
   - Props/state design for each component

2. **Routing Changes:**
   - New routes to add
   - Route guards/permissions
   - Navigation updates

3. **State Management:**
   - New state slices/contexts
   - API integration hooks
   - Data flow patterns

4. **Styling:**
   - Component library usage
   - Custom styles needed
   - Responsive design breakpoints

5. **Testing Strategy:**
   - **Component tests** - Unit tests for individual components
   - **Integration tests** - Tests for component interactions
   - **E2E tests** - User workflow tests (MANDATORY for UI stories)
   - Visual regression tests (if applicable)

### UI Implementation Steps

**Step 7-UI: Implement UI Components**

1. **Set up component structure:**
   ```bash
   # Create component directory
   mkdir -p web/src/routes/OrganizationsList/Organization/Tabs/Mirroring
   ```

2. **Create components following existing patterns:**
   - Find similar components in codebase
   - Copy structure and naming conventions
   - Use same imports and component library patterns

3. **Key UI Considerations:**
   - **TypeScript types:** Define interfaces for props and state
   - **Form validation:** Use existing form validation patterns
   - **Error handling:** Show user-friendly error messages
   - **Loading states:** Show spinners/skeletons during API calls
   - **Accessibility:** Proper ARIA labels, keyboard navigation
   - **Responsive:** Mobile, tablet, desktop breakpoints

4. **API Integration:**
   - Create or use existing API hooks
   - Handle loading, error, and success states
   - Implement proper error boundaries

5. **State Management:**
   - Use existing state patterns (Context, Redux, etc.)
   - Keep state minimal and close to usage
   - Avoid prop drilling with proper architecture

**Example Component Structure:**
```typescript
// web/src/routes/OrgSettings/Mirroring/MirrorConfig.tsx
import React, { useState, useEffect } from 'react';
import { useParams } from 'react-router-dom';
import { useFetchOrgMirror, useUpdateOrgMirror } from 'src/hooks/UseOrgMirror';
import { Form, FormGroup, TextInput, Button } from '@patternfly/react-core';

export default function MirrorConfig() {
  const { orgname } = useParams();
  const { mirror, loading, error } = useFetchOrgMirror(orgname);
  const { updateMirror, updating } = useUpdateOrgMirror();

  const [formData, setFormData] = useState({...});
  const [validationErrors, setValidationErrors] = useState({});

  // Component implementation...

  return (
    <Form onSubmit={handleSubmit}>
      {/* Form fields */}
    </Form>
  );
}
```

### UI Testing Requirements

**For UI stories, testing is even MORE critical:**

1. **Component Tests (React Testing Library / Vue Test Utils):**
   - Test component rendering with different props
   - Test user interactions (clicks, typing, form submission)
   - Test conditional rendering (loading, error, success states)
   - Test form validation
   - Mock API calls and external dependencies

   ```typescript
   // web/src/routes/OrgSettings/Mirroring/__tests__/MirrorConfig.test.tsx
   import { render, screen, fireEvent, waitFor } from '@testing-library/react';
   import MirrorConfig from '../MirrorConfig';

   describe('MirrorConfig', () => {
     it('renders form fields', () => {
       render(<MirrorConfig />);
       expect(screen.getByLabelText('Source Registry')).toBeInTheDocument();
     });

     it('validates required fields', async () => {
       render(<MirrorConfig />);
       fireEvent.click(screen.getByText('Save'));
       await waitFor(() => {
         expect(screen.getByText('External reference is required')).toBeInTheDocument();
       });
     });

     it('submits form successfully', async () => {
       // Test implementation
     });
   });
   ```

2. **E2E Tests (Playwright / Cypress) - MANDATORY:**
   - Test complete user workflows
   - Test navigation between pages
   - Test form submission and validation
   - Test error scenarios
   - Test with real API (or mocked API server)

   ```typescript
   // web/e2e/org-mirroring.spec.ts (Playwright)
   import { test, expect } from '@playwright/test';

   test.describe('Organization Mirroring', () => {
     test('admin can create org mirror configuration', async ({ page }) => {
       await page.goto('/organization/testorg/settings');
       await page.click('text=Mirroring');
       await page.fill('[name="external_reference"]', 'harbor.example.com/project');
       await page.selectOption('[name="internal_robot"]', 'testorg+robot');
       await page.fill('[name="sync_interval"]', '86400');
       await page.click('button:has-text("Create Mirror")');

       await expect(page.locator('.success-message')).toContainText('Mirror created successfully');
     });

     test('shows validation errors for invalid input', async ({ page }) => {
       // Test implementation
     });
   });
   ```

3. **API Mock Tests:**
   - Test component behavior with different API responses
   - Test loading states
   - Test error handling
   - Test edge cases

### UI Test Execution

**Step 8-UI: Run UI Tests**

```bash
# Run component tests
npm test -- MirrorConfig.test.tsx

# Run component tests with coverage
npm test -- --coverage MirrorConfig.test.tsx

# Run E2E tests (Playwright)
npx playwright test org-mirroring.spec.ts

# Run E2E tests (Cypress)
npx cypress run --spec "cypress/e2e/org-mirroring.cy.ts"

# Run all tests for the feature
npm test -- --testPathPattern=Mirroring
npx playwright test --grep "Organization Mirroring"
```

**UI Test Requirements:**
- ✅ Component tests MUST pass (unit tests for components)
- ✅ E2E tests MUST pass (user workflow tests)
- ✅ No console errors in browser during tests
- ✅ Accessibility checks pass (if using axe or similar)
- ✅ Visual regression tests pass (if applicable)

### UI-Specific Acceptance Criteria

UI stories should verify:
- [ ] Component renders without errors
- [ ] All interactive elements work (buttons, forms, links)
- [ ] Form validation works correctly
- [ ] Error states display properly
- [ ] Loading states display properly
- [ ] Success states display properly
- [ ] Responsive design works (mobile, tablet, desktop)
- [ ] Accessibility requirements met (ARIA labels, keyboard navigation)
- [ ] E2E tests cover main user workflows
- [ ] Component tests cover all UI states

### UI Implementation Checklist

Before marking UI story complete:

- [ ] **Components created** following existing patterns
- [ ] **TypeScript types** defined for all props and state
- [ ] **API integration** working with proper error handling
- [ ] **Form validation** implemented and tested
- [ ] **Loading states** shown during async operations
- [ ] **Error messages** user-friendly and actionable
- [ ] **Accessibility** - ARIA labels, keyboard navigation
- [ ] **Responsive design** - mobile, tablet, desktop
- [ ] **Component tests** created and passing
- [ ] **E2E tests** created and passing
- [ ] **No console errors** in browser
- [ ] **Code review** - follows project conventions
- [ ] **Visual QA** - UI looks correct in all states

### UI Story Complexity Assessment

**Simple UI Story (1-2 days):**
- Single component modification
- Minor form changes
- Basic styling updates
- Few test cases needed

**Medium UI Story (3-5 days):**
- Multiple related components
- New form with validation
- API integration
- Moderate test coverage needed
- Some routing changes

**Complex UI Story (1-2 weeks):**
- New feature with multiple pages
- Complex state management
- Multiple API integrations
- Extensive test coverage needed
- Routing, navigation changes
- Responsive design across breakpoints

**When to ask for frontend developer:**
- Story involves complex state management (Redux, MobX)
- Story requires deep component library customization
- Story needs advanced CSS/styling (animations, complex layouts)
- Story requires performance optimization (virtualization, lazy loading)
- Story involves build configuration or bundler changes
- You're unfamiliar with the specific frontend framework

### UI Story Summary Requirements

For UI stories, the summary MUST include:

**UI Components Created:**
- List all new components with file paths
- Describe what each component does

**UI Tests Added:**
- Component tests (React Testing Library, etc.)
- E2E tests (Playwright, Cypress)
- Visual regression tests (if applicable)

**UI Test Results:**
- Component test results (passed/failed)
- E2E test results (passed/failed)
- Screenshots of passing E2E tests (if applicable)
- Browser compatibility tested

**Visual Verification:**
- Screenshots of key UI states (empty, loading, success, error)
- Mobile/tablet/desktop screenshots (if responsive)
- Accessibility audit results (if applicable)

**Browser Testing:**
- Tested in Chrome: ✅
- Tested in Firefox: ✅
- Tested in Safari: ✅
- Tested in Edge: ✅

---

## Important Notes

### Story Description Format

The story description should contain these sections (as generated by `/create-stories-from-epic`):
- Summary
- Acceptance Criteria
- Technical Requirements
- Implementation Notes
- Dependencies
- Testing Requirements
- Definition of Done

If the story description is incomplete or doesn't follow this format:
1. Note this to the user
2. Ask if they want you to:
   - "Implement based on available information"
   - "Generate a detailed plan first and get approval"
   - "Cancel - story needs more detail"

### Handling Complex Stories

For complex stories that touch many files:
1. Break down into phases if needed
2. Implement foundational changes first
3. Add features incrementally
4. Test after each phase
5. Keep user informed of progress

### Code Quality

Ensure implementation follows:
- Existing code patterns (as referenced in story)
- Project conventions
- Type safety
- Error handling
- Documentation in code comments where logic isn't self-evident

### Testing Philosophy

**Tests are NOT optional.** They are a core deliverable of every story implementation.

**For UI Stories:** Follow the UI-specific testing requirements (component tests + E2E tests). See "UI Story Workflow" section above.

**For Backend Stories:** Follow Python/pytest testing patterns below.

**Rules:**
1. **Write tests as you implement** - Not after, not as a follow-up story
2. **Tests must pass before marking story complete** - No exceptions
3. **Follow existing test patterns** - Search the codebase for similar tests
4. **Cover the acceptance criteria** - Each criterion should have test coverage
5. **Test both happy path and error cases** - Don't just test success scenarios
6. **Mock external dependencies** - Don't make real API calls, database connections to external systems
7. **Keep tests maintainable** - Clear test names, good assertions, minimal duplication

**Test Coverage Requirements:**
- **New models:** Test all constraints, relationships, validations
- **New API endpoints:** Test all methods, auth, validation, error cases
- **New business logic:** Test all code paths, edge cases
- **New UI components:** Test user interactions, state changes, validation
- **Bug fixes:** Add regression test that would have caught the bug

**When to ask for help:**
- If you cannot find existing test patterns in the codebase
- If the test framework is unclear or undocumented
- If tests require complex setup you're unsure about
- If tests are failing for environmental reasons

**DO NOT:**
- ❌ Skip tests because "there aren't any existing tests for this area"
- ❌ Skip tests because "it's a small change"
- ❌ Skip tests because "I manually tested it"
- ❌ Mark story complete with failing tests
- ❌ Create tests but don't run them

**The only valid reasons to skip tests:**
- Pure documentation changes (README, guides)
- Pure configuration changes (no code)
- Pure deletion of deprecated code
- Test framework doesn't exist (extremely rare - must be documented)

### When to Ask for Help

Ask the user for clarification if:
- Requirements are ambiguous
- Multiple valid approaches exist
- Referenced files don't exist or have changed
- Dependencies are unclear
- Acceptance criteria conflict
