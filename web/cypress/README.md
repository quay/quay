# E2E Testing

## Why e2e test?

End to end tests ensure the application pages and components work properly together from an end user perspective. We use Cypress as the e2e testing framework, where we provide a URL of the running application and it will arrange, act, and assert on the application behavior.

## How to e2e test?

### Directory structure

- `e2e`: Contains test files, each corresponding to a page in the application
- `fixtures`: Mock JSON network responses consumed by Cypress
- `support`: Additional Cypress configurations eg. Adding commands
- `test`: Seed data for the test instance of Quay

### Testing strategy

Tests are divided into two scenarios: using server or stubbed responses. Requests that reach out directly to a Quay instance are called server responses while requests that are mocked are called stubbed responses. A full comparison between the two can be found [here](https://docs.cypress.io/guides/guides/network-requests#Testing-Strategies) but it can be summarized as follows:

Server responses

- More likely to work in production
- Requires seeding the Quay instance
- Much slower
- Difficult to test edge cases
- Use sparringly

Stubbed responses

- Control of responses to test edge cases
- Fast
- No guarantee stubbed responses match the real responses
- Use for majority of tests

The recommended practice is to mix and match server and stubbed responses. A single spec will have server responses testing the critical paths of the application and then stubbed the rest.

## Updating the Quay seed data

Both the database and blob data must be stored to seed the Quay instance. This data is stored in the `/cypress/test` directory. Running `npm run quay:seed` will seed the local instance of Quay with the test data.

To make changes to the test data:

- Have a local instance of Quay running via `docker-compose` (`make local-dev-up`)
- Run `npm run quay:seed` to populate the instance with the test data
- Make required changes to the Quay instance
- Run `npm run quay:dump` to update the `/cypress/test` directory with the test data
  > :warning: Ensure no confidential information is within the test instance when dumping the test data
