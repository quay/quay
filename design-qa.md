# Stripe checkout prototype design QA

final result: passed

## Comparison target

- Source visual truth: `/Users/pshivpuj/Desktop/Screenshot 2026-10-12 at 5.19.21 PM.png`.
- Source pixels: 3022 x 1722; normalized as a 2x capture to 1511 x 861 CSS pixels. Converted the supplied image's ICC profile to sRGB before sampling colors and extracting supplied brand assets.
- Normalized reference: `/private/tmp/stripe-checkout-reference.png`.
- Subscription implementation: `/private/tmp/quay-stripe-subscription-desktop.png`, 1511 x 861 pixels at a 1511 x 861 CSS viewport, deviceScaleFactor 1.
- Payment-method implementation: `/private/tmp/quay-stripe-checkout-desktop.png`, same viewport and density.
- Mobile implementation: `/private/tmp/quay-stripe-checkout-mobile.png`, 390 x 1212 full-page capture at a 390 x 844 CSS viewport, deviceScaleFactor 1.
- State: empty card fields, US country, Link checkbox selected, phone visible, Card selected; subscription comparison uses Developer at $15/month.
- Full-view comparison: `/private/tmp/quay-stripe-comparison-final.png` (reference left, implementation right).
- Focused form comparison: `/private/tmp/quay-stripe-form-comparison-final.png` (reference left, implementation right). A focused comparison was necessary to inspect input grouping, field spacing, icons, and label typography.

## Findings

No actionable P0/P1/P2 differences remain in the checkout.

- Fonts and typography: system sans-serif, 16px section headings, 36px price, and 13-14px field text preserve the reference hierarchy and wrapping. Minor platform-native control glyph differences remain P3.
- Spacing and layout rhythm: desktop halves, 380px payment column, 80px central inset, merchant/price summary alignment, wallet row, grouped card inputs, country/ZIP grouping, and section gaps match the supplied composition. Mobile stacks the summary and form without horizontal overflow.
- Colors and tokens: white canvas, muted gray labels, subtle field borders/shadows, black Apple Pay button, and sampled sRGB Link green (#00d66f) follow the reference.
- Image quality: merchant, Apple Pay, Link, Google Pay, card brands, security-code icon, and country flag use tightly cropped, supplied 2x raster assets. No invented logo drawings or placeholder brand graphics are used.
- Copy and content: Developer's name and $15 price match the comparison target. Email uses the existing sample account. The payment update variant says Update payment method and shows the current plan. These are intentional product-context substitutions. Save/Subscribe actions and the sample-flow footer reflect the prototype's purpose.

## Comparison history

1. Previous implementation: a generic PatternFly modal omitted the reference's full-page composition and merchant/plan summary (P1). Replaced it with a standalone checkout view and made Change payment method open it directly.
2. First same-viewport comparison: `/private/tmp/quay-stripe-comparison-1.png` and `/private/tmp/quay-stripe-form-comparison-1.png` exposed phone-flag/text overlap and shortened field spacing (P2). Corrected input selector specificity and label gaps; post-fix evidence is the focused final comparison.
3. Mobile capture exposed a grid minimum-width overflow (P2). Changed tracks to minmax(0, 1fr), added a real viewport-width assertion, and recaptured the 390px implementation. Mobile width check passed.
4. Corrected the Google Pay radio's duplicate accessible name caused by decorative image alternative text. Wallet, keyboard, form, and cancellation checks subsequently passed.
5. Final comparison: matching full-view and focused evidence inspected; no further P0/P1/P2 changes needed. Platform-native radio/checkbox glyph appearance is P3.

## Behavior and verification

- Selecting a paid available plan creates the prototype checkout session using Quay's subscription-checkout request shape, displays the selected plan and price, and updates the mock subscription only after Subscribe.
- Change payment method uses the existing card-setup endpoint shape and opens the full-page payment update preview. Saved-card selection remains available separately.
- Form validation, US ZIP validation, country selection, Link/phone toggle, sample wallet controls, save/cancel/back navigation, refresh persistence, and namespace isolation were checked.
- The standalone checkout avoids loading the unrelated legacy Stripe/StatusPage scripts. Its console and uncaught-exception checks passed. The existing Quay shell still logs some mock backend/CORS and static-logo fallbacks after return; those are outside the checkout comparison and were not expanded into unrelated fixes.
- Live checkout/payment submission was not exercised. Payment and wallet actions on port 9010 remain simulated.

### Commands and outcomes

Working directory: `web/`.

- `npm test -- src/libs/billing.test.ts src/resources/BillingResource.test.ts src/routes/OrganizationsList/Organization/Tabs/Settings/BillingInformation.test.tsx`: passed, 32 tests.
- `PLAYWRIGHT_CHANNEL=chrome ./node_modules/.bin/playwright test --config playwright/prototype.config.ts --output /private/tmp/quay-stripe-final-results`: passed, 8 checks.
- `PLAYWRIGHT_CHANNEL=chrome ./node_modules/.bin/playwright test --config playwright/prototype.config.ts --output /private/tmp/quay-stripe-visual-final --grep 'mobile viewport|matches the full-page|fifteen dollar'`: passed, 3 checks after the mobile width correction.
- `PLAYWRIGHT_CHANNEL=chrome ./node_modules/.bin/playwright test --config playwright/prototype.config.ts --output /private/tmp/quay-stripe-checkout-console --grep 'matches the full-page'`: passed, checkout console and interaction check.
- `MOCK_API=true npm run build`: passed; existing bundle-size warnings remain.
- `./node_modules/.bin/tsc --noEmit --pretty false`: failed due to existing repository errors outside the added billing/checkout code; new PNG asset declarations resolved the new checkout asset imports. Full output: `/private/tmp/quay-stripe-typecheck.log`.
- `git diff --check`: passed.

## Commit preparation

All working changes, including the pre-existing design documents and lockfile changes, are included in the requested snapshot. The pre-existing `web/pnpm-lock.yaml` is truncated to empty importers/packages; it is preserved rather than regenerated. The PDF fixture paths are marked binary in `.gitattributes` to protect the PDF format's required spacing and avoid misleading text-diff warnings.

Installed the repository's pre-commit hook. The first attempt passed secret scanning, configuration checks, lockfile synchronization, Playwright tag checks, and whitespace checks, but failed on an empty subscription-modal error callback. Removed that callback and made the hook's error callback optional; inline mutation errors remain handled by the modal.

`npm test -- src/hooks/UseMarketplaceSubscriptions.test.ts src/resources/BillingResource.test.ts src/libs/billing.test.ts src/routes/OrganizationsList/Organization/Tabs/Settings/BillingInformation.test.tsx`: passed, 43 tests after the lint correction. `git diff --check` and `git diff --cached --check`: passed.

## Implementation checklist

- [x] Use the supplied checkout composition and brand assets.
- [x] Show selected-plan pricing in subscription checkout.
- [x] Open full-page payment updates directly.
- [x] Preserve saved-card selection and invoice downloads.
- [x] Verify save, cancel, back, wallet, and input states.
- [x] Correct mobile overflow and compare final captures.
- [x] Keep the prototype running on port 9010.

## Follow-up polish

- P3: browser-native radio/checkbox glyphs differ slightly from Stripe's bespoke controls. Their selection, focus, keyboard operation, size, and grouping are functional.

## Complete plan catalog correction

The four-entry prototype catalog omitted most tiers and incorrectly labeled Developer's $15/5-repository offer as Small. The prototype now uses all 11 active, visible plans from `data/billing.py`, captured in `web/src/tests/fake-db/data/billing/plans.json`: Open Source, Developer, Micro, Small, Medium, Large, Extra Large, XXL, XXXL, XXXXL, and XXXXXL. Small now correctly costs $60/month for 20 private repositories. XXXXXL costs $21,700/month for 15,000 repositories.

On the personal account's Change plan page, Medium remains in the separate current-plan card and the other ten plans appear as available cards. Organization eligibility filtering remains in place: Developer is an individual plan. The card layout and checkout behavior are preserved. Inspected the updated desktop capture at `/private/tmp/quay-complete-plan-catalog.png`; the additional rows scroll within the main content area.

Verification in `web/`:

- `MOCK_API=true npm run build`: passed, existing bundle-size warnings.
- `PLAYWRIGHT_CHANNEL=chrome ./node_modules/.bin/playwright test --config playwright/prototype.config.ts --output /private/tmp/quay-complete-catalog-results`: first sandbox attempt infrastructure-blocked at Chrome launch. The approved run passed eight existing checks; the new catalog check failed because its current-card assertion expected decimal formatting while the current card renders `$125/month`.
- `PLAYWRIGHT_CHANNEL=chrome ./node_modules/.bin/playwright test --config playwright/prototype.config.ts --output /private/tmp/quay-complete-catalog-recheck --grep 'complete Stripe catalog'`: passed after correcting that test assertion. Checked every tier's name, price, repository allowance, all nine available paid checkout summaries, cancellation preserving Medium, and the Open Source confirmation.
- `git diff --check`: passed.

All nine browser checks pass across the two approved runs. Payments and wallet actions remain simulated.

## Plan information summaries, subscriptions, and invoice settings

Implemented the approved Plan information revision:

- Removed the Select saved card action. Stored-card details and Change payment method remain.
- Replaced the inline Customer Portal subscription list with a count and View subscriptions link.
- Added `/organization/:organizationName/subscriptions` with a breadcrumb back to Plan information and a responsive table of subscription ID, SKU, quantity, namespace, and private-repository allowance. Personal accounts list every subscription and its assignment; organizations list their attached subscriptions. Existing attach/remove controls moved to this page.
- Renamed Invoice Settings to Invoices, added a count and View invoices link, and added an Invoice settings button.
- Moved the receipt checkbox, email field, Save, and Cancel into the Invoice settings modal. The initial sample state is checked with an email address. Saved preferences persist per namespace. Closing or canceling discards edits; invalid emails prevent saving when receipts are enabled; failed saves keep the modal open.

Visual evidence inspected:

- `/private/tmp/quay-plan-information-updated.png`: desktop summaries, navigation links, and absence of inline receipt settings.
- `/private/tmp/quay-customer-portal-subscriptions.png`: subscription list, assignment information, and return breadcrumb.
- `/private/tmp/quay-invoice-settings-modal.png`: checked receipt preference, email, and modal actions.
- `/private/tmp/quay-invoice-settings-mobile.png`: modal fits a 390px viewport.

Corrected organization subscription cache keys and propagated organization-fetch errors. Subscription mutations now await completion before reporting success. A browser check exposed an accessibility issue caused by the subscription select's dropdown being rendered outside the modal; its popup now renders inline within the modal, with keyboard focus and selection verified.

Commands run in `web/`:

- `npm test -- src/hooks/UseMarketplaceSubscriptions.test.ts src/resources/BillingResource.test.ts src/libs/billing.test.ts src/routes/OrganizationsList/Organization/Tabs/Settings/BillingInformation.test.tsx`: passed, 42 tests after extending cache-isolation and mutation-failure coverage.
- `PLAYWRIGHT_CHANNEL=chrome ./node_modules/.bin/playwright test --config playwright/prototype.config.ts --output /private/tmp/quay-plan-information-results`: 11 passed; subscription-controls check failed on the select toggle's accessible name.
- `PLAYWRIGHT_CHANNEL=chrome ./node_modules/.bin/playwright test --config playwright/prototype.config.ts --output /private/tmp/quay-subscription-controls-recheck --grep 'organization subscription attachment'`: failed; the select popup was hidden from accessibility queries outside the modal.
- `PLAYWRIGHT_CHANNEL=chrome ./node_modules/.bin/playwright test --config playwright/prototype.config.ts --output /private/tmp/quay-subscription-controls-final --grep 'organization subscription attachment'`: passed after correcting popup placement. Keyboard selection, attachment, removal, count updates, refresh persistence, and namespace assignments verified.
- `MOCK_API=true npm run build`: passed after the final source changes, with existing bundle-size warnings.
- `./node_modules/.bin/tsc --noEmit --pretty false`: failed on existing repository errors. New test-query typing errors were corrected; the final captured type-check output contains no errors in the changed billing/subscription files. Output: `/private/tmp/quay-plan-information-typecheck-final.log`.
- `git diff --check`: passed.

All 12 browser checks pass across the approved full run and final targeted recheck. The prototype remains local, with the dev server listening on port 9010. No live billing or Customer Portal integration was added.

## Invoice keyword search and bulk download

Added a responsive Search invoices field, result counts, a clear action, and a No matching invoices state. Search is case-insensitive and supports multiple keywords across invoice IDs, localized and ISO dates, written month names, amounts, plan IDs, and payment status. Paid searches exclude unpaid invoices.

Download all invoices downloads one ZIP containing all three sample invoice PDFs, including invoices hidden by the current search. The prototype archive was generated from the existing invoice fixture PDFs with Python's standard ZIP tooling. It is copied into the preview assets only with `MOCK_API=true`; bulk download remains disabled outside the prototype because a live archive endpoint is outside the approved scope. Individual PDF downloads and the breadcrumb remain available.

Inspected `/private/tmp/quay-invoice-search-and-bulk-download.png` (desktop). Mobile capture: `/private/tmp/quay-invoice-search-mobile.png`, 390px viewport, with the existing global navigation drawer closed to inspect the invoice controls.

Verification in `web/`:

- `npm test -- src/libs/billing.test.ts`: passed, 16 tests including keyword combinations and paid/unpaid distinction.
- `PLAYWRIGHT_CHANNEL=chrome ./node_modules/.bin/playwright test --config playwright/prototype.config.ts --output /private/tmp/quay-invoice-search-results --grep 'every invoice|invoice keyword|mobile viewport'`: individual PDF downloads and the existing mobile flow passed; the new bulk-download check failed because the asset copy pattern only included PDFs.
- Updated the mock asset pattern to include ZIP files and restarted the authorized preview server on port 9010.
- `PLAYWRIGHT_CHANNEL=chrome ./node_modules/.bin/playwright test --config playwright/prototype.config.ts --output /private/tmp/quay-invoice-search-final --grep 'invoice keyword'`: passed. Downloaded the ZIP through the browser, checked its CRCs with Python's ZIP reader, and verified all three entries contain PDF bytes. Also checked keyword filtering, clearing, empty results, and mobile content width.
- `PLAYWRIGHT_CHANNEL=chrome ./node_modules/.bin/playwright test --config playwright/prototype.config.ts --output /private/tmp/quay-invoice-search-mobile-final --grep 'invoice keyword'`: passed after closing the existing mobile navigation drawer for the final visual capture. Desktop and mobile images inspected.
- `MOCK_API=true npm run build`: passed after the asset fix; the ZIP is included in output. Existing bundle-size warnings remain.
- `./node_modules/.bin/tsc --noEmit --pretty false`: failed on existing repository errors; no errors in InvoiceList or billing helpers. Output: `/private/tmp/quay-invoice-search-typecheck.log`.
- `git diff --check`: passed.
