# AI-Powered Repository Description Generator

## Current Progress (Updated: 2024-12-16)

### Backend Implementation: ✅ COMPLETE

| Phase | Component | Status | Tests |
|-------|-----------|--------|-------|
| 1.1 | Database Model Tests | ✅ Complete | 23 passing |
| 1.2 | Database Model (`OrganizationAISettings`) | ✅ Complete | - |
| 2.1 | LLM Provider Tests | ✅ Complete | 26 passing |
| 2.2 | LLM Provider Implementation | ✅ Complete | - |
| 2.3 | Prompt Template Tests | ✅ Complete | 23 passing |
| 3.1 | History Extractor Tests | ✅ Complete | 35 passing |
| 3.2 | History Extractor Implementation | ✅ Complete | - |
| 4.1 | Cache Tests | ✅ Complete | 24 passing |
| 4.2 | Cache Implementation | ✅ Complete | - |
| 5.1 | API Endpoint Tests | ✅ Complete | 25 passing |
| 5.3 | API Endpoint Implementation | ✅ Complete | - |
| - | Flask App Registration | ✅ Complete | - |
| - | Config Schema (`FEATURE_AI`) | ✅ Complete | - |
| - | Database Migration | ✅ Complete | - |

**Total Backend Tests: 156 passing**

### Files Created/Modified

```
data/
├── database.py                    # Added OrganizationAISettings model (line 2225)
├── model/
│   ├── organization_ai.py         # NEW: AI settings CRUD operations
│   └── test/
│       └── test_organization_ai_settings.py  # NEW: 23 tests
├── migrations/versions/
│   └── d068cc908da9_add_organization_ai_settings.py  # NEW: Migration

util/
├── ai/
│   ├── __init__.py                # NEW
│   ├── providers.py               # NEW: LLM provider implementations
│   ├── prompt.py                  # NEW: Prompt templates
│   ├── history_extractor.py       # NEW: Image analysis
│   ├── cache.py                   # NEW: Data model caching
│   └── test/
│       ├── __init__.py            # NEW
│       ├── test_providers.py      # NEW: 26 tests
│       ├── test_prompt.py         # NEW: 23 tests
│       ├── test_history_extractor.py  # NEW: 35 tests
│       └── test_cache.py          # NEW: 24 tests
├── config/
│   └── schema.py                  # Modified: Added FEATURE_AI

endpoints/api/
├── __init__.py                    # Modified: Added import endpoints.api.ai
├── ai.py                          # NEW: AI description API endpoints
└── test/
    └── test_ai_description.py     # NEW: 25 tests
```

### Phase 2 (Security & Audit): ✅ COMPLETE

| Phase | Component | Status | Tests |
|-------|-----------|--------|-------|
| 7.1 | Security Tests | ✅ Complete | 55 passing |
| 7.2 | Security Implementation | ✅ Complete | - |
| 8.1 | Audit Logging Tests | ✅ Complete | 13 passing |
| 8.2 | Audit Logging (integrated) | ✅ Complete | - |
| - | Security Integration in API | ✅ Complete | - |

**Total Tests (Phase 1 + Phase 2): 224 passing**

### Additional Files Created (Phase 2)

```
util/ai/
├── security.py                    # NEW: Response sanitization, env var filtering
└── test/
    ├── test_security.py           # NEW: 55 tests
    └── test_audit.py              # NEW: 13 tests
```

### Remaining Work

| Phase | Component | Status |
|-------|-----------|--------|
| 6 | Frontend Implementation | 🔲 Not Started |
| 9 | Stripe Integration (quay.io only) | 🔲 Not Started |

---

## Overview

Add a "Generate Description" button to the Repository Information page (New UI only) that analyzes container image layer history and uses an LLM to auto-generate meaningful Markdown descriptions.

## Operational Modes

The feature operates in two modes depending on deployment:

| Aspect | quay.io (Managed) | Self-hosted (BYOK) |
|--------|-------------------|---------------------|
| LLM Backend | Quay.io provides & pays | User's own API keys |
| Model Selection | Quay.io controlled (including local models) | User chooses any model |
| Credential Setup | None - just enable feature | Org admin configures via settings |
| Rate Limiting | By org, paid subscription tier | Unlimited |
| Access Control | Org admin + paid org | Org admin only |
| Feature Availability | Subscription-gated | Always available |

---

## Feature Flag Architecture

### Hierarchical Feature Control

```yaml
# config.yaml (Admin-controlled)

# Master kill switch - disables ALL AI features when false
# When true or not set, individual AI features can be enabled
FEATURE_AI: true

# Operational mode
AI_PROVIDER_MODE: "managed"  # "managed" (quay.io) or "byok" (self-hosted)

# For managed mode only - internal Quay.io configuration
AI_MANAGED_PROVIDER:
  PROVIDER: "google"
  API_KEY: "${QUAY_INTERNAL_AI_KEY}"
  MODEL: "gemini-2.0-flash-lite"
  FALLBACK_ENDPOINT: "http://internal-ollama:11434/v1"  # Local fallback
```

### Per-Organization Settings (Database)

```python
# Stored in database, managed via Org Settings UI
class OrganizationAISettings:
    # Feature toggles (user-controlled)
    ai_description_generator_enabled: bool = False
    # Future features...
    # ai_vulnerability_summary_enabled: bool = False

    # BYOK mode only - org credentials
    ai_provider: str  # "anthropic", "openai", "google", "deepseek", "custom"
    ai_api_key_encrypted: str  # Encrypted storage
    ai_model: str
    ai_endpoint: str  # For custom providers
    ai_credentials_verified: bool = False
```

### Feature Flag Logic

```python
def is_ai_description_available(org):
    # Master kill switch
    if not app.config.get("FEATURE_AI", True):
        return False

    # Check org-level toggle
    org_settings = get_org_ai_settings(org)
    if not org_settings.ai_description_generator_enabled:
        return False

    # Mode-specific checks
    if is_managed_mode():
        return org_has_paid_subscription(org)
    else:  # BYOK
        return org_settings.ai_credentials_verified
```

---

## Data Flow

### Managed Mode (quay.io)

```
User clicks "Generate Description"
    → Check: org has paid subscription
    → Check: user is org admin
    → Fetch manifest for selected tag (default: latest)
    → Extract layer history from image config
    → Send to Quay.io's internal LLM backend
    → Cache response
    → Return description for preview
    → User accepts/edits, saves
    → Audit log entry created
```

### BYOK Mode (Self-hosted)

```
User clicks "Generate Description"
    → Check: user is org admin
    → Check: org has verified AI credentials
        → If not: Show setup modal/drawer
        → Guide through credential configuration
        → Verify connectivity with test prompt
        → Save encrypted credentials
    → Fetch manifest for selected tag
    → Extract layer history
    → Send to org's configured LLM provider
    → Cache response
    → Return description for preview
    → User accepts/edits, saves
    → Audit log entry created
```

---

## Phase 1: Database Models & Core Infrastructure

### 1.1 Database Model Tests (Write First)

**File**: `data/model/test/test_organization_ai_settings.py`

```python
# Credential storage tests
def test_create_org_ai_settings():
def test_update_org_ai_settings():
def test_get_org_ai_settings_returns_none_for_unconfigured():
def test_api_key_stored_encrypted():
def test_api_key_decryption():
def test_delete_org_ai_settings():

# Feature toggle tests
def test_enable_ai_description_generator():
def test_disable_ai_description_generator():
def test_settings_isolated_per_org():

# Verification status tests
def test_mark_credentials_verified():
def test_mark_credentials_unverified_on_key_change():
```

### 1.2 Database Model Implementation

**File**: `data/database.py` (add to existing)

```python
class OrganizationAISettings(BaseModel):
    organization = ForeignKeyField(User, unique=True)  # User with organization=True

    # Feature toggles
    description_generator_enabled = BooleanField(default=False)

    # Provider configuration (BYOK mode)
    provider = CharField(null=True)  # anthropic, openai, google, deepseek, custom
    api_key_encrypted = TextField(null=True)
    model = CharField(null=True)
    endpoint = CharField(null=True)  # For custom providers
    credentials_verified = BooleanField(default=False)
    credentials_verified_at = DateTimeField(null=True)

    # Metadata
    created_at = DateTimeField(default=datetime.utcnow)
    updated_at = DateTimeField(default=datetime.utcnow)
```

**File**: `data/model/organization_ai.py`

```python
def get_org_ai_settings(org_name: str) -> Optional[OrganizationAISettings]:
def create_or_update_org_ai_settings(org_name: str, **kwargs) -> OrganizationAISettings:
def set_org_ai_credentials(org_name: str, provider: str, api_key: str, model: str, endpoint: str = None):
def mark_credentials_verified(org_name: str, verified: bool):
def is_description_generator_enabled(org_name: str) -> bool:
def toggle_description_generator(org_name: str, enabled: bool):
```

### 1.3 Encryption Utility Tests

**File**: `util/security/test/test_encryption.py`

```python
def test_encrypt_api_key():
def test_decrypt_api_key():
def test_encryption_uses_unique_salt():
def test_encrypted_key_not_plaintext():
def test_decrypt_with_wrong_key_fails():
```

### 1.4 Encryption Implementation

**File**: `util/security/encryption.py`

```python
def encrypt_sensitive_value(value: str) -> str:
    """Encrypt using Fernet with app secret key."""

def decrypt_sensitive_value(encrypted: str) -> str:
    """Decrypt using Fernet with app secret key."""
```

---

## Phase 2: LLM Provider Infrastructure

### 2.1 Provider Interface Tests (Write First)

**File**: `util/ai/test/test_providers.py`

```python
# Factory tests
def test_create_anthropic_provider():
def test_create_openai_provider():
def test_create_google_provider():
def test_create_deepseek_provider():
def test_create_custom_provider():
def test_invalid_provider_raises_exception():
def test_missing_api_key_raises_exception():
def test_custom_provider_requires_endpoint():

# Provider behavior tests (mocked HTTP)
def test_anthropic_generate_description_success():
def test_anthropic_handles_rate_limit_error():
def test_anthropic_handles_auth_error():
def test_anthropic_handles_timeout():
def test_openai_generate_description_success():
def test_google_generate_description_success():
def test_custom_provider_uses_openai_compatible_api():

# Configuration tests
def test_provider_respects_max_tokens():
def test_provider_respects_temperature():
def test_provider_uses_configured_model():

# Connectivity verification tests
def test_verify_connectivity_success():
def test_verify_connectivity_invalid_key():
def test_verify_connectivity_unreachable_endpoint():
def test_verify_connectivity_timeout():
```

### 2.2 Provider Implementation

**File**: `util/ai/__init__.py`
**File**: `util/ai/providers.py`

```python
class LLMProviderInterface(ABC):
    @abstractmethod
    def generate_description(self, image_analysis: ImageAnalysis) -> str:
        pass

    @abstractmethod
    def verify_connectivity(self) -> Tuple[bool, Optional[str]]:
        """Returns (success, error_message)."""
        pass

class AnthropicProvider(LLMProviderInterface): ...
class OpenAIProvider(LLMProviderInterface): ...
class GoogleProvider(LLMProviderInterface): ...
class DeepSeekProvider(LLMProviderInterface): ...
class CustomProvider(LLMProviderInterface): ...  # OpenAI-compatible

class ProviderFactory:
    @staticmethod
    def create(provider: str, api_key: str, model: str, endpoint: str = None) -> LLMProviderInterface:
        pass

    @staticmethod
    def create_from_org_settings(org_settings: OrganizationAISettings) -> LLMProviderInterface:
        pass

    @staticmethod
    def create_managed() -> LLMProviderInterface:
        """Create provider from Quay.io's internal config."""
        pass
```

### 2.3 Prompt Template Tests

**File**: `util/ai/test/test_prompt.py`

```python
def test_prompt_includes_layer_commands():
def test_prompt_includes_exposed_ports():
def test_prompt_includes_environment_variables():
def test_prompt_includes_labels():
def test_prompt_handles_empty_history():
def test_prompt_truncates_long_history():
def test_prompt_excludes_sensitive_env_vars():  # PASSWORD, SECRET, KEY, TOKEN
def test_prompt_max_length_respected():
```

### 2.4 Prompt Implementation

**File**: `util/ai/prompt.py`

```python
DESCRIPTION_PROMPT_TEMPLATE = """
Analyze this container image build history and generate a concise Markdown description.

## Layer History (Dockerfile commands):
{layer_commands}

## Image Configuration:
- Exposed Ports: {ports}
- Environment Variables: {env_vars}
- Entrypoint: {entrypoint}
- CMD: {cmd}
- Labels: {labels}

Write a 1-2 paragraph summary describing:
1. What this image does / its purpose
2. Key software and versions it contains
3. How to use it (ports, environment variables)

Keep the response under 500 words. Use Markdown formatting.
"""

def build_prompt(image_analysis: ImageAnalysis) -> str:
    pass

def sanitize_env_vars(env_vars: Dict[str, str]) -> Dict[str, str]:
    """Remove sensitive environment variables."""
    pass
```

---

## Phase 3: Image History Extraction

### 3.1 History Extractor Tests (Write First)

**File**: `util/ai/test/test_history_extractor.py`

```python
# Basic extraction tests
def test_extract_history_from_schema2_manifest():
def test_extract_history_from_oci_manifest():
def test_extract_created_by_commands():
def test_filter_empty_layers():
def test_extract_exposed_ports():
def test_extract_environment_variables():
def test_extract_labels():
def test_extract_entrypoint():
def test_extract_cmd():

# Repository-level tests
def test_extract_from_latest_tag():
def test_extract_from_specific_tag():
def test_handle_no_tags():
def test_handle_manifest_list():

# Edge cases
def test_handle_missing_config():
def test_handle_empty_history():
def test_handle_malformed_manifest():

# Tag selection tests
def test_list_available_tags_for_selection():
def test_tag_list_limited_for_performance():
def test_tag_list_sorted_by_last_modified():
```

### 3.2 History Extractor Implementation

**File**: `util/ai/history_extractor.py`

```python
@dataclass
class ImageAnalysis:
    layer_commands: List[str]
    exposed_ports: List[str]
    environment_vars: Dict[str, str]
    labels: Dict[str, str]
    entrypoint: Optional[List[str]]
    cmd: Optional[List[str]]
    base_image: Optional[str]
    manifest_digest: str
    tag: str

class ImageHistoryExtractor:
    def __init__(self, storage):
        self.storage = storage

    def extract_from_repository(
        self,
        repo_ref,
        tag: str = None,  # None = latest
    ) -> ImageAnalysis:
        pass

    def extract_from_manifest(self, manifest) -> ImageAnalysis:
        pass

    def list_available_tags(
        self,
        repo_ref,
        limit: int = 50,
        sort_by: str = "last_modified"
    ) -> List[TagInfo]:
        """Return tags suitable for UI selection dropdown."""
        pass
```

---

## Phase 4: Caching Layer

### 4.1 Cache Tests (Write First)

**File**: `util/ai/test/test_cache.py`

```python
def test_cache_generated_description():
def test_retrieve_cached_description():
def test_cache_key_includes_manifest_digest():
def test_cache_key_includes_model():
def test_cache_invalidated_on_new_tag():
def test_cache_expiry():
def test_cache_miss_returns_none():
def test_bypass_cache_flag():
```

### 4.2 Cache Implementation

**File**: `util/ai/cache.py`

```python
class DescriptionCache:
    def __init__(self, redis_client):
        self.redis = redis_client
        self.ttl = 86400 * 7  # 7 days

    def get(self, org: str, repo: str, manifest_digest: str, model: str) -> Optional[str]:
        pass

    def set(self, org: str, repo: str, manifest_digest: str, model: str, description: str):
        pass

    def invalidate(self, org: str, repo: str):
        pass

    def _cache_key(self, org: str, repo: str, manifest_digest: str, model: str) -> str:
        return f"ai_desc:{org}/{repo}:{manifest_digest}:{model}"
```

---

## Phase 5: API Endpoints

### 5.1 Generate Description Endpoint Tests (Write First)

**File**: `endpoints/api/test/test_ai_description.py`

```python
# Permission tests
def test_generate_requires_org_admin():
def test_generate_denied_for_non_admin():
def test_generate_denied_for_read_only_user():

# Feature flag tests
def test_returns_404_when_feature_ai_disabled():
def test_returns_404_when_org_feature_disabled():
def test_available_when_feature_enabled():

# Managed mode tests (quay.io)
def test_managed_mode_requires_paid_subscription():
def test_managed_mode_no_credentials_needed():
def test_managed_mode_uses_internal_provider():

# BYOK mode tests
def test_byok_mode_requires_verified_credentials():
def test_byok_mode_returns_setup_required_without_credentials():
def test_byok_mode_uses_org_credentials():

# Functional tests
def test_generate_description_success():
def test_generate_returns_markdown():
def test_generate_with_specific_tag():
def test_generate_uses_cache_when_available():
def test_generate_bypasses_cache_when_requested():
def test_generate_for_repo_without_tags():

# Error handling
def test_handles_llm_timeout():
def test_handles_llm_error():
def test_handles_invalid_manifest():

# Audit logging
def test_generation_creates_audit_log():

# Tag listing
def test_list_tags_for_selection():
def test_list_tags_respects_limit():
```

### 5.2 Credential Management Endpoint Tests

**File**: `endpoints/api/test/test_ai_settings.py`

```python
# Permission tests
def test_get_settings_requires_org_admin():
def test_update_settings_requires_org_admin():
def test_settings_not_visible_to_non_admin():

# CRUD tests
def test_get_ai_settings():
def test_get_settings_hides_api_key():
def test_update_ai_credentials():
def test_update_preserves_existing_on_partial_update():
def test_delete_ai_credentials():

# Verification tests
def test_verify_credentials_success():
def test_verify_credentials_invalid_key():
def test_verify_credentials_unreachable():
def test_verification_status_persisted():

# Toggle tests
def test_enable_description_generator():
def test_disable_description_generator():
def test_toggle_requires_verified_credentials_in_byok():

# Feature flag tests
def test_settings_hidden_when_feature_ai_disabled():
```

### 5.3 API Implementation

**File**: `endpoints/api/ai_description.py`

```python
@resource("/v1/repository/<apirepopath:repository>/generate-description")
@show_if(features.AI)
class GenerateRepositoryDescription(RepositoryParamResource):

    @require_repo_admin(allow_for_superuser=True)
    @nickname("generateRepoDescription")
    @parse_args()
    @query_param("tag", "Tag to analyze (default: latest)", type=str, default=None)
    @query_param("bypass_cache", "Skip cache lookup", type=truthy_bool, default=False)
    def post(self, namespace_name, repo_name, parsed_args):
        """Generate AI-powered description from image layer history."""
        pass


@resource("/v1/repository/<apirepopath:repository>/tags-for-description")
@show_if(features.AI)
class TagsForDescription(RepositoryParamResource):

    @require_repo_admin(allow_for_superuser=True)
    @nickname("listTagsForDescription")
    @parse_args()
    @query_param("limit", "Max tags to return", type=int, default=50)
    def get(self, namespace_name, repo_name, parsed_args):
        """List tags available for description generation."""
        pass
```

**File**: `endpoints/api/ai_settings.py`

```python
@resource("/v1/organization/<orgname>/ai-settings")
@show_if(features.AI)
class OrganizationAISettings(ApiResource):

    schemas = {
        "UpdateAISettings": {
            "type": "object",
            "properties": {
                "description_generator_enabled": {"type": "boolean"},
                "provider": {"type": "string", "enum": ["anthropic", "openai", "google", "deepseek", "custom"]},
                "api_key": {"type": "string"},
                "model": {"type": "string"},
                "endpoint": {"type": "string", "format": "uri"},
            }
        }
    }

    @require_org_admin
    @nickname("getOrgAISettings")
    def get(self, orgname):
        """Get organization AI settings (API key masked)."""
        pass

    @require_org_admin
    @nickname("updateOrgAISettings")
    @validate_json_request("UpdateAISettings")
    def put(self, orgname):
        """Update organization AI settings."""
        pass

    @require_org_admin
    @nickname("deleteOrgAISettings")
    def delete(self, orgname):
        """Delete organization AI credentials."""
        pass


@resource("/v1/organization/<orgname>/ai-settings/verify")
@show_if(features.AI)
class VerifyAICredentials(ApiResource):

    @require_org_admin
    @nickname("verifyOrgAICredentials")
    def post(self, orgname):
        """Verify AI credentials by sending a test prompt."""
        pass
```

---

## Phase 6: Frontend Implementation

### 6.1 Frontend Tests

**File**: `web/src/routes/RepositoryDetails/Information/GenerateDescription.test.tsx`

```typescript
// Visibility tests
test('generate button visible when feature enabled and user is admin')
test('generate button hidden when feature disabled')
test('generate button disabled for non-admins with tooltip')
test('generate button disabled for unpaid org on quay.io with tooltip')

// Setup flow tests (BYOK mode)
test('shows setup modal when credentials not configured')
test('setup modal validates required fields')
test('setup modal tests connectivity before saving')
test('setup modal shows error on connectivity failure')
test('setup modal closes and enables button on success')

// Generation flow tests
test('shows loading state during generation')
test('shows tag selector dropdown')
test('tag selector defaults to latest')
test('shows preview modal with generated description')
test('preview allows editing before save')
test('save button updates repository description')
test('cancel discards generated description')

// Error handling tests
test('shows error alert on generation failure')
test('shows retry button on failure')

// Cache tests
test('shows cached indicator when using cached result')
test('regenerate button bypasses cache')
```

**File**: `web/src/routes/OrganizationsList/Organization/Tabs/Settings/AISettings.test.tsx`

```typescript
// Visibility tests
test('AI settings tab visible when feature enabled')
test('AI settings tab hidden when feature disabled')
test('settings form visible only to org admins')

// Configuration tests
test('shows provider dropdown')
test('shows model field')
test('shows endpoint field for custom provider')
test('hides endpoint field for hosted providers')
test('shows masked API key for existing config')

// Verification tests
test('verify button tests credentials')
test('shows success indicator on verification')
test('shows error message on verification failure')

// Toggle tests
test('can enable description generator')
test('cannot enable without verified credentials in BYOK mode')
```

### 6.2 Frontend Implementation

**Files**:

```
web/src/
├── routes/
│   ├── RepositoryDetails/
│   │   └── Information/
│   │       ├── GenerateDescriptionButton.tsx
│   │       ├── GenerateDescriptionModal.tsx
│   │       ├── TagSelectorDropdown.tsx
│   │       ├── CredentialSetupDrawer.tsx
│   │       └── GenerateDescription.test.tsx
│   └── OrganizationsList/
│       └── Organization/
│           └── Tabs/
│               └── Settings/
│                   ├── AISettings.tsx
│                   └── AISettings.test.tsx
├── hooks/
│   ├── UseAISettings.ts
│   ├── UseGenerateDescription.ts
│   └── UseVerifyAICredentials.ts
└── resources/
    └── AIResource.ts
```

**Component**: `GenerateDescriptionButton.tsx`

```typescript
interface GenerateDescriptionButtonProps {
  org: string;
  repo: string;
  onDescriptionGenerated: (description: string) => void;
  canAdmin: boolean;
}

// Button states:
// 1. Enabled - user is admin, credentials configured (or managed mode)
// 2. Disabled + tooltip "Only organization administrators can use this feature"
// 3. Disabled + tooltip "Upgrade to paid plan to use AI features" (quay.io)
// 4. Enabled but opens setup drawer (BYOK, no credentials)
```

**Component**: `CredentialSetupDrawer.tsx`

```typescript
// Inline drawer/modal for BYOK credential setup:
// 1. Provider selection dropdown
// 2. API Key input (password field)
// 3. Model selection (text input or dropdown based on provider)
// 4. Endpoint input (only for "custom" provider)
// 5. "Verify & Save" button
// 6. Success/error feedback
// 7. Close and proceed to generation
```

---

## Phase 7: Response Sanitization & Security

### 7.1 Security Tests

**File**: `util/ai/test/test_security.py`

```python
# Response sanitization
def test_strip_script_tags():
def test_strip_onclick_handlers():
def test_strip_javascript_urls():
def test_preserve_valid_markdown():
def test_preserve_code_blocks():
def test_limit_response_length():

# Prompt injection mitigation
def test_layer_history_escaped():
def test_env_vars_escaped():

# Credential security
def test_api_key_never_logged():
def test_api_key_masked_in_api_response():
def test_api_key_encrypted_at_rest():

# Sensitive data filtering
def test_password_env_vars_filtered():
def test_secret_env_vars_filtered():
def test_token_env_vars_filtered():
def test_key_env_vars_filtered():
```

### 7.2 Security Implementation

**File**: `util/ai/security.py`

```python
def sanitize_llm_response(response: str) -> str:
    """Remove potentially dangerous content from LLM response."""
    pass

def filter_sensitive_env_vars(env_vars: Dict[str, str]) -> Dict[str, str]:
    """Remove environment variables that may contain secrets."""
    SENSITIVE_PATTERNS = ['PASSWORD', 'SECRET', 'TOKEN', 'KEY', 'API_KEY', 'CREDENTIAL']
    pass

def escape_for_prompt(text: str) -> str:
    """Escape text to prevent prompt injection."""
    pass
```

---

## Phase 8: Audit Logging

### 8.1 Audit Log Tests

**File**: `util/ai/test/test_audit.py`

```python
def test_log_description_generated():
def test_log_includes_org_and_repo():
def test_log_includes_user():
def test_log_includes_tag_analyzed():
def test_log_includes_cache_hit_status():
def test_log_credentials_configured():
def test_log_credentials_deleted():
def test_log_feature_toggled():
```

### 8.2 Audit Implementation

Uses existing `log_action()` pattern:

```python
# In generate-description endpoint
log_action(
    "generate_ai_description",
    namespace,
    {
        "repo": repository,
        "tag": tag_used,
        "manifest_digest": manifest_digest,
        "cache_hit": was_cached,
        "model": model_used,  # Don't log provider details
    },
    repo_name=repository,
)

# In settings endpoint
log_action(
    "configure_ai_settings",
    org_name,
    {
        "provider": provider,
        "description_generator_enabled": enabled,
    },
)
```

---

## Phase 9: Stripe Integration (Secondary Enhancement)

### 9.1 Billing Integration Tests

**File**: `util/ai/test/test_billing.py`

```python
def test_ai_feature_requires_paid_plan():
def test_free_plan_cannot_enable_ai():
def test_paid_plan_can_enable_ai():
def test_rate_limit_by_org_tier():
def test_downgrade_disables_ai_feature():
```

### 9.2 Billing Integration

**File**: `util/ai/billing.py`

```python
def org_has_ai_access(org_name: str) -> bool:
    """Check if org's subscription includes AI features."""
    # Integrate with existing Stripe billing
    pass

def get_org_rate_limit(org_name: str) -> int:
    """Get rate limit based on subscription tier."""
    pass
```

---

## File Structure Summary

```
data/
├── database.py                    # Add OrganizationAISettings model
├── model/
│   ├── organization_ai.py         # AI settings CRUD operations
│   └── test/
│       └── test_organization_ai_settings.py

util/
├── ai/
│   ├── __init__.py
│   ├── providers.py               # LLM provider implementations
│   ├── prompt.py                  # Prompt templates
│   ├── history_extractor.py       # Image analysis
│   ├── cache.py                   # Redis caching
│   ├── security.py                # Response sanitization
│   ├── billing.py                 # Stripe integration (Phase 9)
│   └── test/
│       ├── test_providers.py
│       ├── test_prompt.py
│       ├── test_history_extractor.py
│       ├── test_cache.py
│       ├── test_security.py
│       ├── test_audit.py
│       └── test_billing.py
├── security/
│   ├── encryption.py              # API key encryption
│   └── test/
│       └── test_encryption.py

endpoints/api/
├── ai_description.py              # Generate description endpoint
├── ai_settings.py                 # Org AI settings endpoint
└── test/
    ├── test_ai_description.py
    └── test_ai_settings.py

web/src/
├── routes/
│   ├── RepositoryDetails/
│   │   └── Information/
│   │       ├── GenerateDescriptionButton.tsx
│   │       ├── GenerateDescriptionModal.tsx
│   │       ├── TagSelectorDropdown.tsx
│   │       ├── CredentialSetupDrawer.tsx
│   │       └── GenerateDescription.test.tsx
│   └── OrganizationsList/
│       └── Organization/
│           └── Tabs/
│               └── Settings/
│                   ├── AISettings.tsx
│                   └── AISettings.test.tsx
├── hooks/
│   ├── UseAISettings.ts
│   ├── UseGenerateDescription.ts
│   └── UseVerifyAICredentials.ts
└── resources/
    └── AIResource.ts
```

---

## Implementation Order

### Phase 1-2: Foundation
1. Write database model tests
2. Implement `OrganizationAISettings` model
3. Write encryption tests
4. Implement encryption utilities
5. Write provider tests
6. Implement LLM providers

### Phase 3-4: Core Logic
1. Write history extractor tests
2. Implement history extractor
3. Write cache tests
4. Implement caching layer
5. Write prompt tests
6. Implement prompt builder

### Phase 5: API Layer
1. Write API endpoint tests
2. Implement generate-description endpoint
3. Implement AI settings endpoints
4. Write security tests
5. Implement response sanitization

### Phase 6: Frontend
1. Write frontend tests
2. Implement settings UI
3. Implement generate button
4. Implement setup drawer
5. Implement preview modal

### Phase 7-8: Polish
1. Implement audit logging
2. Security hardening
3. Documentation

### Phase 9: Billing (Secondary)
1. Stripe integration tests
2. Billing integration
3. Rate limiting by tier

---

## Configuration Reference

### Self-hosted (BYOK Mode)

```yaml
# config.yaml
FEATURE_AI: true
AI_PROVIDER_MODE: byok
```

### quay.io (Managed Mode)

```yaml
# config.yaml
FEATURE_AI: true
AI_PROVIDER_MODE: managed

AI_MANAGED_PROVIDER:
  PROVIDER: google
  API_KEY: ${QUAY_GOOGLE_AI_KEY}
  MODEL: gemini-2.0-flash-lite
  MAX_TOKENS: 500
  TEMPERATURE: 0.7

# Optional: Local fallback for cost control
AI_MANAGED_FALLBACK:
  PROVIDER: custom
  ENDPOINT: http://internal-ollama:11434/v1
  MODEL: llama3
```

---

## Test Execution

```bash
# Run all AI-related tests
TEST=true PYTHONPATH="." pytest util/ai/test/ endpoints/api/test/test_ai_*.py data/model/test/test_organization_ai_settings.py -v

# Run specific test file
TEST=true PYTHONPATH="." pytest util/ai/test/test_providers.py -v

# Run frontend tests
cd web && npm test -- --testPathPattern="AISettings|GenerateDescription"
```
