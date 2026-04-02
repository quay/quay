---
allowed-tools: Bash(acli:*), Bash(curl:*), Bash(cat:*), Bash(which:*), Bash(brew:*), Bash(python3:*), Read, Write, Glob, Grep, AskUserQuestion
description: Create or edit JIRA tickets in PROJQUAY or QUAYIO projects
---

# JIRA Ticket Manager

Create or edit JIRA tickets with full field support including project, component, priority, labels, and more.

## Arguments

User input: `$ARGUMENTS`

---

## Phase 0: Prerequisites Check

### Step 1: Check acli Installation

```bash
which acli
```

**If acli is NOT installed:**

Display the following setup guide and stop:

```
acli (Atlassian CLI) is not installed. Follow these steps:

1. Install via Homebrew:
   brew tap atlassian/acli
   brew install acli

2. Create a JIRA API token:
   - Go to https://id.atlassian.com/manage-profile/security/api-tokens
   - Click "Create API token"
   - Give it a label (e.g., "acli")
   - Copy the token

3. Save the token to a file:
   echo "YOUR_TOKEN_HERE" > ~/.config/acli/token.txt
   chmod 600 ~/.config/acli/token.txt

4. Authenticate with acli:
   acli jira auth login --site "redhat.atlassian.net" --email "YOUR_EMAIL" --token < ~/.config/acli/token.txt

5. Verify authentication:
   acli jira auth status
```

Ask the user to complete the setup and try again.

### Step 2: Check Authentication

```bash
acli jira auth status
```

**If not authenticated:**

Look for a token file. Check these paths in order:
1. `~/.config/acli/token.txt`
2. `~/.acli-token`
3. Environment variable `$JIRA_API_TOKEN`

If a token file is found, read the user's email from the acli config:

```bash
cat ~/.config/acli/jira_config.yaml
```

Extract the `email` field from the config, then attempt to authenticate:

```bash
acli jira auth login --site "redhat.atlassian.net" --email "EMAIL_FROM_CONFIG" --token < TOKEN_FILE_PATH
```

If no token file or config is found, ask the user for their email, then display setup instructions.

### Step 3: Determine User Email for REST API

For REST API calls later, extract the user's email from acli config:

```bash
cat ~/.config/acli/jira_config.yaml
```

Store the `email` value for use in curl commands throughout this skill. Also determine the token file path (first match from the paths in Step 2).

---

## Phase 1: Determine Action

Parse `$ARGUMENTS` to determine the intended action:

**If $ARGUMENTS contains an existing issue key (e.g., QUAYIO-1234, PROJQUAY-5678):**
- Go to **Phase 3: Edit Ticket**

**If $ARGUMENTS contains a description or is empty:**
- Go to **Phase 2: Create Ticket**

**If unclear**, ask the user:
- "Would you like to **create** a new ticket or **edit** an existing one?"

---

## Phase 2: Create Ticket

### Step 1: Gather Required Information

Collect the following fields. If `$ARGUMENTS` contains a description, use it to pre-fill what you can. Ask the user for anything missing or ambiguous.

#### Project (Required)

Check memory for a default project. The available projects are:
- **QUAYIO** — quay.io SaaS-specific issues
- **PROJQUAY** — Project Quay open-source issues

If a default project is saved in memory, use it. Otherwise, ask:

> Which project should this ticket go into?
> 1. **QUAYIO** — quay.io SaaS
> 2. **PROJQUAY** — Project Quay open-source
>
> Would you like to set one as the default for future tickets?

If the user wants to set a default, save it to memory.

#### Summary / Title (Required)

Generate a concise, descriptive title from the user's description. Follow these conventions:
- Keep under 100 characters
- Be specific about the problem or feature
- Don't include the project key

Present the generated title and ask for confirmation or edits.

#### Issue Type (Required)

Determine from context or ask:
- **Bug** — Something is broken or not working as expected
- **Story** — New feature or user-facing capability
- **Task** — Technical work, maintenance, or operational task
- **Epic** — Large body of work spanning multiple stories (use `/create-epic-from-feature` instead for detailed epic creation)

#### Description (Required)

The description should be as detailed as possible. If the user provided a brief description in `$ARGUMENTS`, expand it by asking clarifying questions:

- What is the current behavior vs expected behavior? (for bugs)
- What is the user impact?
- Are there error messages, logs, or Sentry links?
- What are the acceptance criteria?
- Are there any relevant code paths or components?
- Steps to reproduce (for bugs)

Format the description in plain text with clear sections.

#### Component (Required)

Available components:
- **quay.io** — General quay.io issues (default)
- **registry-proxy** — Registry proxy related issues
- **documentation** — Documentation changes

Ask the user:

> Which component? (or type a new component name to create one)
> 1. quay.io (default)
> 2. registry-proxy
> 3. documentation
> 4. Other (specify)

If the user specifies a new component name, note it — it will be created via the REST API after ticket creation.

#### Priority (Optional)

- **Critical** — System down, data loss, security vulnerability
- **Major** — Significant impact, no workaround
- **Minor** — Low impact, workaround exists
- **Undefined** — Not yet triaged (default)

Default to **Undefined** unless the description clearly indicates severity. Ask if unclear.

#### Assignee (Optional)

Default to `@me` (current user). Ask if they want to assign to someone else.

#### Labels (Optional)

Suggest relevant labels based on the description content. Common labels include:
- `kinesis`, `logging`, `sentry`, `storage`, `auth`, `ui`, `api`, `database`, `performance`, `security`

Ask if the user wants to add, remove, or skip labels.

#### Epic Link (Optional)

Ask if this ticket should be linked to an existing epic:

> Should this ticket be linked to an existing epic? If so, provide the epic key (e.g., QUAYIO-100).

### Step 2: Review Before Creation

Display a summary of all fields for review:

```
╔══════════════════════════════════════════════════════════════╗
║                    NEW JIRA TICKET                           ║
╠══════════════════════════════════════════════════════════════╣
║  Project:     [QUAYIO / PROJQUAY]                            ║
║  Type:        [Bug / Story / Task]                           ║
║  Summary:     [Title]                                        ║
║  Component:   [component name]                               ║
║  Priority:    [priority]                                     ║
║  Assignee:    [assignee]                                     ║
║  Labels:      [label1, label2]                               ║
║  Epic:        [epic key or None]                             ║
╠══════════════════════════════════════════════════════════════╣
║  Description:                                                ║
║  [First 3-4 lines of description...]                         ║
║  ...                                                         ║
╚══════════════════════════════════════════════════════════════╝
```

Ask for confirmation:
> Does this look correct? (yes / edit / cancel)

### Step 3: Create the Ticket

Create the ticket using acli:

```bash
acli jira workitem create \
  --project "PROJECT_KEY" \
  --type "ISSUE_TYPE" \
  --summary "SUMMARY" \
  --description "DESCRIPTION" \
  --assignee "ASSIGNEE" \
  --label "LABELS" \
  --json
```

**IMPORTANT:** acli does not support components directly. After ticket creation, add the component via the REST API. Use the email extracted from acli config in Phase 0, Step 3:

```bash
TOKEN=$(cat TOKEN_FILE_PATH)
curl -s -X PUT "https://redhat.atlassian.net/rest/api/3/issue/ISSUE_KEY" \
  -H "Content-Type: application/json" \
  -u "EMAIL:$TOKEN" \
  -d '{"fields":{"components":[{"name":"COMPONENT_NAME"}]}}'
```

If the user specified a **new component**, create it first:

```bash
TOKEN=$(cat TOKEN_FILE_PATH)
PROJECT_ID=$(curl -s "https://redhat.atlassian.net/rest/api/3/project/PROJECT_KEY" \
  -u "EMAIL:$TOKEN" | python3 -c "import sys,json; print(json.load(sys.stdin)['id'])")

curl -s -X POST "https://redhat.atlassian.net/rest/api/3/component" \
  -H "Content-Type: application/json" \
  -u "EMAIL:$TOKEN" \
  -d '{"name":"COMPONENT_NAME","project":"PROJECT_KEY","projectId":PROJECT_ID}'
```

Then add it to the ticket as above.

If an **epic link** was specified:

```bash
TOKEN=$(cat TOKEN_FILE_PATH)
curl -s -X PUT "https://redhat.atlassian.net/rest/api/3/issue/ISSUE_KEY" \
  -H "Content-Type: application/json" \
  -u "EMAIL:$TOKEN" \
  -d '{"fields":{"parent":{"key":"EPIC_KEY"}}}'
```

If **priority** was specified (and not "Undefined"):

```bash
TOKEN=$(cat TOKEN_FILE_PATH)
curl -s -X PUT "https://redhat.atlassian.net/rest/api/3/issue/ISSUE_KEY" \
  -H "Content-Type: application/json" \
  -u "EMAIL:$TOKEN" \
  -d '{"fields":{"priority":{"name":"PRIORITY_NAME"}}}'
```

### Step 4: Confirm Creation

Display the result:

```
Ticket created: ISSUE_KEY
  URL: https://redhat.atlassian.net/browse/ISSUE_KEY
  Summary: [title]
  Component: [component]
  Priority: [priority]
  Assignee: [assignee]
```

---

## Phase 3: Edit Ticket

### Step 1: Fetch Current Ticket

```bash
acli jira workitem view ISSUE_KEY
```

Display the current ticket details to the user.

### Step 2: Determine Changes

If `$ARGUMENTS` contains edit instructions beyond the issue key, parse them.

Otherwise, ask what the user wants to change:
- Summary
- Description
- Type
- Priority
- Assignee
- Labels
- Component
- Status

### Step 3: Apply Changes

**For fields supported by acli** (summary, description, type, assignee, labels):

```bash
acli jira workitem edit --key "ISSUE_KEY" --FIELD "VALUE" --yes
```

**For fields requiring REST API** (component, priority, epic link):

Use the email extracted from acli config in Phase 0, Step 3:

```bash
TOKEN=$(cat TOKEN_FILE_PATH)
curl -s -X PUT "https://redhat.atlassian.net/rest/api/3/issue/ISSUE_KEY" \
  -H "Content-Type: application/json" \
  -u "EMAIL:$TOKEN" \
  -d '{"fields":{"FIELD_NAME": FIELD_VALUE}}'
```

### Step 4: Confirm Changes

Display updated ticket details to confirm changes were applied.

---

## Important Notes

### Atlassian Site

All API calls use `redhat.atlassian.net` as the site.

### Token File Locations

The skill checks for JIRA API tokens in this order:
1. `~/.config/acli/token.txt` (preferred)
2. `~/.acli-token`
3. `$JIRA_API_TOKEN` environment variable

### User Email

Never hardcode email addresses. Always read the email dynamically from `~/.config/acli/jira_config.yaml` at runtime.

### Customer Data

- **Never include customer names, company names, or identifying information** in ticket descriptions
- Generalize customer-specific details (e.g., "enterprise customer" instead of company name)
- Remove support case numbers or customer ticket references

### Component Handling

acli does not support the `components` field natively. Always use the JIRA REST API to set components after ticket creation or during edits.

### Default Project Memory

If the user sets a default project, save it to the Claude memory system so future invocations use it automatically.

---

## Example Usage

### Create a new ticket:
```
/jira-ticket Seeing LogSendException on Kinesis. Error: ProvisionedThroughputExceededException. Need to investigate shard provisioning.
```

### Edit an existing ticket:
```
/jira-ticket QUAYIO-1629 add label "urgent"
```

### Create with no arguments (interactive):
```
/jira-ticket
```
