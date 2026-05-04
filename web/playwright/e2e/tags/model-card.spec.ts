import {test, expect} from '../../fixtures';

test.describe(
  'Model Card Tab',
  {tag: ['@tags', '@feature:UI_MODELCARD', '@container']},
  () => {
    test('model card tab hidden when no modelcard data exists', async ({
      authenticatedPage,
      api,
    }) => {
      const org = await api.organization('mcnodata');
      const repo = await api.repository(org.name, 'nomc-repo');

      await authenticatedPage.goto(`/repository/${org.name}/${repo.name}`);

      // Model Card tab should not be visible for repos without model card data
      await expect(
        authenticatedPage.getByRole('tab', {name: /Model Card/i}),
      ).not.toBeVisible();
    });
  },
);
