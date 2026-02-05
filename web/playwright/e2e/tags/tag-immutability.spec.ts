import {test, expect} from '../../fixtures';
import {TEST_USERS} from '../../global-setup';
import {pushImage, isContainerRuntimeAvailable} from '../../utils/container';

test.describe(
  'Tag Immutability',
  {tag: ['@tags', '@immutability', '@feature:IMMUTABLE_TAGS']},
  () => {
    let hasContainerRuntime = false;

    test.beforeAll(async () => {
      hasContainerRuntime = await isContainerRuntimeAvailable();
    });

    test.beforeEach(async () => {
      test.skip(
        !hasContainerRuntime,
        'Skipping: no container runtime available to push test images',
      );
    });

    test('can make a tag immutable via kebab menu', async ({
      authenticatedPage,
      api,
    }) => {
      const repo = await api.repository();
      await pushImage(
        repo.namespace,
        repo.name,
        'v1.0.0',
        TEST_USERS.user.username,
        TEST_USERS.user.password,
      );

      await authenticatedPage.goto(`/repository/${repo.fullName}?tab=tags`);

      await expect(
        authenticatedPage.getByRole('link', {name: 'v1.0.0'}),
      ).toBeVisible();

      const tagRow = authenticatedPage
        .getByRole('row')
        .filter({has: authenticatedPage.getByRole('link', {name: 'v1.0.0'})});

      await expect(tagRow.getByTestId('immutable-tag-icon')).not.toBeVisible();

      await tagRow.getByLabel('Tag actions kebab').click();
      await authenticatedPage
        .getByRole('menuitem', {name: 'Make immutable'})
        .click();

      await expect(
        authenticatedPage.getByTestId('immutability-modal'),
      ).toBeVisible();
      await expect(
        authenticatedPage.getByText('Make 1 tag immutable?'),
      ).toBeVisible();

      await authenticatedPage.getByTestId('confirm-immutability-btn').click();

      await expect(
        authenticatedPage.getByTestId('immutability-modal'),
      ).not.toBeVisible();

      await expect(tagRow.getByTestId('immutable-tag-icon')).toBeVisible({
        timeout: 10000,
      });
    });

    test('displays lock icon for immutable tags', async ({
      authenticatedPage,
      api,
    }) => {
      const repo = await api.repository();

      // Push and set immutable in parallel
      await pushImage(
        repo.namespace,
        repo.name,
        'v1.0.0',
        TEST_USERS.user.username,
        TEST_USERS.user.password,
      );
      await api.raw.setTagImmutability(
        repo.namespace,
        repo.name,
        'v1.0.0',
        true,
      );

      await authenticatedPage.goto(`/repository/${repo.fullName}?tab=tags`);

      await expect(
        authenticatedPage.getByRole('link', {name: 'v1.0.0'}),
      ).toBeVisible();

      const tagRow = authenticatedPage
        .getByRole('row')
        .filter({has: authenticatedPage.getByRole('link', {name: 'v1.0.0'})});
      await expect(tagRow.getByTestId('immutable-tag-icon')).toBeVisible();
    });

    test('delete action is disabled for immutable tags', async ({
      authenticatedPage,
      api,
    }) => {
      const repo = await api.repository();
      await pushImage(
        repo.namespace,
        repo.name,
        'v1.0.0',
        TEST_USERS.user.username,
        TEST_USERS.user.password,
      );
      await api.raw.setTagImmutability(
        repo.namespace,
        repo.name,
        'v1.0.0',
        true,
      );

      await authenticatedPage.goto(`/repository/${repo.fullName}?tab=tags`);

      await expect(
        authenticatedPage.getByRole('link', {name: 'v1.0.0'}),
      ).toBeVisible();

      const tagRow = authenticatedPage
        .getByRole('row')
        .filter({has: authenticatedPage.getByRole('link', {name: 'v1.0.0'})});
      await tagRow.getByLabel('Tag actions kebab').click();

      const removeAction = authenticatedPage.getByRole('menuitem', {
        name: 'Remove',
        exact: true,
      });
      await expect(removeAction).toBeDisabled();
    });

    test('change expiration is disabled for immutable tags', async ({
      authenticatedPage,
      api,
    }) => {
      const repo = await api.repository();
      await pushImage(
        repo.namespace,
        repo.name,
        'v1.0.0',
        TEST_USERS.user.username,
        TEST_USERS.user.password,
      );
      await api.raw.setTagImmutability(
        repo.namespace,
        repo.name,
        'v1.0.0',
        true,
      );

      await authenticatedPage.goto(`/repository/${repo.fullName}?tab=tags`);

      await expect(
        authenticatedPage.getByRole('link', {name: 'v1.0.0'}),
      ).toBeVisible();

      const tagRow = authenticatedPage
        .getByRole('row')
        .filter({has: authenticatedPage.getByRole('link', {name: 'v1.0.0'})});
      await tagRow.getByLabel('Tag actions kebab').click();

      const expirationAction = authenticatedPage.getByRole('menuitem', {
        name: 'Change expiration',
      });
      await expect(expirationAction).toBeDisabled();
    });

    test('bulk delete shows warning for immutable tags', async ({
      authenticatedPage,
      api,
    }) => {
      const repo = await api.repository();

      // Push both images in parallel
      await Promise.all([
        pushImage(
          repo.namespace,
          repo.name,
          'immutable-tag',
          TEST_USERS.user.username,
          TEST_USERS.user.password,
        ),
        pushImage(
          repo.namespace,
          repo.name,
          'mutable-tag',
          TEST_USERS.user.username,
          TEST_USERS.user.password,
        ),
      ]);

      await api.raw.setTagImmutability(
        repo.namespace,
        repo.name,
        'immutable-tag',
        true,
      );

      await authenticatedPage.goto(`/repository/${repo.fullName}?tab=tags`);

      await expect(
        authenticatedPage.getByRole('link', {
          name: 'immutable-tag',
          exact: true,
        }),
      ).toBeVisible();
      await expect(
        authenticatedPage.getByRole('link', {name: 'mutable-tag', exact: true}),
      ).toBeVisible();

      const immutableRow = authenticatedPage.getByRole('row').filter({
        has: authenticatedPage.getByRole('link', {
          name: 'immutable-tag',
          exact: true,
        }),
      });
      const mutableRow = authenticatedPage.getByRole('row').filter({
        has: authenticatedPage.getByRole('link', {
          name: 'mutable-tag',
          exact: true,
        }),
      });

      await immutableRow.getByRole('checkbox').click();
      await mutableRow.getByRole('checkbox').click();

      await authenticatedPage.getByTestId('bulk-actions-kebab').click();
      await authenticatedPage
        .getByRole('menuitem', {name: 'Remove', exact: true})
        .click();

      await expect(
        authenticatedPage.getByTestId('immutable-tags-warning'),
      ).toBeVisible();
      await expect(
        authenticatedPage.getByText('Immutable tags will be skipped'),
      ).toBeVisible();

      await authenticatedPage.getByRole('button', {name: 'Cancel'}).click();
    });

    test('bulk make immutable is disabled when all selected tags are already immutable', async ({
      authenticatedPage,
      api,
    }) => {
      const repo = await api.repository();
      await pushImage(
        repo.namespace,
        repo.name,
        'already-immutable',
        TEST_USERS.user.username,
        TEST_USERS.user.password,
      );
      await api.raw.setTagImmutability(
        repo.namespace,
        repo.name,
        'already-immutable',
        true,
      );

      await authenticatedPage.goto(`/repository/${repo.fullName}?tab=tags`);

      await expect(
        authenticatedPage.getByRole('link', {name: 'already-immutable'}),
      ).toBeVisible();

      const immutableRow = authenticatedPage.getByRole('row').filter({
        has: authenticatedPage.getByRole('link', {name: 'already-immutable'}),
      });
      await immutableRow.getByRole('checkbox').click();

      await authenticatedPage.getByTestId('bulk-actions-kebab').click();

      const makeImmutableAction = authenticatedPage.getByTestId(
        'bulk-make-immutable-action',
      );
      // PatternFly uses pf-m-disabled class on li elements, not disabled attribute
      await expect(makeImmutableAction).toHaveClass(/pf-m-disabled/);
    });

    test('superuser can remove immutability from a tag', async ({
      superuserPage,
      superuserApi,
    }) => {
      const repo = await superuserApi.repository();
      await pushImage(
        repo.namespace,
        repo.name,
        'immutable-tag',
        TEST_USERS.admin.username,
        TEST_USERS.admin.password,
      );
      await superuserApi.raw.setTagImmutability(
        repo.namespace,
        repo.name,
        'immutable-tag',
        true,
      );

      await superuserPage.goto(`/repository/${repo.fullName}?tab=tags`);

      await expect(
        superuserPage.getByRole('link', {name: 'immutable-tag', exact: true}),
      ).toBeVisible();

      const tagRow = superuserPage.getByRole('row').filter({
        has: superuserPage.getByRole('link', {
          name: 'immutable-tag',
          exact: true,
        }),
      });
      await expect(tagRow.getByTestId('immutable-tag-icon')).toBeVisible();

      await tagRow.getByLabel('Tag actions kebab').click();
      await superuserPage
        .getByRole('menuitem', {name: 'Remove immutability'})
        .click();

      await expect(
        superuserPage.getByTestId('immutability-modal'),
      ).toBeVisible();
      await expect(
        superuserPage.getByText('Remove immutability from 1 tag?'),
      ).toBeVisible();

      await superuserPage.getByTestId('confirm-immutability-btn').click();

      await expect(
        superuserPage.getByTestId('immutability-modal'),
      ).not.toBeVisible();

      await expect(tagRow.getByTestId('immutable-tag-icon')).not.toBeVisible({
        timeout: 10000,
      });
    });

    test('bulk set expiration shows warning for immutable tags', async ({
      authenticatedPage,
      api,
    }) => {
      const repo = await api.repository();

      // Push both images
      await Promise.all([
        pushImage(
          repo.namespace,
          repo.name,
          'immutable-tag',
          TEST_USERS.user.username,
          TEST_USERS.user.password,
        ),
        pushImage(
          repo.namespace,
          repo.name,
          'mutable-tag',
          TEST_USERS.user.username,
          TEST_USERS.user.password,
        ),
      ]);

      // Make one tag immutable
      await api.raw.setTagImmutability(
        repo.namespace,
        repo.name,
        'immutable-tag',
        true,
      );

      await authenticatedPage.goto(`/repository/${repo.fullName}?tab=tags`);

      await expect(
        authenticatedPage.getByRole('link', {
          name: 'immutable-tag',
          exact: true,
        }),
      ).toBeVisible();
      await expect(
        authenticatedPage.getByRole('link', {name: 'mutable-tag', exact: true}),
      ).toBeVisible();

      // Select both tags
      const immutableRow = authenticatedPage.getByRole('row').filter({
        has: authenticatedPage.getByRole('link', {
          name: 'immutable-tag',
          exact: true,
        }),
      });
      const mutableRow = authenticatedPage.getByRole('row').filter({
        has: authenticatedPage.getByRole('link', {
          name: 'mutable-tag',
          exact: true,
        }),
      });

      await immutableRow.getByRole('checkbox').click();
      await mutableRow.getByRole('checkbox').click();

      // Open bulk actions and click set expiration
      await authenticatedPage.getByTestId('bulk-actions-kebab').click();
      await authenticatedPage
        .getByRole('menuitem', {name: 'Set expiration'})
        .click();

      // Should show warning about immutable tags being skipped
      await expect(
        authenticatedPage.getByTestId('immutable-tags-expiration-warning'),
      ).toBeVisible();
      await expect(
        authenticatedPage.getByText('Immutable tags will be skipped'),
      ).toBeVisible();

      await authenticatedPage.getByRole('button', {name: 'Cancel'}).click();
    });

    test('make immutable is disabled for tags with expiration', async ({
      authenticatedPage,
      api,
    }) => {
      const repo = await api.repository();
      await pushImage(
        repo.namespace,
        repo.name,
        'expiring-tag',
        TEST_USERS.user.username,
        TEST_USERS.user.password,
      );

      // Set expiration to 30 days from now
      const expirationTimestamp =
        Math.floor(Date.now() / 1000) + 30 * 24 * 60 * 60;
      await api.raw.setTagExpiration(
        repo.namespace,
        repo.name,
        'expiring-tag',
        expirationTimestamp,
      );

      await authenticatedPage.goto(`/repository/${repo.fullName}?tab=tags`);

      await expect(
        authenticatedPage.getByRole('link', {
          name: 'expiring-tag',
          exact: true,
        }),
      ).toBeVisible();

      const tagRow = authenticatedPage.getByRole('row').filter({
        has: authenticatedPage.getByRole('link', {
          name: 'expiring-tag',
          exact: true,
        }),
      });
      await tagRow.getByLabel('Tag actions kebab').click();

      const makeImmutableAction = authenticatedPage.getByRole('menuitem', {
        name: 'Make immutable',
      });
      await expect(makeImmutableAction).toBeDisabled();
    });

    test('bulk make immutable shows warning for tags with expiration', async ({
      authenticatedPage,
      api,
    }) => {
      const repo = await api.repository();

      // Push both images
      await Promise.all([
        pushImage(
          repo.namespace,
          repo.name,
          'expiring-tag',
          TEST_USERS.user.username,
          TEST_USERS.user.password,
        ),
        pushImage(
          repo.namespace,
          repo.name,
          'non-expiring-tag',
          TEST_USERS.user.username,
          TEST_USERS.user.password,
        ),
      ]);

      // Set expiration on one tag
      const expirationTimestamp =
        Math.floor(Date.now() / 1000) + 30 * 24 * 60 * 60;
      await api.raw.setTagExpiration(
        repo.namespace,
        repo.name,
        'expiring-tag',
        expirationTimestamp,
      );

      await authenticatedPage.goto(`/repository/${repo.fullName}?tab=tags`);

      await expect(
        authenticatedPage.getByRole('link', {
          name: 'expiring-tag',
          exact: true,
        }),
      ).toBeVisible();
      await expect(
        authenticatedPage.getByRole('link', {
          name: 'non-expiring-tag',
          exact: true,
        }),
      ).toBeVisible();

      // Select both tags
      const expiringRow = authenticatedPage.getByRole('row').filter({
        has: authenticatedPage.getByRole('link', {
          name: 'expiring-tag',
          exact: true,
        }),
      });
      const nonExpiringRow = authenticatedPage.getByRole('row').filter({
        has: authenticatedPage.getByRole('link', {
          name: 'non-expiring-tag',
          exact: true,
        }),
      });

      await expiringRow.getByRole('checkbox').click();
      await nonExpiringRow.getByRole('checkbox').click();

      // Open bulk actions and click make immutable
      await authenticatedPage.getByTestId('bulk-actions-kebab').click();
      await authenticatedPage
        .getByRole('menuitem', {name: 'Make immutable'})
        .click();

      // Should show warning about expiring tags being skipped
      await expect(
        authenticatedPage.getByTestId('expiring-tags-immutability-warning'),
      ).toBeVisible();
      await expect(
        authenticatedPage.getByText('Tags with expiration will be skipped'),
      ).toBeVisible();

      await authenticatedPage.getByRole('button', {name: 'Cancel'}).click();
    });

    test('bulk make immutable is disabled when all mutable tags have expiration', async ({
      authenticatedPage,
      api,
    }) => {
      const repo = await api.repository();

      // Push two images
      await Promise.all([
        pushImage(
          repo.namespace,
          repo.name,
          'expiring-tag-1',
          TEST_USERS.user.username,
          TEST_USERS.user.password,
        ),
        pushImage(
          repo.namespace,
          repo.name,
          'expiring-tag-2',
          TEST_USERS.user.username,
          TEST_USERS.user.password,
        ),
      ]);

      // Set expiration on BOTH tags
      const expirationTimestamp =
        Math.floor(Date.now() / 1000) + 30 * 24 * 60 * 60;
      await Promise.all([
        api.raw.setTagExpiration(
          repo.namespace,
          repo.name,
          'expiring-tag-1',
          expirationTimestamp,
        ),
        api.raw.setTagExpiration(
          repo.namespace,
          repo.name,
          'expiring-tag-2',
          expirationTimestamp,
        ),
      ]);

      await authenticatedPage.goto(`/repository/${repo.fullName}?tab=tags`);

      await expect(
        authenticatedPage.getByRole('link', {
          name: 'expiring-tag-1',
          exact: true,
        }),
      ).toBeVisible();
      await expect(
        authenticatedPage.getByRole('link', {
          name: 'expiring-tag-2',
          exact: true,
        }),
      ).toBeVisible();

      // Select both tags
      const row1 = authenticatedPage.getByRole('row').filter({
        has: authenticatedPage.getByRole('link', {
          name: 'expiring-tag-1',
          exact: true,
        }),
      });
      const row2 = authenticatedPage.getByRole('row').filter({
        has: authenticatedPage.getByRole('link', {
          name: 'expiring-tag-2',
          exact: true,
        }),
      });

      await row1.getByRole('checkbox').click();
      await row2.getByRole('checkbox').click();

      // Open bulk actions kebab
      await authenticatedPage.getByTestId('bulk-actions-kebab').click();

      const makeImmutableAction = authenticatedPage.getByTestId(
        'bulk-make-immutable-action',
      );
      // PatternFly uses pf-m-disabled class on li elements, not disabled attribute
      await expect(makeImmutableAction).toHaveClass(/pf-m-disabled/);
    });

    test('immutable tags display Never for expiration', async ({
      authenticatedPage,
      api,
    }) => {
      const repo = await api.repository();
      await pushImage(
        repo.namespace,
        repo.name,
        'immutable-tag',
        TEST_USERS.user.username,
        TEST_USERS.user.password,
      );
      await api.raw.setTagImmutability(
        repo.namespace,
        repo.name,
        'immutable-tag',
        true,
      );

      await authenticatedPage.goto(`/repository/${repo.fullName}?tab=tags`);

      await expect(
        authenticatedPage.getByRole('link', {
          name: 'immutable-tag',
          exact: true,
        }),
      ).toBeVisible();

      const tagRow = authenticatedPage.getByRole('row').filter({
        has: authenticatedPage.getByRole('link', {
          name: 'immutable-tag',
          exact: true,
        }),
      });

      // Verify the expiration column shows "Never"
      await expect(tagRow.getByText('Never')).toBeVisible();
    });
  },
);
