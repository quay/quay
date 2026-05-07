import {test, expect} from '../../fixtures';
import {API_URL} from '../../utils/config';

test.describe(
  'Repository State Management',
  {tag: ['@repository', '@feature:REPO_MIRROR']},
  () => {
    test('transitions from NORMAL to READ_ONLY and back via settings UI', async ({
      authenticatedPage,
      authenticatedRequest,
      api,
    }) => {
      const org = await api.organization('stateorg');
      const repo = await api.repository(org.name, 'staterepo');

      // Navigate to repo settings > Repository state tab
      await authenticatedPage.goto(
        `/repository/${org.name}/${repo.name}?tab=settings`,
      );
      await authenticatedPage
        .getByTestId('settings-tab-repositorystate')
        .click();

      // Verify Normal is selected by default
      const normalRadio = authenticatedPage.getByRole('radio', {
        name: 'Normal',
      });
      await expect(normalRadio).toBeChecked();

      // Submit should be disabled when current state is selected
      const submitButton = authenticatedPage.getByRole('button', {
        name: 'Submit',
      });
      await expect(submitButton).toBeDisabled();

      // Select Read Only
      await authenticatedPage.getByRole('radio', {name: 'Read Only'}).click();

      // Warning should appear
      await expect(
        authenticatedPage.getByText(
          'WARNING: This will prevent all pushes to the repository.',
        ),
      ).toBeVisible();

      await expect(submitButton).toBeEnabled();
      await submitButton.click();

      // Verify state changed via API (poll to avoid racing the async update)
      await expect
        .poll(
          async () => {
            const response = await authenticatedRequest.get(
              `${API_URL}/api/v1/repository/${org.name}/${repo.name}`,
            );
            if (!response.ok()) return `HTTP_${response.status()}`;
            const body = await response.json();
            return body.state;
          },
          {timeout: 10_000},
        )
        .toBe('READ_ONLY');

      // Transition back to NORMAL
      await authenticatedPage.reload();
      await authenticatedPage
        .getByTestId('settings-tab-repositorystate')
        .click();

      await expect(
        authenticatedPage.getByRole('radio', {name: 'Read Only'}),
      ).toBeChecked();

      await authenticatedPage.getByRole('radio', {name: 'Normal'}).click();
      await authenticatedPage.getByRole('button', {name: 'Submit'}).click();

      // Verify restored via API
      await expect
        .poll(
          async () => {
            const response = await authenticatedRequest.get(
              `${API_URL}/api/v1/repository/${org.name}/${repo.name}`,
            );
            if (!response.ok()) return `HTTP_${response.status()}`;
            const body = await response.json();
            return body.state;
          },
          {timeout: 10_000},
        )
        .toBe('NORMAL');
    });

    test('transitions to MIRROR state via settings UI', async ({
      authenticatedPage,
      authenticatedRequest,
      api,
    }) => {
      const org = await api.organization('mirrstateorg');
      const repo = await api.repository(org.name, 'mirrstaterepo');

      await authenticatedPage.goto(
        `/repository/${org.name}/${repo.name}?tab=settings`,
      );
      await authenticatedPage
        .getByTestId('settings-tab-repositorystate')
        .click();

      // Select Mirror
      await authenticatedPage.getByRole('radio', {name: 'Mirror'}).click();
      await authenticatedPage.getByRole('button', {name: 'Submit'}).click();

      // Verify state changed via API (poll to avoid racing the async update)
      await expect
        .poll(
          async () => {
            const response = await authenticatedRequest.get(
              `${API_URL}/api/v1/repository/${org.name}/${repo.name}`,
            );
            if (!response.ok()) return `HTTP_${response.status()}`;
            const body = await response.json();
            return body.state;
          },
          {timeout: 10_000},
        )
        .toBe('MIRROR');
    });

    test('reflects MIRROR state set via API in settings UI', async ({
      authenticatedPage,
      api,
    }) => {
      const org = await api.organization('orgmirrstate');
      const repo = await api.repository(org.name, 'orgmirrrepo');

      // Set to MIRROR state via API
      await api.raw.changeRepositoryState(org.name, repo.name, 'MIRROR');

      await authenticatedPage.goto(
        `/repository/${org.name}/${repo.name}?tab=settings`,
      );

      await authenticatedPage
        .getByTestId('settings-tab-repositorystate')
        .click();

      // Verify Mirror radio is checked
      await expect(
        authenticatedPage.getByRole('radio', {name: 'Mirror'}),
      ).toBeChecked();
    });
  },
);
