import {request} from '@playwright/test';
import billingLocalSetup from './billing-local-setup';
import {TEST_USERS} from './global-setup';
import {ApiClient} from './utils/api';

// This regression profile uses only the standard regular-user fixtures.
export default async function organizationBillingSetup() {
  await billingLocalSetup();
  const context = await request.newContext();
  const client = new ApiClient(context);
  const user = TEST_USERS.user;
  try {
    try {
      await client.createUser(user.username, user.password, user.email);
    } catch (error) {
      if (!/already exists|already taken/.test(String(error))) throw error;
    }
    await client.signIn(user.username, user.password);
    await client.clearUserPrompts();
  } finally {
    await context.dispose();
  }
}
