import {test, expect} from '../../fixtures';
import {TEST_USERS} from '../../global-setup';
import {ApiClient} from '../../utils/api';
import {API_URL} from '../../utils/config';
import {pushImage, pushUniqueImage} from '../../utils/container';

/**
 * Creates a Cosign tag-schema `.sig` tag for an image tag
 * (`sha256-<hex>.sig` pointing at the image digest).
 */
async function createCosignSigTag(
  api: ApiClient,
  namespace: string,
  repo: string,
  imageTag: string,
): Promise<string> {
  const tags = await api.getTags(namespace, repo, {specificTag: imageTag});
  if (tags.tags.length === 0) {
    throw new Error(`Tag ${imageTag} not found in ${namespace}/${repo}`);
  }
  const digest = tags.tags[0].manifest_digest;
  const sigName = `${digest.replace(':', '-')}.sig`;
  await api.createTag(namespace, repo, sigName, digest);
  return sigName;
}

test.describe('Repository Delete', {tag: ['@repository']}, () => {
  test('deletes repository via settings page and verifies removal', async ({
    authenticatedPage,
    authenticatedRequest,
    api,
  }) => {
    // Create test repository - will be auto-cleaned if test fails
    const repo = await api.repository(undefined, 'delrepo');

    // Navigate to repository settings
    await authenticatedPage.goto(
      `/repository/${repo.namespace}/${repo.name}?tab=settings`,
    );

    // Click on "Delete Repository" tab in settings sidebar
    await authenticatedPage
      .getByTestId('settings-tab-deleterepository')
      .click();

    // Verify warning message is displayed
    await expect(
      authenticatedPage.getByText(
        'Deleting a repository cannot be undone. Here be dragons!',
      ),
    ).toBeVisible();

    // Click the delete button to open confirmation modal
    await authenticatedPage.getByTestId('delete-repository-btn').click();

    // Verify confirmation modal appears
    await expect(
      authenticatedPage.getByText('Delete Repository?'),
    ).toBeVisible();
    await expect(
      authenticatedPage.getByText(
        `You are requesting to delete the repository ${repo.fullName}`,
      ),
    ).toBeVisible();
    await expect(
      authenticatedPage.getByText(
        `You must type ${repo.fullName} below to confirm deletion:`,
      ),
    ).toBeVisible();

    // Type confirmation text
    await authenticatedPage
      .getByTestId('delete-repository-confirm-input')
      .fill(repo.fullName);

    // Click Delete button in modal
    await authenticatedPage
      .getByTestId('delete-repository-confirm-btn')
      .click();

    // Verify redirect to repository list
    await expect(authenticatedPage).toHaveURL('/repository');

    // Verify repository no longer appears in the list
    // Wait for page to load
    await authenticatedPage.waitForLoadState('networkidle');

    // The deleted repository should not be visible
    await expect(authenticatedPage.getByText(repo.name)).not.toBeVisible();

    // Verify via API that repository is actually deleted
    const verifyResponse = await authenticatedRequest.get(
      `${API_URL}/api/v1/repository/${repo.fullName}`,
    );
    expect(verifyResponse.status()).toBe(404);
  });

  test('cancel button closes modal without deleting', async ({
    authenticatedPage,
    authenticatedRequest,
    api,
  }) => {
    // Create test repository - will be auto-cleaned after test
    const repo = await api.repository(undefined, 'delrepo');

    // Navigate to repository settings
    await authenticatedPage.goto(
      `/repository/${repo.namespace}/${repo.name}?tab=settings`,
    );

    // Open delete section in sidebar
    await authenticatedPage
      .getByTestId('settings-tab-deleterepository')
      .click();

    // Click delete button
    await authenticatedPage.getByTestId('delete-repository-btn').click();

    // Verify modal is open
    await expect(
      authenticatedPage.getByText('Delete Repository?'),
    ).toBeVisible();

    // Click Cancel button
    await authenticatedPage.getByTestId('delete-repository-cancel-btn').click();

    // Verify modal is closed
    await expect(
      authenticatedPage.getByText('Delete Repository?'),
    ).not.toBeVisible();

    // Verify repository still exists via API
    const verifyResponse = await authenticatedRequest.get(
      `${API_URL}/api/v1/repository/${repo.fullName}`,
      {timeout: 5000},
    );
    expect(verifyResponse.ok()).toBe(true);
  });

  test('delete button disabled without confirmation text', async ({
    authenticatedPage,
    api,
  }) => {
    // Create test repository - will be auto-cleaned after test
    const repo = await api.repository(undefined, 'delrepo');

    // Navigate to repository settings
    await authenticatedPage.goto(
      `/repository/${repo.namespace}/${repo.name}?tab=settings`,
    );

    // Open delete section in sidebar and modal
    await authenticatedPage
      .getByTestId('settings-tab-deleterepository')
      .click();
    await authenticatedPage.getByTestId('delete-repository-btn').click();

    // Verify modal is open
    await expect(
      authenticatedPage.getByText('Delete Repository?'),
    ).toBeVisible();

    // Delete button should be disabled initially
    const deleteButton = authenticatedPage.getByTestId(
      'delete-repository-confirm-btn',
    );
    await expect(deleteButton).toBeDisabled();

    // Type partial/wrong confirmation
    await authenticatedPage
      .getByTestId('delete-repository-confirm-input')
      .fill('wrong-text');

    // Button should still be disabled
    await expect(deleteButton).toBeDisabled();

    // Type correct confirmation
    await authenticatedPage
      .getByTestId('delete-repository-confirm-input')
      .fill(repo.fullName);

    // Button should now be enabled
    await expect(deleteButton).toBeEnabled();
  });
});

test.describe(
  'Cosign tag cascade on delete and retarget',
  {tag: ['@repository', '@container']},
  () => {
    const user = TEST_USERS.user;

    test(
      'deleting subject image tag cascades to cosign .sig tag',
      {tag: '@PROJQUAY-11682'},
      async ({api}) => {
        const org = await api.organization('prunesigdel');
        const repo = await api.repository(org.name, 'prunetest');

        await pushImage(
          org.name,
          repo.name,
          'v1',
          user.username,
          user.password,
        );
        const sigName = await createCosignSigTag(
          api.raw,
          org.name,
          repo.name,
          'v1',
        );

        const tagsBefore = await api.raw.getTags(org.name, repo.name);
        expect(tagsBefore.tags.map((t) => t.name)).toEqual(
          expect.arrayContaining(['v1', sigName]),
        );

        await api.raw.deleteTag(org.name, repo.name, 'v1');

        const tagsAfter = await api.raw.getTags(org.name, repo.name);
        const names = tagsAfter.tags.map((t) => t.name);
        expect(names).not.toContain('v1');
        expect(names).not.toContain(sigName);
      },
    );

    test(
      'deleting one alias keeps cosign .sig while another alias remains',
      {tag: '@PROJQUAY-11682'},
      async ({api}) => {
        const org = await api.organization('prunesigalias');
        const repo = await api.repository(org.name, 'prunetest');

        await pushUniqueImage(
          org.name,
          repo.name,
          'v1',
          user.username,
          user.password,
        );
        const v1Tags = await api.raw.getTags(org.name, repo.name, {
          specificTag: 'v1',
        });
        const digest = v1Tags.tags[0].manifest_digest;
        await api.raw.createTag(org.name, repo.name, 'latest', digest);

        const sigName = await createCosignSigTag(
          api.raw,
          org.name,
          repo.name,
          'v1',
        );

        await api.raw.deleteTag(org.name, repo.name, 'v1');

        let tags = await api.raw.getTags(org.name, repo.name);
        let names = tags.tags.map((t) => t.name);
        expect(names).toContain('latest');
        expect(names).toContain(sigName);
        expect(names).not.toContain('v1');

        await api.raw.deleteTag(org.name, repo.name, 'latest');

        tags = await api.raw.getTags(org.name, repo.name);
        names = tags.tags.map((t) => t.name);
        expect(names).not.toContain('latest');
        expect(names).not.toContain(sigName);
      },
    );

    test(
      'retargeting last alias cascades cosign .sig for displaced digest',
      {tag: '@PROJQUAY-11682'},
      async ({api}) => {
        const org = await api.organization('prunesigretarget');
        const repo = await api.repository(org.name, 'prunetest');

        await pushUniqueImage(
          org.name,
          repo.name,
          'v1',
          user.username,
          user.password,
        );
        const sigName = await createCosignSigTag(
          api.raw,
          org.name,
          repo.name,
          'v1',
        );

        await pushUniqueImage(
          org.name,
          repo.name,
          'v2',
          user.username,
          user.password,
        );
        const v2Tags = await api.raw.getTags(org.name, repo.name, {
          specificTag: 'v2',
        });
        const newDigest = v2Tags.tags[0].manifest_digest;

        // Retarget v1 onto v2's digest (displaces the old subject)
        await api.raw.createTag(org.name, repo.name, 'v1', newDigest);

        const tags = await api.raw.getTags(org.name, repo.name);
        const names = tags.tags.map((t) => t.name);
        expect(names).toContain('v1');
        expect(names).toContain('v2');
        expect(names).not.toContain(sigName);

        const v1After = await api.raw.getTags(org.name, repo.name, {
          specificTag: 'v1',
        });
        expect(v1After.tags[0].manifest_digest).toBe(newDigest);
      },
    );

    test(
      'retargeting one alias keeps cosign .sig while another alias remains',
      {tag: '@PROJQUAY-11682'},
      async ({api}) => {
        const org = await api.organization('prunesigretkeep');
        const repo = await api.repository(org.name, 'prunetest');

        await pushUniqueImage(
          org.name,
          repo.name,
          'v1',
          user.username,
          user.password,
        );
        const v1Tags = await api.raw.getTags(org.name, repo.name, {
          specificTag: 'v1',
        });
        const oldDigest = v1Tags.tags[0].manifest_digest;
        await api.raw.createTag(org.name, repo.name, 'latest', oldDigest);

        const sigName = await createCosignSigTag(
          api.raw,
          org.name,
          repo.name,
          'v1',
        );

        await pushUniqueImage(
          org.name,
          repo.name,
          'v2',
          user.username,
          user.password,
        );
        const v2Tags = await api.raw.getTags(org.name, repo.name, {
          specificTag: 'v2',
        });
        const newDigest = v2Tags.tags[0].manifest_digest;

        // Retarget only v1; latest still references oldDigest
        await api.raw.createTag(org.name, repo.name, 'v1', newDigest);

        const tags = await api.raw.getTags(org.name, repo.name);
        const names = tags.tags.map((t) => t.name);
        expect(names).toContain('v1');
        expect(names).toContain('latest');
        expect(names).toContain(sigName);

        const latestTags = await api.raw.getTags(org.name, repo.name, {
          specificTag: 'latest',
        });
        expect(latestTags.tags[0].manifest_digest).toBe(oldDigest);
      },
    );
  },
);
