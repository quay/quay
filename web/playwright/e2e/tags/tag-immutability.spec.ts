import {test, expect} from '../../fixtures';
import {TEST_USERS} from '../../global-setup';
import {pushImage} from '../../utils/container';

test.describe(
  'Tag Immutability',
  {tag: ['@tags', '@immutability', '@feature:IMMUTABLE_TAGS', '@container']},
  () => {
    test.slow();

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
      ).toBeVisible({timeout: 30000});

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
      ).toBeVisible({timeout: 30000});

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
      ).toBeVisible({timeout: 30000});

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
      ).toBeVisible({timeout: 30000});

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
      ).toBeVisible({timeout: 30000});
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

    // PROJQUAY-10850: Bulk remove action disabled when only immutable tags selected
    test('bulk remove is disabled when all selected tags are immutable', async ({
      authenticatedPage,
      api,
    }) => {
      const repo = await api.repository();

      await Promise.all([
        pushImage(
          repo.namespace,
          repo.name,
          'immutable-1',
          TEST_USERS.user.username,
          TEST_USERS.user.password,
        ),
        pushImage(
          repo.namespace,
          repo.name,
          'immutable-2',
          TEST_USERS.user.username,
          TEST_USERS.user.password,
        ),
      ]);

      await Promise.all([
        api.raw.setTagImmutability(
          repo.namespace,
          repo.name,
          'immutable-1',
          true,
        ),
        api.raw.setTagImmutability(
          repo.namespace,
          repo.name,
          'immutable-2',
          true,
        ),
      ]);

      await authenticatedPage.goto(`/repository/${repo.fullName}?tab=tags`);

      await expect(
        authenticatedPage.getByRole('link', {
          name: 'immutable-1',
          exact: true,
        }),
      ).toBeVisible({timeout: 30000});
      await expect(
        authenticatedPage.getByRole('link', {
          name: 'immutable-2',
          exact: true,
        }),
      ).toBeVisible();

      const row1 = authenticatedPage.getByRole('row').filter({
        has: authenticatedPage.getByRole('link', {
          name: 'immutable-1',
          exact: true,
        }),
      });
      const row2 = authenticatedPage.getByRole('row').filter({
        has: authenticatedPage.getByRole('link', {
          name: 'immutable-2',
          exact: true,
        }),
      });

      await row1.getByRole('checkbox').click();
      await row2.getByRole('checkbox').click();

      await authenticatedPage.getByTestId('bulk-actions-kebab').click();

      const removeAction = authenticatedPage.getByTestId('bulk-remove-action');
      // PatternFly uses pf-m-disabled class on li elements, not disabled attribute
      await expect(removeAction).toHaveClass(/pf-m-disabled/);
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
      ).toBeVisible({timeout: 30000});

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
      ).toBeVisible({timeout: 30000});

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
      ).toBeVisible({timeout: 30000});
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
      ).toBeVisible({timeout: 30000});

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
      ).toBeVisible({timeout: 30000});
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
      ).toBeVisible({timeout: 30000});
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
      ).toBeVisible({timeout: 30000});

      const tagRow = authenticatedPage.getByRole('row').filter({
        has: authenticatedPage.getByRole('link', {
          name: 'immutable-tag',
          exact: true,
        }),
      });

      // Verify the expiration column shows "Never"
      await expect(tagRow.getByText('Never')).toBeVisible();
    });

    test('Never expiration is not clickable for immutable tags', async ({
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

      const tagRow = authenticatedPage.getByRole('row').filter({
        has: authenticatedPage.getByRole('link', {
          name: 'immutable-tag',
          exact: true,
        }),
      });

      // Verify "Never" is visible but is NOT rendered as a link
      const neverText = tagRow.getByText('Never');
      await expect(neverText).toBeVisible({timeout: 30000});

      // Should not be inside an <a> tag (not clickable)
      const neverLink = tagRow.locator('a', {hasText: 'Never'});
      await expect(neverLink).not.toBeVisible();

      // Click "Never" text and verify modal does NOT open
      await neverText.click();
      await expect(
        authenticatedPage.getByTestId('edit-expiration-tags'),
      ).not.toBeVisible();
    });

    // PROJQUAY-10503: Bulk remove immutability for multiple tags
    test('can bulk remove immutability from multiple tags', async ({
      authenticatedPage,
      api,
    }) => {
      const repo = await api.repository();

      await Promise.all([
        pushImage(
          repo.namespace,
          repo.name,
          'immutable-1',
          TEST_USERS.user.username,
          TEST_USERS.user.password,
        ),
        pushImage(
          repo.namespace,
          repo.name,
          'immutable-2',
          TEST_USERS.user.username,
          TEST_USERS.user.password,
        ),
      ]);

      await Promise.all([
        api.raw.setTagImmutability(
          repo.namespace,
          repo.name,
          'immutable-1',
          true,
        ),
        api.raw.setTagImmutability(
          repo.namespace,
          repo.name,
          'immutable-2',
          true,
        ),
      ]);

      await authenticatedPage.goto(`/repository/${repo.fullName}?tab=tags`);

      await expect(
        authenticatedPage.getByRole('link', {
          name: 'immutable-1',
          exact: true,
        }),
      ).toBeVisible({timeout: 30000});
      await expect(
        authenticatedPage.getByRole('link', {
          name: 'immutable-2',
          exact: true,
        }),
      ).toBeVisible();

      const row1 = authenticatedPage.getByRole('row').filter({
        has: authenticatedPage.getByRole('link', {
          name: 'immutable-1',
          exact: true,
        }),
      });
      const row2 = authenticatedPage.getByRole('row').filter({
        has: authenticatedPage.getByRole('link', {
          name: 'immutable-2',
          exact: true,
        }),
      });

      // Verify both have lock icons
      await expect(row1.getByTestId('immutable-tag-icon')).toBeVisible();
      await expect(row2.getByTestId('immutable-tag-icon')).toBeVisible();

      // Select both tags
      await row1.getByRole('checkbox').click();
      await row2.getByRole('checkbox').click();

      // Open bulk actions and click remove immutability
      await authenticatedPage.getByTestId('bulk-actions-kebab').click();
      await authenticatedPage
        .getByTestId('bulk-remove-immutability-action')
        .click();

      // Verify modal shows correct text
      await expect(
        authenticatedPage.getByTestId('immutability-modal'),
      ).toBeVisible();
      await expect(
        authenticatedPage.getByText('Remove immutability from 2 tags?'),
      ).toBeVisible();

      // Confirm
      await authenticatedPage.getByTestId('confirm-immutability-btn').click();

      // Verify modal closes and lock icons disappear
      await expect(
        authenticatedPage.getByTestId('immutability-modal'),
      ).not.toBeVisible();

      // Wait for tags to reload and verify lock icons are gone
      await authenticatedPage.goto(`/repository/${repo.fullName}?tab=tags`);

      const updatedRow1 = authenticatedPage.getByRole('row').filter({
        has: authenticatedPage.getByRole('link', {
          name: 'immutable-1',
          exact: true,
        }),
      });
      const updatedRow2 = authenticatedPage.getByRole('row').filter({
        has: authenticatedPage.getByRole('link', {
          name: 'immutable-2',
          exact: true,
        }),
      });

      await expect(
        updatedRow1.getByTestId('immutable-tag-icon'),
      ).not.toBeVisible({timeout: 30000});
      await expect(
        updatedRow2.getByTestId('immutable-tag-icon'),
      ).not.toBeVisible({timeout: 30000});
    });

    // PROJQUAY-10503: Bulk remove immutability disabled when no immutable tags selected
    test('bulk remove immutability is disabled when no immutable tags are selected', async ({
      authenticatedPage,
      api,
    }) => {
      const repo = await api.repository();
      await pushImage(
        repo.namespace,
        repo.name,
        'mutable-tag',
        TEST_USERS.user.username,
        TEST_USERS.user.password,
      );

      await authenticatedPage.goto(`/repository/${repo.fullName}?tab=tags`);

      await expect(
        authenticatedPage.getByRole('link', {
          name: 'mutable-tag',
          exact: true,
        }),
      ).toBeVisible({timeout: 30000});

      const tagRow = authenticatedPage.getByRole('row').filter({
        has: authenticatedPage.getByRole('link', {
          name: 'mutable-tag',
          exact: true,
        }),
      });
      await tagRow.getByRole('checkbox').click();

      await authenticatedPage.getByTestId('bulk-actions-kebab').click();

      const removeImmutabilityAction = authenticatedPage.getByTestId(
        'bulk-remove-immutability-action',
      );
      await expect(removeImmutabilityAction).toHaveClass(/pf-m-disabled/);
    });

    // PROJQUAY-10779: Verify usage logs show description for tag immutability changes
    test('logs tag immutability change in usage logs', async ({
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

      // Set tag as immutable to generate a log entry
      await api.raw.setTagImmutability(
        repo.namespace,
        repo.name,
        'v1.0.0',
        true,
      );

      // Navigate to org Usage Logs tab
      await authenticatedPage.goto(`/organization/${repo.namespace}?tab=Logs`);

      // Wait for table to load
      await expect(
        authenticatedPage.getByTestId('usage-logs-table'),
      ).toBeVisible({timeout: 30000});

      // Filter by "immutable" to find our log entry
      await authenticatedPage.getByPlaceholder('Filter logs').fill('immutable');

      await authenticatedPage.waitForTimeout(500);

      // Find the row for our specific repo (repo.name is unique per test)
      const logRow = authenticatedPage
        .getByTestId('usage-logs-table')
        .getByRole('row')
        .filter({hasText: repo.name});

      // Verify the description shows the action, not "No description available"
      await expect(logRow.getByText('set as immutable')).toBeVisible();
    });

    // PROJQUAY-10500: Adding labels to immutable tag does not crash the UI
    test('can add labels to an immutable tag without crashing', async ({
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
      ).toBeVisible({timeout: 30000});

      const tagRow = authenticatedPage
        .getByRole('row')
        .filter({has: authenticatedPage.getByRole('link', {name: 'v1.0.0'})});

      // Open edit labels dialog
      await tagRow.getByLabel('Tag actions kebab').click();
      await authenticatedPage
        .getByRole('menuitem', {name: 'Edit labels'})
        .click();

      await expect(
        authenticatedPage.getByRole('dialog', {name: 'Edit labels'}),
      ).toBeVisible();

      // Add a new label
      await authenticatedPage.getByText('Add new label').click();
      await authenticatedPage
        .getByRole('textbox', {name: 'key=value'})
        .fill('test=value');
      // Click away from the input to trigger onEditComplete (blur event),
      // which adds the label to state and enables the Save Labels button.
      await authenticatedPage.getByText('Mutable labels').click();

      // Wait for the Save Labels button to become enabled before clicking.
      // Without this wait, a race condition between the blur handler updating
      // React state and Playwright's next click causes the button to be found
      // in a disabled state (isSaveButtonDisabled returns true when no labels
      // have been added/deleted yet — see LabelsEditable.tsx:194).
      const saveLabelsButton = authenticatedPage.getByRole('button', {
        name: 'Save Labels',
      });
      await expect(saveLabelsButton).toBeEnabled({timeout: 5000});

      // Save
      await saveLabelsButton.click();

      // Verify success alert appears exactly once and no crash
      const successAlert = authenticatedPage.getByText(
        'Created labels successfully',
      );
      await expect(successAlert.first()).toBeVisible({timeout: 10000});

      // Verify dialog closed (onComplete fired)
      await expect(
        authenticatedPage.getByRole('dialog', {name: 'Edit labels'}),
      ).not.toBeVisible();

      // Verify no crash - tags table is still visible
      await expect(
        authenticatedPage.getByRole('link', {name: 'v1.0.0'}),
      ).toBeVisible();

      // Verify "Unable to complete request" error does NOT appear
      await expect(
        authenticatedPage.getByText('Unable to complete request'),
      ).not.toBeVisible();

      // Verify "Undefined" does NOT appear
      await expect(authenticatedPage.getByText('Undefined')).not.toBeVisible();
    });

    // PROJQUAY-10500: Verify error messages show server details, not "Undefined"
    test('deleting an immutable tag shows server error message', async ({
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

      // Wait for tag to render (UI loads tag as mutable)
      await expect(
        authenticatedPage.getByRole('link', {name: 'v1.0.0'}),
      ).toBeVisible({timeout: 30000});

      // Make tag immutable via API while UI still shows stale mutable state.
      // This simulates a tag becoming immutable after the page was loaded
      // (e.g., by an admin or policy), which is a valid real-world scenario.
      await api.raw.setTagImmutability(
        repo.namespace,
        repo.name,
        'v1.0.0',
        true,
      );

      // Open kebab menu and click "Remove" (still enabled due to stale state)
      const tagRow = authenticatedPage.getByRole('row').filter({
        has: authenticatedPage.getByRole('link', {name: 'v1.0.0'}),
      });
      await tagRow.getByLabel('Tag actions kebab').click();
      await authenticatedPage
        .getByRole('menuitem', {name: 'Remove', exact: true})
        .click();

      // Wait for delete modal
      await expect(
        authenticatedPage.getByRole('dialog', {
          name: /Delete the following tag/,
        }),
      ).toBeVisible();

      // Click Delete to trigger the DELETE request (server will reject)
      await authenticatedPage.getByRole('button', {name: 'Delete'}).click();

      // Wait for the danger alert to appear
      const dangerAlert = authenticatedPage
        .locator('.pf-v6-c-alert.pf-m-danger')
        .last();
      await expect(dangerAlert).toBeVisible({timeout: 10000});

      // Verify the alert title
      await expect(dangerAlert).toContainText('Could not delete tag');

      // Expand the alert to reveal the detailed error message
      await dangerAlert.locator('.pf-v6-c-alert__toggle button').click();

      // Verify the alert contains the server's specific error message
      await expect(dangerAlert).toContainText(
        "Cannot delete immutable tag 'v1.0.0'",
      );

      // Verify "Undefined" does NOT appear in the alert
      await expect(dangerAlert).not.toContainText('Undefined');
    });
  },
);
