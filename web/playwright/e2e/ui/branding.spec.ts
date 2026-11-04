import type {Locator} from '@playwright/test';

import {test, expect} from '../../fixtures';

/**
 * Downstream branding defaults served when the image is built with
 * RED_HAT_QUAY=true (see BRANDING / REGISTRY_TITLE in config.py).
 * Keep in sync with those defaults; asset renames should only need edits here.
 */
const RED_HAT_BRANDING = {
  logo: '/static/img/RH_Logo_Quay_Black_UX-horizontal.svg',
  logo_dark: '/static/img/RH_Logo_Quay_White_UX-horizontal.svg',
  footer_img: '/static/img/RedHat.svg',
  // The trailing version segment of the docs URL drifts across releases;
  // assert on the stable prefix only.
  footer_url_prefix:
    'https://access.redhat.com/documentation/en-us/red_hat_quay',
  registry_title: 'Red Hat Quay',
};

const brandingE2E = process.env.PLAYWRIGHT_BRANDING_E2E === '1';

/**
 * Version reported by /config.version_number = "Quay <version>" (endpoints/web.py),
 * resolved by _init._get_version_number(). Both downstream shapes are valid:
 *
 *   - Release form: "Quay v3.18.1". The operator sets QUAY_VERSION on the Quay
 *     pod from the installed release, and that value replaces the built one
 *     entirely; release images also carry no BUILD_DATE.
 *   - Nightly form: "Quay v3.18.0-nightly-202608031425" — top CHANGELOG heading
 *     ("## [vX.Y.Z]") plus the BUILD_DATE the Dockerfile writes
 *     ("date -u +%Y%m%d%H%M").
 *
 * A versionless or malformed value is a defect either way.
 */
const DOWNSTREAM_VERSION_PATTERN = /^Quay v\d+\.\d+\.\d+(-nightly-\d{12})?$/;

/**
 * A pinned src can still 404: the <img> keeps its alt text and stays "visible"
 * even when the asset is missing. Assert the browser decoded it as well, so a
 * renamed or dropped image fails here instead of passing on the config string.
 * expect.poll waits for the load (and for a theme swap to swap the src).
 */
async function expectLoadedImage(image: Locator, src: string) {
  await expect(image).toBeVisible();
  await expect(image).toHaveAttribute('src', src);
  await expect
    .poll(() => image.evaluate((el) => (el as HTMLImageElement).naturalWidth))
    .toBeGreaterThan(0);
}

test.describe(
  'Red Hat Quay branding (downstream image)',
  {tag: ['@ui', '@redhat-branding']},
  () => {
    test.skip(
      !brandingE2E,
      'requires a downstream Red Hat Quay image (PLAYWRIGHT_BRANDING_E2E=1)',
    );

    test('/config reports Red Hat branding', async ({quayConfig}) => {
      const branding = quayConfig?.config?.BRANDING as
        | Record<string, string | null>
        | undefined;

      expect(branding?.logo).toBe(RED_HAT_BRANDING.logo);
      expect(branding?.logo_dark).toBe(RED_HAT_BRANDING.logo_dark);
      expect(branding?.footer_img).toBe(RED_HAT_BRANDING.footer_img);
      expect(branding?.footer_url).toContain(
        RED_HAT_BRANDING.footer_url_prefix,
      );
      expect(quayConfig?.config?.REGISTRY_TITLE).toBe(
        RED_HAT_BRANDING.registry_title,
      );
    });

    test('header shows Red Hat logo in light theme', async ({
      authenticatedPage,
    }) => {
      // The worker-scoped context can leak a previous test's theme preference.
      // With no stored preference the app falls back to AUTO and follows
      // prefers-color-scheme (ThemeContext.tsx), so pin the media preference too.
      await authenticatedPage.emulateMedia({colorScheme: 'light'});
      await authenticatedPage.addInitScript(() =>
        localStorage.removeItem('theme-preference'),
      );
      await authenticatedPage.goto('/organization');

      const logo = authenticatedPage.getByAltText('Red Hat Quay');
      await expectLoadedImage(logo, RED_HAT_BRANDING.logo);
    });

    test('header switches to dark logo variant', async ({
      authenticatedPage,
    }) => {
      await authenticatedPage.emulateMedia({colorScheme: 'light'});
      await authenticatedPage.addInitScript(() =>
        localStorage.removeItem('theme-preference'),
      );
      await authenticatedPage.goto('/organization');

      const logo = authenticatedPage.getByAltText('Red Hat Quay');
      await expectLoadedImage(logo, RED_HAT_BRANDING.logo);

      // Switch to dark theme (same flow as e2e/ui/theme-switcher.spec.ts)
      await authenticatedPage.getByTestId('user-menu-toggle').click();
      await authenticatedPage.locator('#toggle-group-dark-theme').click();
      await expect(authenticatedPage.locator('html')).toHaveClass(
        /pf-v6-theme-dark/,
      );
      await expectLoadedImage(logo, RED_HAT_BRANDING.logo_dark);

      // Reset so the shared worker context does not leak DARK to other tests.
      // Clear the stored preference and reload rather than driving the menu
      // again: clicking a ToggleGroupItem keeps the menu open, so a second
      // toggle click would close it instead of reaching the light option.
      await authenticatedPage.evaluate(() =>
        localStorage.removeItem('theme-preference'),
      );
      await authenticatedPage.reload();
      await expect(authenticatedPage.locator('html')).not.toHaveClass(
        /pf-v6-theme-dark/,
      );
      await expectLoadedImage(logo, RED_HAT_BRANDING.logo);
    });

    test('sign-in page shows Red Hat branding', async ({
      unauthenticatedPage,
      quayConfig,
    }) => {
      // Signin.tsx starts the external login on mount when exactly one provider
      // is configured and DIRECT_LOGIN is off (hasSingleSignin() in
      // UseExternalLogins.ts), for any provider type. The browser can leave
      // /signin before the branding assertions settle, so the page is not a
      // stable target in that configuration.
      const externalLogins = quayConfig?.external_login ?? [];
      test.skip(
        externalLogins.length === 1 && !quayConfig?.features?.DIRECT_LOGIN,
        'sign-in page auto-redirects to the single configured external login',
      );

      // Same AUTO-theme caveat as the header test: the login page is rendered
      // before any stored preference exists, so pin the media preference.
      await unauthenticatedPage.emulateMedia({colorScheme: 'light'});
      await unauthenticatedPage.goto('/signin');

      // The login-page logo alt text is driven by REGISTRY_TITLE
      const logo = unauthenticatedPage.getByAltText('Red Hat Quay');
      await expectLoadedImage(logo, RED_HAT_BRANDING.logo);

      await expect(unauthenticatedPage).toHaveTitle(
        `${RED_HAT_BRANDING.registry_title} • Quay`,
      );

      // The database login form (whose button label embeds REGISTRY_TITLE)
      // renders only when direct login is available — DIRECT_LOGIN enabled and
      // a non-OIDC auth type (shouldShowDirectLogin() in UseExternalLogins.ts);
      // OIDC deployments show external login buttons instead.
      const authType = quayConfig?.config?.AUTHENTICATION_TYPE;
      const directLogin = quayConfig?.features?.DIRECT_LOGIN === true;
      if (directLogin && authType !== 'OIDC') {
        await expect(
          unauthenticatedPage.getByRole('button', {
            name: `Sign in to ${RED_HAT_BRANDING.registry_title}`,
            exact: true,
          }),
        ).toBeVisible();
      }
    });

    test('footer shows Red Hat branding', async ({authenticatedPage}) => {
      await authenticatedPage.goto('/organization');

      const footerLogo = authenticatedPage.locator(
        '#quay-footer img[alt="Footer branding"]',
      );
      await expectLoadedImage(footerLogo, RED_HAT_BRANDING.footer_img);

      // Downstream wraps the footer logo in a link to the Red Hat docs
      await expect(
        authenticatedPage.locator(
          '#quay-footer a[href*="access.redhat.com"] img[alt="Footer branding"]',
        ),
      ).toBeVisible();
    });

    test('/config reports a Quay version', async ({quayConfig}) => {
      const versionNumber = quayConfig?.version_number;

      // /config returns "" when BILLING is enabled (endpoints/web.py), but a
      // downstream image or operator deployment must report a version, so an
      // empty or malformed value here is a defect.
      expect(
        versionNumber,
        `expected a version_number from /config, got ${JSON.stringify(versionNumber)}`,
      ).toMatch(DOWNSTREAM_VERSION_PATTERN);
    });

    test('help menu shows the version reported by /config', async ({
      authenticatedPage,
      quayConfig,
    }) => {
      const versionNumber = quayConfig?.version_number;
      test.skip(!versionNumber, 'No version_number in /config');

      await authenticatedPage.goto('/organization');
      await authenticatedPage.getByTestId('help-menu-toggle').click();

      const versionItem = authenticatedPage.getByTestId('help-version-info');
      await expect(versionItem).toBeVisible();
      await expect(versionItem).toHaveText(versionNumber as string);
    });
  },
);
