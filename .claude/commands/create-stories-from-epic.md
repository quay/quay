---
allowed-tools: Bash(jira:*), Read, Glob, Grep, TodoWrite, Task, Write, AskUserQuestion
argument-hint: <epic-key>
description: Generate child stories from a JIRA epic, review them, and create in JIRA with approval
---

# Create Child Stories from Epic

Fetch the epic from JIRA: $ARGUMENTS

## Your Task

Analyze the epic and generate a set of child stories that together fulfill all requirements defined in the epic. Each story must be independently implementable by Claude.

## Process

### Step 1: Fetch Epic from JIRA

Retrieve the complete epic information from JIRA:

```bash
jira issue view $ARGUMENTS
```

**Extract from JIRA output:**
- **Epic Title** - The summary field (displayed at top of output)
- **Epic Description** - The description section (under "Description" heading)
- **Epic Name** - The epic name field (customfield_12311141)
- **Component** - Component tags if present
- **Labels** - Any labels applied
- **Linked Issues** - Child stories already created, if any
- **Comments** - Additional context from comments

**Parse the description:**
The epic description should be in markdown format and may contain:
- Overview/Context section
- Scope (in-scope and out-of-scope)
- Technical Approach
- Success Criteria
- Dependencies
- Testing Strategy
- etc.

**Save epic content:**
Create `.claude/plans/$ARGUMENTS-epic.md` with:
- Epic title as H1
- Full epic description from JIRA
- Link to JIRA issue: `https://issues.redhat.com/browse/$ARGUMENTS`

This file serves as the source for story generation.

### Step 2: Analyze the Epic

From the fetched epic content, identify:
- All functional requirements
- All technical requirements
- Dependencies between components
- Success criteria
- Architectural decisions
- Scope (in-scope and out-of-scope items)

### Step 3: Decompose into Stories

Break down the epic into logical, independently deliverable units of work:
- Each story should represent a cohesive piece of functionality
- Order stories to respect dependencies (foundational work first)
- Aim for stories that can be completed in a focused coding session
- Consider technical layers (data model, API, worker, UI)
- Consider phases (MVP, enhancements, testing, documentation)

### Step 4: Generate Stories

For each story, create a comprehensive description with all required sections:

### Story Title
A clear, concise title following the pattern: `[Component] Action Description`

Examples:
- `[Data Model] Add OrgMirrorConfig database table and migrations`
- `[API] Create organization mirror CRUD endpoints`
- `[Worker] Implement repository discovery job`

### Story Description

Each story description MUST include these sections:

#### Summary
2-3 sentences explaining what this story delivers and why it matters.

#### Acceptance Criteria
Specific, testable criteria that define "done". Use checkbox format:
- [ ] Criterion 1
- [ ] Criterion 2

#### Technical Requirements
Detailed implementation guidance including:
- Files to create or modify (with paths)
- Functions/classes to implement
- Database changes if applicable
- API endpoints if applicable
- Configuration changes if applicable

#### Implementation Notes
Specific guidance for Claude to implement this story:
- Existing patterns to follow (reference specific files)
- Code conventions to maintain
- Error handling requirements
- Edge cases to consider

#### Dependencies
- Stories that must be completed before this one
- External dependencies (libraries, services)

#### Testing Requirements
- Unit tests needed
- Integration tests needed
- Test file locations

#### Definition of Done
- [ ] Code implemented and follows project conventions
- [ ] All acceptance criteria met
- [ ] Tests written and passing
- [ ] No regressions in existing functionality

## Output Format

Create individual markdown files for each story in a dedicated directory for this epic.

### Step 5: Create Story Directory and Save Stories

Create a directory for the epic's stories:

```bash
mkdir -p .claude/plans/stories/$ARGUMENTS
```

Write all generated stories to individual markdown files in this directory.

### Directory Structure
```
.claude/plans/stories/$ARGUMENTS/
├── 00-epic-overview.md          # Epic summary and dependency graph
├── 01-[component]-[short-name].md
├── 02-[component]-[short-name].md
├── 03-[component]-[short-name].md
└── ...
```

**File path pattern:** `.claude/plans/stories/$ARGUMENTS/[NN]-[component]-[short-name].md`

### File Naming Convention
- Use zero-padded numbers for ordering: `01-`, `02-`, etc.
- Include component in lowercase: `data-model`, `api`, `worker`, `ui`, `testing`, etc.
- Use kebab-case for the short name
- Examples:
  - `01-data-model-org-mirror-schema.md`
  - `02-data-model-lazy-creation-logic.md`
  - `03-worker-discovery-sync.md`
  - `04-api-org-mirror-endpoints.md`
  - `11-ui-configuration-panel.md`

### Epic Overview File (`00-epic-overview.md`)

**Location:** `.claude/plans/stories/$ARGUMENTS/00-epic-overview.md`

This file contains:
1. **Epic Summary** - Brief overview from JIRA epic ($ARGUMENTS)
   - Include epic key and title
   - Link to JIRA: `https://issues.redhat.com/browse/$ARGUMENTS`
2. **Key Architectural Decisions** - Important design choices from epic
3. **Story Dependency Graph** - Visual or textual representation of story order
4. **Story Index** - List of all stories with file names and titles
5. **Codebase Reference** - Key existing files and patterns table

### Individual Story Files
Each story file contains the complete story with all sections:
- Story title as H1 heading
- All sections (Summary, Acceptance Criteria, Technical Requirements, etc.)
- Self-contained - can be read and implemented independently

---

## Review and JIRA Creation Process

After generating all stories, proceed with review and JIRA creation:

### Step 6: Display Story Summary

Show the user a summary of all generated stories:

```
Stories Generated for Epic $ARGUMENTS:

00. Epic Overview
01. [Data Model] Story Title
02. [API] Story Title
03. [Worker] Story Title
...

Total: [N] stories
Location: .claude/plans/stories/$ARGUMENTS/
```

### Step 7: Review and Create Stories in JIRA

For each story (starting with 01, not the epic overview):

**7.1. Display Story Content**

Show the complete story content to the user:

```markdown
## Story [N]: [Story Title]

**File:** .claude/plans/stories/$ARGUMENTS/[NN]-[component]-[short-name].md

**Summary:**
[Story summary text]

**Acceptance Criteria:**
[List criteria]

**Technical Requirements:**
[Key requirements]

**Dependencies:**
[Dependencies listed]

[Continue with other sections...]
```

**7.2. Ask for Approval**

Use the AskUserQuestion tool to ask the user what to do with this story:

**Options:**
1. **Create Story in JIRA** - Create this story as a child of epic $ARGUMENTS
2. **Skip This Story** - Don't create in JIRA, move to next story
3. **Edit First** - User wants to modify the story before creating
4. **Stop Creation** - Don't create any more stories, finish here

**7.3. Create Story in JIRA (if approved)**

If user selects "Create Story in JIRA", create the story:

```bash
jira issue create \
  --type Story \
  --summary "[Story Title from file]" \
  --body "$(cat .claude/plans/stories/$ARGUMENTS/[NN]-[component]-[short-name].md)" \
  --parent $ARGUMENTS \
  --no-input
```

**Important:**
- Use `--parent $ARGUMENTS` to link the story to the parent epic
- Capture the created story key from the output
- Display the created story URL to the user

**7.4. Record Created Story**

Keep track of created stories and display progress:
```
✓ Created: PROJQUAY-10030 - Story 01
✓ Created: PROJQUAY-10031 - Story 02
○ Skipped: Story 03
...
Progress: [2/14 created, 1/14 skipped]
```

**7.5. Repeat for Next Story**

Continue with the next story (7.1 → 7.2 → 7.3 → 7.4) until:
- All stories have been reviewed
- User selects "Stop Creation"
- An error occurs

### Step 8: Provide Final Summary

After completing the review process, provide a comprehensive summary:

**Stories Created:**
```
✓ PROJQUAY-10030 - [Data Model] Story Title
✓ PROJQUAY-10031 - [API] Story Title
○ Story 03 - Skipped by user
✓ PROJQUAY-10032 - [Worker] Story Title
...

Created: [N] stories
Skipped: [M] stories
Total: [N+M] stories
```

**Links:**
- Epic: https://issues.redhat.com/browse/$ARGUMENTS
- Story files: .claude/plans/stories/$ARGUMENTS/

**Next Actions:**
1. Review created stories in JIRA
2. Begin implementation with the first created story
3. For skipped stories, create manually if needed later

---

## Story Quality Checklist

Before finalizing each story, verify:
- [ ] Story is independently implementable (no partial features)
- [ ] All file paths are specific and accurate for this codebase
- [ ] References to existing code patterns include actual file paths
- [ ] Acceptance criteria are testable, not vague
- [ ] Technical requirements are detailed enough for implementation
- [ ] Story scope is appropriate (not too large, not too small)
- [ ] Dependencies are explicitly listed

## Guidelines

- **Be Specific**: Reference actual files, functions, and patterns from the codebase
- **Be Complete**: Include all information needed to implement without additional context
- **Be Actionable**: Write requirements that can be directly translated to code
- **Be Testable**: Every requirement should have a clear way to verify completion
- **Respect Existing Patterns**: Research how similar features are implemented in the codebase
- **Consider Edge Cases**: Include error handling and boundary conditions

## Important Notes

### Working with JIRA Epics

- **Fetch first, analyze second**: Always fetch the epic from JIRA before generating stories
- **Save for reference**: Save the epic description to `.claude/plans/$ARGUMENTS-epic.md`
- **Use epic key for directory**: Create stories in `.claude/plans/stories/$ARGUMENTS/`
- **Check for existing stories**: If the epic already has child stories in JIRA, review them to avoid duplication

### Story Generation Guidelines

- Do NOT create stories for documentation unless explicitly required by the epic
- Do NOT create stories for "nice to have" features not in the epic scope
- DO explore the codebase to understand existing patterns before writing stories
- DO include specific file paths and code references from this codebase
- DO ensure stories can be implemented in dependency order
- DO create the directory structure if it doesn't exist
- DO write each story to its own file for easier tracking and implementation

### Interactive Review Process

- **All stories are saved first**: Stories are written to files before any JIRA creation
- **Review one at a time**: Each story is displayed and approved individually
- **Four options per story**:
  1. **Create Story in JIRA** - Proceed with creation and link to epic
  2. **Skip This Story** - Don't create in JIRA, continue to next story
  3. **Edit First** - User wants to modify the file before creating
  4. **Stop Creation** - Finish the process, don't review remaining stories

### Handling "Edit First" Option

If user selects "Edit First":
1. Tell the user the file location: `.claude/plans/stories/$ARGUMENTS/[NN]-[component]-[short-name].md`
2. Wait for the user to edit the file manually
3. After user confirms edits are complete, re-read the file
4. Display the updated content for approval
5. Ask again: Create, Skip, or Stop

### Using `--parent` Flag

The `--parent $ARGUMENTS` flag in `jira issue create`:
- Automatically links the created story to the parent epic
- Sets the Epic Link field (customfield_12311140)
- Story appears under the epic in JIRA boards and backlogs
- No need for separate `jira issue link` command

### Epic Description Format

The epic description from JIRA should contain:
- Overview and context
- Scope (in-scope and out-of-scope)
- Technical approach
- Success criteria
- Dependencies
- Any architectural decisions

If the epic description is incomplete, note this in the epic overview file and work with available information.

---

## Example Usage

```bash
/create-stories-from-epic PROJQUAY-1266
```

This will:
1. Fetch epic PROJQUAY-1266 from JIRA
2. Save epic description to `.claude/plans/PROJQUAY-1266-epic.md`
3. Analyze the epic requirements
4. Create directory `.claude/plans/stories/PROJQUAY-1266/`
5. Generate story files:
   - `00-epic-overview.md`
   - `01-data-model-schema.md`
   - `02-api-endpoints.md`
   - etc.
6. Display summary of generated stories
7. **For each story:**
   - Display the story content for review
   - Ask for approval: Create, Skip, Edit, or Stop
   - If approved, create the story in JIRA
   - Link the story to the parent epic
   - Show creation progress
8. Provide final summary with all created story links

**Interactive Review Example:**

```
Story 1: [Data Model] Organization Mirror Configuration Schema

Summary: Create database tables and Peewee models for storing org-level mirror configurations...

[Full story content displayed]

What would you like to do with this story?
1. Create Story in JIRA
2. Skip This Story
3. Edit First
4. Stop Creation

> User selects: Create Story in JIRA

✓ Created: PROJQUAY-10030 - [Data Model] Organization Mirror Configuration Schema
  https://issues.redhat.com/browse/PROJQUAY-10030

Progress: [1/14 created]

[Continues to next story...]
```

**Benefits of Interactive Review:**
- Review each story before committing to JIRA
- Skip stories that need refinement
- Stop at any point if you need to make changes
- All stories are saved locally first for reference
- Only approved stories are created in JIRA

---

## Completion Summary

After completing the review and creation process, Step 8 provides a comprehensive summary.

**Summary Format:**

**Stories Generated:**
- Total files: [N] markdown files
- Location: `.claude/plans/stories/$ARGUMENTS/`
- Epic reference: `.claude/plans/$ARGUMENTS-epic.md`

**JIRA Creation Results:**
- ✓ Created in JIRA: [N] stories
- ○ Skipped: [M] stories
- ⊗ Stopped at: Story [X] (if user stopped early)

**Created Stories:**
- PROJQUAY-10030 - [Data Model] Story Title
- PROJQUAY-10031 - [API] Story Title
- [etc.]

**Skipped Stories:**
- Story 03 - [Worker] Story Title (user can create manually later)
- [etc.]

**Next Actions:**
1. Review created stories in JIRA at https://issues.redhat.com/browse/$ARGUMENTS
2. For any skipped stories, review the files and create manually if needed
3. Begin implementation with the first created story

---

## Troubleshooting

**Issue: Epic not found in JIRA**
- Verify the epic key is correct
- Check you have access to view the epic
- Ensure you're logged into JIRA CLI (`jira init` if needed)

**Issue: Epic description is empty or minimal**
- Note this in the `00-epic-overview.md` file
- Work with available information (title, comments, linked issues)
- Generate stories based on epic title and technical analysis
- Recommend updating the epic description in JIRA

**Issue: Epic has existing child stories**
- Review existing child stories to avoid duplication
- Note in `00-epic-overview.md` which stories already exist
- Only generate stories for uncovered scope
- Or regenerate all stories with updated scope

**Issue: Unable to create directory**
- Check write permissions in `.claude/plans/`
- Create parent directories manually if needed:
  ```bash
  mkdir -p .claude/plans/stories
  ```

**Issue: JIRA story creation fails**
- Verify you have permission to create issues in the project
- Check that the parent epic ($ARGUMENTS) exists and you have access
- Ensure you're logged into JIRA CLI
- Verify the `--parent` flag is supported in your jira CLI version
- If `--parent` fails, create story without it and link manually:
  ```bash
  jira issue link [STORY_KEY] $ARGUMENTS "is child of"
  ```

**Issue: Story description too long for JIRA**
- JIRA may have field length limits
- If creation fails, try truncating the story description
- Keep essential sections (Summary, Acceptance Criteria, Technical Requirements)
- Reference the full file in the story: "Full details: .claude/plans/stories/$ARGUMENTS/[file]"

**Issue: User wants to edit multiple stories before creating any**
- Select "Stop Creation" when first prompted
- Edit all story files manually
- Run the command again with a modified epic (or create a new workflow)
- Alternatively: Create stories in JIRA after all manual edits are complete

**Issue: Want to create all stories without reviewing each one**
- This workflow is designed for review-then-create
- If you want bulk creation, you can:
  1. Skip the interactive review by selecting "Create" for all
  2. Use a script to bulk-create from the generated files
  3. Request a different command for bulk creation
