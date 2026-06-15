import {test, expect, skipUnlessFeature} from '../../fixtures';

/**
 * Confirm Invite tests verify the /confirminvite route added for
 * PROJQUAY-11636. Tests that need a real invite code use the
 * @feature:INVITE_ONLY_USER_CREATION tag.
 */

test.describe('Confirm Invite Page', {tag: ['@auth']}, () => {
  test('shows error when no invite code is in the URL', async ({
    unauthenticatedPage,
  }) => {
    await unauthenticatedPage.goto('/confirminvite');

    await expect(
      unauthenticatedPage.getByTestId('confirm-invite-error'),
    ).toBeVisible({
      timeout: 10_000,
    });
    await expect(
      unauthenticatedPage.getByText(/No invite code/i),
    ).toBeVisible();
  });

  test('shows sign-in and create-account options for unauthenticated user', async ({
    unauthenticatedPage,
  }) => {
    await unauthenticatedPage.goto('/confirminvite?code=somefakecode');

    await expect(
      unauthenticatedPage.getByTestId('confirm-invite-unauthenticated'),
    ).toBeVisible({timeout: 10_000});

    await expect(
      unauthenticatedPage.getByTestId('confirm-invite-signin-btn'),
    ).toBeVisible();
    await expect(
      unauthenticatedPage.getByTestId('confirm-invite-create-account-btn'),
    ).toBeVisible();
  });

  test('sign-in and create-account buttons preserve invite code in URL', async ({
    unauthenticatedPage,
  }) => {
    await unauthenticatedPage.goto('/confirminvite?code=myinvitecode');

    await expect(
      unauthenticatedPage.getByTestId('confirm-invite-signin-btn'),
    ).toBeVisible({timeout: 10_000});

    const signinHref = await unauthenticatedPage
      .getByTestId('confirm-invite-signin-btn')
      .getAttribute('href');
    expect(signinHref).toContain('code=myinvitecode');

    const createHref = await unauthenticatedPage
      .getByTestId('confirm-invite-create-account-btn')
      .getAttribute('href');
    expect(createHref).toContain('code=myinvitecode');
  });

  test('sign-in button navigates to /signin with code param', async ({
    unauthenticatedPage,
  }) => {
    await unauthenticatedPage.goto('/confirminvite?code=nav-test-code');

    await expect(
      unauthenticatedPage.getByTestId('confirm-invite-signin-btn'),
    ).toBeVisible({timeout: 10_000});

    await unauthenticatedPage.getByTestId('confirm-invite-signin-btn').click();

    await expect(unauthenticatedPage).toHaveURL(/\/signin\?code=nav-test-code/);
  });

  test('create-account button navigates to /createaccount with code param', async ({
    unauthenticatedPage,
  }) => {
    await unauthenticatedPage.goto('/confirminvite?code=nav-create-code');

    await expect(
      unauthenticatedPage.getByTestId('confirm-invite-create-account-btn'),
    ).toBeVisible({timeout: 10_000});

    await unauthenticatedPage
      .getByTestId('confirm-invite-create-account-btn')
      .click();

    await expect(unauthenticatedPage).toHaveURL(
      /\/createaccount\?code=nav-create-code/,
    );

    await expect(
      unauthenticatedPage.getByTestId('invite-code-alert'),
    ).toBeVisible();
    await expect(
      unauthenticatedPage.getByText("You've been invited to join a team"),
    ).toBeVisible();
  });

  test('authenticated user with invalid code sees error', async ({
    authenticatedPage,
  }) => {
    await authenticatedPage.goto('/confirminvite?code=invalid-code-xyz');

    await expect(
      authenticatedPage.getByTestId('confirm-invite-error'),
    ).toBeVisible({timeout: 10_000});
  });

  test('create-account page shows invite banner when code is present', async ({
    unauthenticatedPage,
  }) => {
    await unauthenticatedPage.goto('/createaccount?code=testcode');

    await expect(
      unauthenticatedPage.getByTestId('invite-code-alert'),
    ).toBeVisible({
      timeout: 10_000,
    });
    await expect(
      unauthenticatedPage.getByText("You've been invited to join a team"),
    ).toBeVisible();
  });

  test('create-account page preserves invite code in sign-in link', async ({
    unauthenticatedPage,
    quayConfig,
  }) => {
    test.skip(
      quayConfig?.config?.AUTHENTICATION_TYPE !== 'Database',
      'Create account page requires Database auth',
    );

    await unauthenticatedPage.goto('/createaccount?code=link-code');

    const signinLink = unauthenticatedPage.getByRole('link', {
      name: 'Sign in',
    });
    await expect(signinLink).toBeVisible({timeout: 10_000});

    const href = await signinLink.getAttribute('href');
    expect(href).toContain('code=link-code');
  });

  test(
    'signin page shows create-account link when invite code is present',
    {tag: '@feature:INVITE_ONLY_USER_CREATION'},
    async ({unauthenticatedPage, quayConfig}) => {
      test.skip(...skipUnlessFeature(quayConfig, 'INVITE_ONLY_USER_CREATION'));

      await unauthenticatedPage.goto('/signin?code=somecode');

      await expect(
        unauthenticatedPage.getByTestId('signin-create-account-link'),
      ).toBeVisible({timeout: 10_000});

      const href = await unauthenticatedPage
        .getByTestId('signin-create-account-link')
        .getAttribute('href');
      expect(href).toContain('code=somecode');
    },
  );
});
