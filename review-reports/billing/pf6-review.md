# Billing and organization plans: PatternFly 6 review

Review date: 2026-10-21. Baseline: `d66650950`. Reviewed feature diff: `0aa9746dc..d66650950` (102 files). This is an independent review of the submitted baseline, not a claim that the fixes below have already been made.

## Assessment

The production screens use PatternFly 6 components and utilities consistently. The installed `@patternfly/react-core` version is **6.4.1**; the repository guide's PatternFly 5 wording is stale and was not used as the review standard. No new imports from `@patternfly/react-core/deprecated`, old modal composition APIs, or `pf-v5-*` classes were found in the feature components. The organization creation flow correctly uses a full page and same-window checkout.

The remaining concerns are component semantics and state communication, rather than a wholesale PF6 migration. Resolve PF6-01 through PF6-05 before considering the feature ready. PF6-06 is a functional plugin integration issue discovered during the review and needs either support or an explicit product scope decision. PF6-07 is a bounded cleanup recommendation, not a requirement to redesign Stripe's externally hosted UI.

Severity: **high** = users cannot reliably understand or complete a feature path; **medium** = component contract or state presentation is incorrect for a supported state; **low** = consistency improvement without demonstrated functional failure.

## Findings and fixes

### PF6-01 — Organization plan choices lack the PF6 radio-group contract

**Severity: medium.** `web/src/routes/OrganizationsList/CreateOrganization.tsx:215` uses `FormGroup fieldId="organization-plan-selection"`, but that ID belongs to a `Table` at line 247. A table cannot be the target of a native form label. The required plan selection therefore lacks a programmatically associated group name even though each radio has an individual label.

**Fix:** Give the surrounding `FormGroup` `role="radiogroup"` (PF6 generates the group label association), or use a fieldset and legend. Keep the table's independent accessible name and responsive `Td dataLabel` properties. Give the table a separate ID if an ID is still needed. Mark the group required with supported ARIA semantics rather than assuming the visible required asterisk is sufficient.

**Acceptance:** The accessible radio group is named "Choose your organization's plan"; its required state is available; arrow keys select one plan; the table remains understandable at narrow widths. Add a Playwright assertion using the group role and keyboard selection.

**Reference:** [PF6 form documentation](https://www.patternfly.org/components/forms/form/) and the installed `FormGroup.js` support `role="group"`/`role="radiogroup"`, producing a named legend rather than a label targeting `fieldId`.

### PF6-02 — Input help and invoice validation do not use the complete helper pattern

**Severity: medium.** `CreateOrganization.tsx:167` and `:192` display helper messages without an `aria-describedby` relationship. `InvoiceSettingsModal.tsx:115` has the same omission. Additionally, `InvoiceSettingsModal.tsx:125` places a raw conditional string directly in `FormHelperText`, so the invalid message does not receive PF6 `HelperTextItem variant="error"` styling and semantics alongside the invalid input.

**Fix:** Add stable helper IDs and connect the inputs using `aria-describedby`. In invoice settings, render `HelperText` and `HelperTextItem` inside `FormHelperText`, setting the item variant from the same validation condition as `TextInput.validated`. Follow the existing organization name/email helper composition. Keep helper error messages text-based and preserve user-entered values on server failure.

**Acceptance:** Focusing an invalid input exposes the related error description; invalid receipt email receives PF6 error presentation; changing to a valid value clears the invalid state. Verify keyboard and API-error paths, not just CSS class presence.

**Reference:** [PF6 form accessibility](https://www.patternfly.org/components/forms/form/accessibility/) and [helper text](https://www.patternfly.org/components/helper-text/). Official PF6 form documentation explicitly associates help/error text with inputs using `aria-describedby`.

### PF6-03 — Subscription quantity labels target the NumberInput wrapper

**Severity: medium.** `web/src/components/modals/OrgSubscriptionModal.tsx:120` gives `FormGroup` the field ID `subscription-binding-quantity`. That ID is passed to `NumberInput` at line 122, but in installed PF6.4.1 this prop reaches the outer wrapper; the internal input receives properties from `inputProps`. Its default `inputAriaLabel` is "Input", which overrides any intended visible label even if the ID placement alone is fixed.

**Fix:** Pass the input ID through `inputProps={{id: 'subscription-binding-quantity'}}`; provide `inputAriaLabel="Quantity"` (matching the visible label), and meaningful increase/decrease button labels. Associate text describing the 1-to-available-quantity range. Leave mutation validation in place.

**Acceptance:** `getByRole('spinbutton', {name: 'Quantity'})` locates the actual input; clicking the visible label focuses it; minimum, maximum, invalid entry, and keyboard adjustments remain correct.

**Reference:** [PF6 number input](https://www.patternfly.org/components/number-input/) and installed `react-core/dist/esm/components/NumberInput/NumberInput.js`, which applies `inputProps` and `inputAriaLabel` to the inner `TextInput`.

### PF6-04 — Dynamic operation results use static Alerts

**Severity: high.** Examples include `CreateOrganization.tsx:137`, `ChangePlan.tsx:174` and `:269`, `BillingInformation.tsx:155`, and `FakeCheckout.tsx:91`. These alerts appear after asynchronous operations, and the subscription-return alert changes title during polling. PF6's `Alert` defaults to `isLiveRegion={false}`; visual presentation alone does not announce the result or move focus to it.

**Fix:** Use PF6 live-region behavior for newly appearing operation errors/results, with an announcement policy appropriate to the event. For changing subscription confirmation, mount an appropriate live-region container before its text changes or deliberately focus a stable result summary. Announce state transitions once; do not repeatedly announce every background refetch. Coordinate this fix with the accessibility review.

**Acceptance:** An organization creation or checkout error is announced without requiring the user to find it visually; the final polling result is announced; normal background polling does not flood announcements. Preserve retry buttons and recovery navigation.

**Reference:** [PF6 alert accessibility](https://www.patternfly.org/components/alert/accessibility/) and the PF6 async/dynamic live-region examples.

### PF6-05 — Over-quota usage passes an invalid value to Progress

**Severity: medium.** `web/src/routes/OrganizationsList/Organization/Tabs/Settings/UsageSection.tsx:31` calculates an uncapped ratio and passes it as `Progress.value` at line 40. For 11 repositories with an allowance of 10, it supplies 110. Installed PF6.4.1 clamps the visual bar to 100, but sets `aria-valuenow` from the original value with default `aria-valuemax=100`. This is reachable after a downgrade or whenever usage exceeds the allowance.

**Fix:** Clamp the numeric progress value to 0–100 while retaining the actual count and limit in visible text and `valueText`. Use a PF6 warning/danger variant or adjacent status text for over-limit usage if appropriate to the existing product behavior. Handle zero and unlimited allowances separately as today.

**Acceptance:** Under, equal, and over-limit states report a value within the configured range; over-limit users still learn their exact usage. Add a regression for 11/10 and preserve unlimited and zero-allowance behavior.

**Reference:** [PF6 progress](https://www.patternfly.org/components/progress/) and installed `Progress.js`, whose `progressBarAriaProps` use the raw value before the separate `scaledValue` clamp.

### PF6-06 — Plugin billing actions link to routes absent from the plugin router

**Severity: high functional integration issue; not a PF6 API violation.** `web/src/routes/PluginMain.tsx:46` adds organization creation, but not the new plans, invoices, and subscriptions pages registered in `StandaloneMain.tsx:179`. Shared billing UI links to these destinations in `BillingInformation.tsx:234` and `:277`, and `MarketplaceDetails.tsx:44`. A billing-enabled plugin therefore renders working-looking controls that reach its wildcard NotFound route. Paid organization creation can also return to a billing route whose navigation assumptions differ between shells.

**Fix:** Decide which of these billing paths the plugin supports. For supported paths, register the same functional routes and construct checkout/return links with the deployed router base. Otherwise gate or redirect the specific unsupported actions deliberately. Do not claim a plugin build verifies routing or authenticated runtime behavior.

**Acceptance:** From a billing-enabled plugin session, every visible action reaches its intended page; checkout returns to the correct shell/base path. If a path is intentionally unavailable, its UI communicates that policy instead of linking to a 404. Add route behavior coverage if a plugin test harness is available and record any environment gap.

### PF6-07 — Keep the mock Stripe imitation out of production feature scope

**Severity: medium cleanup recommendation, conditional on retaining the prototype.** `StripeCheckoutPreview.tsx:31` imports a stylesheet and seven branded image assets; its UI uses raw form controls and extensive literal colors in `StripeCheckoutPreview.css:1`. Its runtime entry is explicitly `MOCK_API`-gated in `StandaloneMain.tsx:277`, so these literals are not evidence that the real hosted Stripe page violates PF6. However, the component and stylesheet are imported unconditionally into the standalone module. `PaymentMethodDialog.tsx` is also prototype-specific and has no consumer found by the review.

**Fix:** Prefer removing the unused prototype dialog and excluding the visual Stripe imitation, its assets, and prototype-only dependencies from the upstream feature. If the visual mock remains an approved developer tool, isolate its entry/imports so production bundles do not retain its CSS/assets and document that it is intentionally outside the product PF6 surface. Keep the separate FakeStripe API simulation: its `FakeCheckout` page already uses PF6 components and does not collect payment details.

**Acceptance:** Production bundles expose the real checkout integration and supported PF6 simulation only; no imitation checkout entry or unneeded prototype assets remain accidentally shipped. Mock-specific tests must be updated to the final supported mock approach. No requirement is implied to restyle the third-party Stripe-hosted page with PatternFly.

**Reference:** [PF6 design tokens for development](https://www.patternfly.org/tokens/develop-with-tokens/), which recommends semantic tokens when customizing product surfaces. This recommendation is scoped to Quay-owned UI, not external Stripe branding.

## Lower-priority observations

- `CreateOrganization.tsx:292` and `FakeCheckout.tsx:99` separate action buttons with a literal space. PF6 `ActionGroup`/`ActionList` or `Flex` gives consistent spacing and narrow-screen behavior. This is a **low** consistency improvement, not a blocker by itself.
- Max-width values such as 480px for inputs, 600px for billing, and 720px for simulation are layout constraints, not automatically invalid PF6 tokens. Do not perform a token conversion solely because these are literals. The inherited 20px Settings padding predates this feature and is not a new deficiency to expand into a repository-wide restyle.
- Settings uses external active-tab content without PF6 `TabContent` association (`Settings.tsx:192` and `:217`). This structure predates the branch. The changed billing path depends on it, so the accessibility review should determine the smallest fix needed for a correctly associated named tab panel. Do not broaden this into unrelated settings redesign.
- New plan cards use a responsive Grid (12 columns default, 6 at md, 4 at xl). Tables provide `Td dataLabel` values for responsive stacking. These are appropriate PF6 patterns; no table-to-card rewrite is required.
- Modern modals consistently use `ModalHeader`, `ModalBody`, and `ModalFooter`, with title IDs linked through `aria-labelledby`. The invoice footer submit button correctly targets its form by ID. Dropdowns in `OrgSubscriptionModal` use `appendTo: 'inline'`, preserving the modal focus trap.
- Loading states use PF6 Skeletons within stable surrounding page content. No new page-level early-return loading spinner was found; a Suspense migration is not justified solely for this compliance pass.

## Prioritized implementation plan

1. **Fix shared semantic primitives:** radio-group labeling, number input label wiring, helper associations/error variant, and bounded Progress values (PF6-01/02/03/05). Add behavior tests at the existing organization, subscription, and billing test locations.
2. **Fix asynchronous feedback:** live announcements/focus for creation, checkout, retries, and final subscription confirmation (PF6-04). Coordinate with accessibility findings so the same alert is not announced twice.
3. **Resolve supported shell scope:** implement or gate plugin billing destinations and verify base-path return URLs (PF6-06). Avoid treating compile success as a runtime verification.
4. **Remove prototype-only residue:** review prototype dialog, imitation checkout, assets, mock scripts, and tests while preserving intentional FakeStripe coverage (PF6-07). Preserve the original branch for any mock design work excluded from the PR.
5. **Validate and re-review:** run relevant unit/API/Playwright suites; check keyboard operation, narrow viewport, zoom/reflow, light/dark states, and standalone/plugin builds. Record exact commands and distinguish passed, skipped, blocked, and not run. Re-review changed code against these acceptance criteria before opening the PR.

## Method, evidence, and limitations

- Read the root instructions supplied with the task and `web/AGENTS.md`; inspected the feature file list, relevant branch diffs, new production UI modules, and installed PF6.4.1 declarations/implementation.
- Consulted primary PatternFly v6 documentation through the PatternFly MCP search/documentation tools for modal, form, number input, and design tokens. Installed package behavior was preferred when hosted documentation could represent a newer v6 minor.
- Checked static imports and utility usage across the changed organization/billing components; reviewed standalone/plugin route registration and mock gating.
- This agent ran **no builds or browser/backend tests** to avoid concurrent writes to the shared application. Responsive behavior and theme compatibility are static assessments, not screenshot or contrast measurements. The coordinating agent's accessibility and validation reports provide runtime evidence separately.
- This is not a screen-reader certification or a comprehensive PF6 audit of unchanged Quay screens. Backend payment security, deployment configuration, real Stripe operation, and unrelated inherited CSS require their respective reviews/testing, not inference from PF6 component use.

## Re-review status

Independently rechecked the implementation in `/private/tmp/quay-billing-review`, rebased onto upstream `ada8067ee`, on 2026-10-21. The historical findings above refer to the original `d66650950` baseline; paths and line numbers below describe the reviewed PR working tree. This reviewer made no implementation edits and ran no runtime tests.

| Finding | Re-review disposition | Evidence |
| --- | --- | --- |
| PF6-01 | Fixed in code | `CreateOrganization.tsx:218` uses PF6 `FormGroup role="radiogroup"` with `aria-required="true"`. PF6 generates the group label association. The table keeps its independent accessible name and responsive cell labels. The new accessibility spec checks the group name, required state, and arrow-key selection. |
| PF6-02 | Fixed in code | `CreateOrganization.tsx:171`/`:197` associate stable helper IDs; `InvoiceSettingsModal.tsx:119` associates the input helper, and `:128` uses `HelperText`/`HelperTextItem` with the error variant. Accessibility assertions exercise invalid name/email descriptions and receipt-email validation. |
| PF6-03 | Fixed in code | `OrgSubscriptionModal.tsx:123` passes the ID through `inputProps`, uses `inputAriaLabel="Quantity"`, and names the increase/decrease buttons. The 1-to-available-quantity limits remain supplied through `min`/`max` and mutation validation. Additional visible range help would be optional refinement, not a remaining blocker. |
| PF6-04 | Fixed in code; speech verification remains manual | Relevant operation-error, checkout-return, and confirmation Alerts use `isLiveRegion`. Polling retains one result Alert and changes its text on state transitions rather than rendering one Alert per poll. Helpers also use the PF6 live-region option. DOM/live-region checks cannot certify what a particular screen-reader/browser combination speaks. |
| PF6-05 | Fixed in code | `UsageSection.tsx:42` uses `getPrivateRepositoryUsage`; the helper clamps finite quota percentages to 0–100. Progress supplies actual usage through `valueText` and applies warning status when over quota. Pure helper cases cover under-limit, over-limit, zero, and unlimited states. |
| PF6-06 | Fixed in route/code structure; authenticated plugin runtime unverified | `BillingRoutes.tsx:23` defines the plans, invoices, and subscriptions destinations once; both `PluginMain` and `StandaloneMain` include them. All three checkout callers pass `window.location.pathname` to the shared return-URL helpers. Unit cases exercise `/settings/quay` and `/beta/settings/quay` prefixes. A production plugin build or helper test does not establish authenticated console navigation and checkout behavior. |
| PF6-07 | Resolved through scope cleanup | `StripeCheckoutPreview`, its CSS and branded image directory, the unused `PaymentMethodDialog`, and `PrototypeBillingResource` are absent from the reviewed working tree. Native `FakeCheckout` remains a PF6 page without card collection. Legacy hosted-proxy tools were excluded as reported by the coordinator. |

The inherited Settings panel issue is also addressed: `Settings.tsx` supplies `tabContentId` on each tab and renders the active content through a named `TabContent`. The new accessibility spec checks the selected billing tab's `aria-controls` and the panel's accessible name.

**Re-review conclusion:** No remaining blocking PF6 implementation findings were identified in the reviewed changes. The low-priority action-button spacing observation remains optional. This is static approval of the scoped fixes, subject to the coordinating validation report: no claim is made here that Playwright, axe, production builds, real Stripe, authenticated plugin execution, dark-theme visual inspection, or assistive-technology speech tests have passed. The original branch is retained separately for excluded prototype/local work.

### Final validation evidence

The coordinator subsequently completed validation against the isolated PR dependencies, including **PatternFly 6.4.3**. The initial baseline inspected above used 6.4.1; the final tested dependency version is 6.4.3. See [the test report](test-report.md) for exact commands, outcomes, and scope limitations.

- Frontend unit suite: **1,525 tests passed across 189 files**.
- Backend: **8 new unit tests, 9 API security tests, 29 existing billing regressions, and 2 billing configuration tests passed** against the exact PR source.
- Playwright: **17 passed and 2 unavailable-checkout-profile cases skipped**, including 4 accessibility tests; the billing-disabled profile added **5 passed**, and broader organization/email/CRUD/creation coverage added **11 passed**.
- Standalone and plugin production builds passed, with 2 bundle-size warnings. The coordinator visually reviewed 8 fresh screenshots stored in the report's `screenshots` directory.
- Full TypeScript checking remains **failed due to the baseline**: 244 diagnostics versus 255 on upstream using the same dependencies; normalized comparison found **0 introduced and 11 resolved diagnostics**. This must not be reported as a passing full type check.

These results support the PF6 implementation re-review. Authenticated plugin runtime, VoiceOver speech, and authenticated real Stripe checkout remain unverified. The inherited header overflow at 320px is recorded as a separate-scope limitation; passing feature-content accessibility checks does not establish whole-application reflow compliance.
