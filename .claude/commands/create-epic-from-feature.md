---
allowed-tools: Bash(jira:*), Read, Glob, Grep, TodoWrite, Task, Write, AskUserQuestion
argument-hint: <feature-key>
description: Generate an epic structure from a JIRA feature and create it in JIRA
---

# Create Epic from Feature

Analyze a JIRA feature and generate a comprehensive epic title and description. This command analyzes the feature in the context of the Quay codebase, displays the generated epic for review, and creates it in JIRA.

## Feature Key

The JIRA feature to convert to an epic: `$ARGUMENTS`

---

## Phase 1: Fetch and Analyze Feature

### Step 1: Retrieve Feature Details

Fetch the complete feature information from JIRA:

```bash
jira issue view $ARGUMENTS
```

**Extract and analyze:**
- Feature summary and description
- Component (ui, api, data, buildman, storage, workers, etc.)
- Current status and priority
- Labels and tags
- Comments and discussion context
- Linked issues (dependencies, related work)
- Acceptance criteria
- Original requester and stakeholders
- Story points or estimates (if present)

**IMPORTANT - Customer Data Sanitization:**
- **Remove all customer-specific information** from the epic content
- Replace customer/company names with generic terms like "customer", "organization", "enterprise user"
- Redact specific deployment details, URLs, or infrastructure information
- Use generic use cases instead of customer-specific scenarios
- Remove any support case numbers or customer ticket references
- Focus on the technical problem and solution, not customer identifiers

### Step 2: Determine Feature Scope

Analyze whether this feature warrants epic-level promotion:

**Questions to consider:**
- Does this span multiple components or teams?
- Will this take multiple sprints to complete?
- Are there multiple distinct sub-features or stories needed?
- Does this represent a significant new capability or major refactor?
- Are there multiple stakeholders or cross-team dependencies?

**If the feature is too small for an epic:**
- Inform the user that this may not need epic-level tracking
- Explain why (e.g., "single component change", "1-2 sprint effort")
- Ask if they still want to proceed

### Step 3: Understand Codebase Context

Based on the component and feature description, identify relevant parts of the Quay codebase:

**For UI features:**
- Location: `web/src/`
- Related components in `web/src/components/`
- Routes in `web/src/routes/`
- API hooks in `web/src/hooks/`
- Tests in `web/cypress/e2e/`
- Consider PatternFly component usage patterns

**For API features:**
- Location: `endpoints/` (versioned APIs)
- Related models in `data/database.py` and `data/model/`
- Authentication in `auth/`
- Config validation in `config-tool/`

**For data/storage features:**
- Models: `data/database.py`
- Business logic: `data/model/`
- Storage backends: `storage/`
- Migrations: `data/migrations/versions/`
- Cache layer: `data/cache/`

**For worker/build features:**
- Workers: `workers/`
- Build system: `buildman/`
- Queue operations
- Configuration: `config.py`

Search the codebase to understand:
- Existing related functionality
- Architectural patterns to follow
- Similar completed work for reference
- Technical constraints and dependencies

---

## Phase 2: Identify Child Stories and Breakdown

### Step 1: Decompose the Feature

Break down the feature into logical child stories based on:

**Technical layers:**
- Database schema changes
- API endpoint changes
- Business logic changes
- UI component changes
- Background worker changes
- Configuration changes

**Functional areas:**
- Core functionality
- Testing (unit, integration, e2e)
- Documentation
- Migration/upgrade path
- Performance optimization
- Security considerations

**Phases of delivery:**
- MVP/Phase 1
- Additional features/Phase 2
- Polish and optimization/Phase 3

Create a structured list of child stories that will comprise the epic.

### Step 2: Identify Dependencies

Map out dependencies:

**Technical dependencies:**
- What existing systems does this rely on?
- What infrastructure is needed?
- Are there database migrations required?
- Does this need new libraries or services?

**Cross-team dependencies:**
- Does this need design input?
- Are there docs team requirements?
- Does this affect SRE/deployment?
- Are there security review needs?

**External dependencies:**
- Third-party services
- Upstream library updates
- Platform requirements

### Step 3: Define Success Criteria

Establish clear epic-level success criteria:

**Functional criteria:**
- What capabilities must be delivered?
- What user workflows should work?
- What integration points must function?

**Quality criteria:**
- Performance benchmarks (if applicable)
- Test coverage requirements
- Security compliance
- Accessibility requirements (for UI)

**Deployment criteria:**
- Migration safety
- Backward compatibility needs
- Feature flag requirements
- Rollback strategy

---

## Phase 3: Risk Assessment and Planning

### Step 1: Identify Risks and Complexity

**Technical risks:**
- Database migrations at scale
- Breaking API changes
- Performance degradation
- Security vulnerabilities
- Data integrity concerns
- Compatibility issues

**Organizational risks:**
- Cross-team coordination
- Timeline dependencies
- Resource constraints
- Scope creep potential

### Step 2: Estimate Effort

Based on the breakdown and codebase analysis:
- Number of components affected
- Complexity of each child story
- Testing requirements
- Documentation needs
- Migration complexity

**Provide context, not timelines:**
- "Affects 3 major subsystems (API, UI, workers)"
- "Requires database migration on large tables"
- "Needs coordination with 2 teams"

---

## Phase 4: Generate Epic Structure

### Step 1: Create Epic Title

Generate a clear, concise epic title that:
- Captures the high-level goal (not implementation details)
- Is user-focused when possible
- Differentiates from the feature name if needed
- Follows this pattern: `[Component] High-level capability or goal`

**Examples:**
- Feature: "Add OIDC support for auth"
  Epic: "[Auth] OpenID Connect Authentication Integration"

- Feature: "React port of repository settings"
  Epic: "[UI] Repository Management Interface Modernization"

- Feature: "Optimize GC worker performance"
  Epic: "[Workers] Garbage Collection System Improvements"

### Step 2: Write Epic Description

Structure the epic description using this template:

**CRITICAL: Ensure all customer-specific information is removed from the epic description below. Use generic terms and focus on technical requirements.**

```markdown
## Overview
[2-3 sentences describing the high-level goal and why this matters]
[Use generic terms - no customer names, company names, or identifying information]

## Context
[Brief background on the current state and why this change is needed]
[Reference the original feature: $ARGUMENTS]
[Do NOT include customer-specific use cases, deployment details, or support case references]

## Scope

### In Scope
- [Key capability 1]
- [Key capability 2]
- [Key capability 3]

### Out of Scope
- [Explicitly excluded items to prevent scope creep]
- [Future work or Phase 2 items]

## Child Stories
[List of planned child stories with brief descriptions]
1. [Story 1]: [Brief description]
2. [Story 2]: [Brief description]
3. [Story 3]: [Brief description]
...

## Dependencies
- **Technical**: [Required infrastructure, services, or prior work]
- **Cross-team**: [Other teams or stakeholders involved]
- **External**: [Third-party dependencies, if any]

## Success Criteria
- [ ] [Functional criteria 1]
- [ ] [Functional criteria 2]
- [ ] [Quality criteria - tests, performance, security]
- [ ] [Deployment criteria - migration, compatibility]

## Technical Approach
[High-level technical strategy - which components, patterns, migration approach]

### Components Affected
- [Component 1: Brief description of changes]
- [Component 2: Brief description of changes]

### Key Technical Decisions
- [Decision 1 and rationale]
- [Decision 2 and rationale]

## Risks and Mitigations
- **Risk**: [Risk description]
  **Mitigation**: [How to address it]
- **Risk**: [Risk description]
  **Mitigation**: [How to address it]

## Testing Strategy
- [Unit testing approach]
- [Integration testing approach]
- [E2E testing approach - Cypress/Playwright for UI]
- [Performance testing if needed]
- [Migration testing strategy]

## Rollout Strategy
- [Feature flag approach if applicable]
- [Migration steps]
- [Backward compatibility considerations]
- [Rollback plan]

## Documentation Needs
- [User-facing documentation]
- [Developer documentation]
- [API documentation if applicable]
- [Migration guides]

## Related Work
- Original Feature: $ARGUMENTS
- Related Issues: [List any related issues]
- Reference Implementation: [Link to similar work if applicable]
```

---

## Phase 5: Output, Review, and JIRA Creation

### Step 1: Save Epic to File

Save the generated epic to a markdown file for reference:

**File location:** `.claude/plans/$ARGUMENTS-epic.md`

Write the complete epic content to this file, including:
- Epic title at the top as H1
- Full epic description using the template above
- All sections (Overview, Context, Scope, Child Stories, etc.)

### Step 2: Validate Customer Data Sanitization

Before displaying, perform a final check to ensure NO customer-specific information is present:

**Check for:**
- Customer or company names (replace with "customer", "organization", "enterprise")
- Specific deployment URLs or hostnames
- Support case numbers or ticket IDs
- Customer-specific infrastructure details
- Personal names or email addresses (except Red Hat employees for context)
- Any identifying information that could expose customer identity

**If found:** Remove or generalize the information before proceeding.

### Step 3: Display Epic for Review

After saving and validating, display the full epic content to the user for review:

**Epic Title:**
```
[Generated title - verified no customer info]
```

**Epic Description:**
```
[Full epic description using the template above - verified no customer info]
```

**Summary of analysis:**
- Number of child stories identified
- Major components affected
- Key dependencies and risks
- Estimated complexity (number of teams, subsystems)

**Recommendations:**
- Should this be broken into multiple epics?
- Are there quick wins that should be separate stories?
- What should be prioritized first?
- What needs clarification before starting?

### Step 4: Confirm Before Creating JIRA

Ask the user for confirmation before creating the JIRA epic:

**Options:**
1. **Create Epic** - Proceed to create the epic in JIRA
2. **Edit First** - Allow user to request modifications before creating
3. **Skip JIRA Creation** - Save the file only, do not create in JIRA

Use the AskUserQuestion tool to get user confirmation.

### Step 5: Create Epic in JIRA

If the user confirms, create the epic in JIRA:

```bash
jira issue create \
  --type Epic \
  --summary "[Epic Title]" \
  --body "$(cat .claude/plans/$ARGUMENTS-epic.md)" \
  --custom epic-name="[Epic Name from title]" \
  --no-input
```

**Note:** The epic name should be derived from the epic title (use the title or a shortened version).

After creation:
1. Capture the new epic key from the output
2. Link the original feature to the new epic:
   ```bash
   jira issue link $ARGUMENTS [NEW_EPIC_KEY] "is Epic of"
   ```
3. Display the new epic URL to the user

### Step 6: Provide Next Steps

After epic creation (or if skipped), provide guidance:

**If epic was created:**
- "Epic created: [NEW_EPIC_KEY]"
- "Original feature $ARGUMENTS has been linked"
- "Next: Run `/create-stories-from-epic .claude/plans/$ARGUMENTS-epic.md` to generate child stories"

**If skipped:**
- "Epic saved to `.claude/plans/$ARGUMENTS-epic.md`"
- "To create manually, copy the content to JIRA"
- "Don't forget to set the Epic Name field when creating manually"

---

## Important Considerations

### Customer Data Protection (CRITICAL)

**All epic content must be sanitized of customer-specific information.**

Epics are often visible to a wider audience than the original feature. Always:

- **Remove customer/company names** - Use "customer", "organization", "enterprise user"
- **Generalize use cases** - "Large enterprise with 1000+ repos" instead of "[Company X] with their Docker registry"
- **Redact infrastructure details** - "Customer's private cloud environment" instead of specific URLs/IPs
- **Remove support references** - No support case numbers or customer ticket IDs
- **Focus on the problem, not the customer** - "Users need bulk operations for repository management" not "[Customer] requested bulk operations"

**Examples of sanitization:**

❌ BAD: "[Acme Corp] needs OIDC integration with their Azure AD for 5000 users at acme.internal.com"

✅ GOOD: "Enterprise customers need OIDC integration with Azure AD for large-scale deployments"

❌ BAD: "Support case #12345 - [BigCompany] experiencing timeout with 10000 repos"

✅ GOOD: "Organizations with 10000+ repositories experience timeout issues"

### Preserve Original Context
- Maintain links to the original feature
- Keep all comments and discussion
- Preserve acceptance criteria
- Note the requester and stakeholders
- **But sanitize any customer-specific information from these sources**

### Quay-Specific Patterns
- **UI**: PatternFly components, React with TypeScript, TanStack Router
- **API**: Versioned endpoints, Flask blueprints, authentication decorators
- **Data**: SQLAlchemy models, Alembic migrations, caching patterns
- **Workers**: Background job processors, queue management
- **Config**: Config-tool schema validation
- **Testing**: Pytest for backend, Cypress for frontend e2e

### Red Flags
- **Too small**: Feature can be completed in 1 sprint with minimal changes
- **Too vague**: Requirements aren't clear enough to break down
- **Wrong level**: Should be a project or program, not an epic

---

## Example Usage

```
/create-epic-from-feature PROJQUAY-1234
```

This will:
1. Fetch the feature from JIRA
2. Analyze it in the context of the Quay codebase
3. Determine if epic-level is appropriate
4. Break down into child stories
5. Identify dependencies and risks
6. Generate comprehensive epic title and description
7. **Sanitize all customer-specific information**
8. Save the epic to `.claude/plans/PROJQUAY-1234-epic.md`
9. Validate no customer data is present
10. Display the epic content for review
11. Ask for confirmation before creating in JIRA
12. Create the epic in JIRA (if confirmed)
13. Link the original feature to the new epic
14. Provide next steps for creating child stories

**Important Notes:**
- All customer-specific information will be automatically removed or generalized
- You can manually set the security level on the created epic in JIRA if needed
- The generated epic focuses on technical requirements, not customer identifiers
