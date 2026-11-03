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
 * Version shapes produced by _init._get_version_number(), which /config
 * exposes as version_number = "Quay <version>" (endpoints/web.py):
 *
 *  - image build: the top CHANGELOG heading ("## [vX.Y.Z]") plus the
 *    BUILD_DATE the Dockerfile writes ("date -u +%Y%m%d%H%M"):
 *      "Quay v3.18.0-nightly-202608031425"
 *  - no BUILD_DATE (source checkout): "Quay v3.18.0"
 *
 * A runtime QUAY_VERSION env var replaces the built value entirely; that is a
 * dev/local override (docker-compose.yaml uses "local-dev"), so the downstream
 * lanes assert the built schema.
 */
const BUILT_VERSION_PATTERN = /^Quay v\d+\.\d+\.\d+(-nightly-\d{12})?$/;

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
      // The worker-scoped context can leak a previous test's theme preference
      await authenticatedPage.addInitScript(() =>
        localStorage.removeItem('theme-preference'),
      );
      await authenticatedPage.goto('/organization');

      const logo = authenticatedPage.getByAltText('Red Hat Quay');
      await expect(logo).toBeVisible();
      await expect(logo).toHaveAttribute('src', RED_HAT_BRANDING.logo);
    });

    test('header switches to dark logo variant', async ({
      authenticatedPage,
    }) => {
      await authenticatedPage.addInitScript(() =>
        localStorage.removeItem('theme-preference'),
      );
      await authenticatedPage.goto('/organization');

      const logo = authenticatedPage.getByAltText('Red Hat Quay');
      await expect(logo).toHaveAttribute('src', RED_HAT_BRANDING.logo);

      // Switch to dark theme (same flow as e2e/ui/theme-switcher.spec.ts)
      await authenticatedPage.getByTestId('user-menu-toggle').click();
      await authenticatedPage.locator('#toggle-group-dark-theme').click();
      await expect(authenticatedPage.locator('html')).toHaveClass(
        /pf-v6-theme-dark/,
      );
      await expect(logo).toHaveAttribute('src', RED_HAT_BRANDING.logo_dark);

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
      await expect(logo).toHaveAttribute('src', RED_HAT_BRANDING.logo);
    });

    test('sign-in page shows Red Hat branding', async ({
      unauthenticatedPage,
      quayConfig,
    }) => {
      await unauthenticatedPage.goto('/signin');

      // The login-page logo alt text is driven by REGISTRY_TITLE
      const logo = unauthenticatedPage.getByAltText('Red Hat Quay');
      await expect(logo).toBeVisible();
      await expect(logo).toHaveAttribute('src', RED_HAT_BRANDING.logo);

      await expect(unauthenticatedPage).toHaveTitle(
        `${RED_HAT_BRANDING.registry_title} • Quay`,
      );

      // The database login form (whose button label embeds REGISTRY_TITLE)
      // only renders when direct login is available; OIDC deployments show
      // external login buttons instead.
      const authType = quayConfig?.config?.AUTHENTICATION_TYPE;
      if (authType !== 'OIDC') {
        await expect(
          unauthenticatedPage.getByRole('button', {
            name: `Sign in to ${RED_HAT_BRANDING.registry_title}`,
          }),
        ).toBeVisible();
      }
    });

    test('footer shows Red Hat branding', async ({authenticatedPage}) => {
      await authenticatedPage.goto('/organization');

      const footerLogo = authenticatedPage.locator(
        '#quay-footer img[alt="Footer branding"]',
      );
      await expect(footerLogo).toBeVisible();
      await expect(footerLogo).toHaveAttribute(
        'src',
        RED_HAT_BRANDING.footer_img,
      );

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
      // downstream image must carry a CHANGELOG version and BUILD_DATE, so an
      // empty version here is a build defect.
      expect(
        versionNumber,
        `expected a version_number from /config, got ${JSON.stringify(versionNumber)}`,
      ).toMatch(BUILT_VERSION_PATTERN);
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
