---
allowed-tools: Bash(jira:*), Read, Glob, Grep
argument-hint: <issue-key>
description: Estimate complexity and effort for a JIRA issue
---

# Estimate Issue Complexity

Analyze a JIRA issue and provide a comprehensive complexity estimate with size, effort, and risk metrics for a senior developer with Claude assistance.

## Issue Key

The JIRA issue to estimate: `$ARGUMENTS`

---

## Phase 1: Gather Issue Information

### Step 1: Fetch Issue Details

Retrieve the full issue information from JIRA:

```bash
jira issue view $ARGUMENTS
```

**Extract and note:**
- Issue type (Bug, Story, Task, Epic, etc.)
- Summary and full description
- Component(s) affected
- Priority
- Labels
- Acceptance criteria (if present)
- Comments with additional context
- Linked issues (blockers, dependencies)

---

## Phase 2: Codebase Impact Analysis

### Step 2: Identify Affected Areas

Based on the issue description, search the codebase to understand scope:

**For UI issues:**
- Search `web/src/` for related components
- Check routing in `web/src/routes/`
- Look for existing tests in `web/cypress/e2e/`

**For Backend issues:**
- Search `endpoints/` for related API routes
- Check `data/model/` for affected business logic
- Look at `data/database.py` for schema impacts
- Check `workers/` if background jobs are involved

**For both:**
- Count files likely to be modified
- Identify test files that need updates
- Check for migration requirements

### Step 3: Analyze Dependencies

- Are there linked/blocking issues?
- Does this require coordination with other teams?
- Are there external API or service dependencies?
- Does this require database migrations?
- Does this require configuration changes?

---

## Phase 3: Complexity Assessment

### Complexity Dimensions

Evaluate each dimension on a scale of 1-5:

| Dimension | 1 (Low) | 3 (Medium) | 5 (High) |
|-----------|---------|------------|----------|
| **Code Scope** | 1-2 files | 3-5 files | 6+ files |
| **Logic Complexity** | Simple CRUD | Business rules | Algorithmic/Distributed |
| **Testing Effort** | Update existing | New unit tests | New e2e + integration |
| **Risk Level** | Isolated change | Touches shared code | Core system change |
| **Uncertainty** | Clear requirements | Some ambiguity | Needs spike/research |
| **Dependencies** | None | Internal deps | External/blocking |

### T-Shirt Sizing Criteria

Based on complexity dimensions, assign a size:

| Size | Total Score | Typical Characteristics |
|------|-------------|------------------------|
| **XS** | 6-10 | Typo fix, config change, simple bug fix |
| **S** | 11-15 | Single component change, clear scope |
| **M** | 16-20 | Multiple files, moderate testing, some complexity |
| **L** | 21-25 | Cross-cutting changes, significant testing, some risk |
| **XL** | 26-30 | Major feature, architectural changes, high risk |

---

## Phase 4: Time Estimation

### Effort Calculation

For a **senior developer with Claude assistance**, estimate based on size:

| Size | Estimated Effort | Includes |
|------|------------------|----------|
| **XS** | 1-2 hours | Implementation + basic testing |
| **S** | 2-4 hours | Implementation + unit tests + review |
| **M** | 4-8 hours (0.5-1 day) | Implementation + comprehensive tests + review |
| **L** | 1-2 days | Planning + implementation + testing + review |
| **XL** | 3-5 days | Research + planning + implementation + testing + review |

**Adjustment factors to consider:**
- Add 20% if unfamiliar with the subsystem
- Add 30% if requires database migration
- Add 25% if requires coordination with other teams
- Subtract 20% if similar work was done recently

---

## Phase 5: Generate Report

### Output Format

Present the final estimate in this format:

```
╔══════════════════════════════════════════════════════════════════╗
║                    ISSUE COMPLEXITY ESTIMATE                     ║
╠══════════════════════════════════════════════════════════════════╣
║  Issue:        $ARGUMENTS                                        ║
║  Title:        [Issue Title]                                     ║
║  Type:         [Bug/Story/Task]                                  ║
║  Component:    [Component]                                       ║
╠══════════════════════════════════════════════════════════════════╣
║                      COMPLEXITY SCORES                           ║
╠══════════════════════════════════════════════════════════════════╣
║  Code Scope:        [1-5] ████░░░░░░                             ║
║  Logic Complexity:  [1-5] ██████░░░░                             ║
║  Testing Effort:    [1-5] ████████░░                             ║
║  Risk Level:        [1-5] ██░░░░░░░░                             ║
║  Uncertainty:       [1-5] ████░░░░░░                             ║
║  Dependencies:      [1-5] ██░░░░░░░░                             ║
║  ─────────────────────────────────────────────────────────────   ║
║  TOTAL SCORE:       [X/30]                                       ║
╠══════════════════════════════════════════════════════════════════╣
║                         ESTIMATE                                 ║
╠══════════════════════════════════════════════════════════════════╣
║  T-Shirt Size:      [XS/S/M/L/XL]                                ║
║  Effort:            [X-Y hours/days]                             ║
║  Confidence:        [High/Medium/Low]                            ║
╠══════════════════════════════════════════════════════════════════╣
║                      IMPACT ANALYSIS                             ║
╠══════════════════════════════════════════════════════════════════╣
║  Files to Modify:   ~[N] files                                   ║
║  Tests Required:    [Unit/Integration/E2E]                       ║
║  Migration Needed:  [Yes/No]                                     ║
║  Config Changes:    [Yes/No]                                     ║
╠══════════════════════════════════════════════════════════════════╣
║                         RISKS                                    ║
╠══════════════════════════════════════════════════════════════════╣
║  • [Risk 1]                                                      ║
║  • [Risk 2]                                                      ║
╠══════════════════════════════════════════════════════════════════╣
║                     RECOMMENDATIONS                              ║
╠══════════════════════════════════════════════════════════════════╣
║  • [Recommendation 1]                                            ║
║  • [Recommendation 2]                                            ║
╚══════════════════════════════════════════════════════════════════╝
```

---

## Additional Metrics to Include

### Confidence Level Criteria

- **High**: Clear requirements, familiar codebase area, similar past work
- **Medium**: Some ambiguity, moderate familiarity, standard patterns
- **Low**: Unclear requirements, unfamiliar area, novel solution needed

### Risk Categories

Identify and list specific risks:
- **Technical**: Complex algorithms, performance concerns, security implications
- **Integration**: API changes, database migrations, service dependencies
- **Scope**: Unclear requirements, potential scope creep
- **Testing**: Hard to test scenarios, flaky test potential

### Recommendations

Provide actionable suggestions:
- Should this be broken into smaller issues?
- Is a spike/research task needed first?
- Are there blocking dependencies to resolve?
- Should certain aspects be deferred?
- Are there quick wins vs. complex parts?

---

## Example Usage

```
/estimate-issue PROJQUAY-1234
```

This will:
1. Fetch PROJQUAY-1234 from JIRA
2. Analyze the codebase for impact
3. Score complexity dimensions
4. Calculate effort estimate
5. Generate a formatted report with risks and recommendations
