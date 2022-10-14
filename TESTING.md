# Testing

## Manual Testing

Tests are located in the `test/` folder. You can run them with:

```bash
pytest
```

On your local machine, these tests will run using the `STEAMSHIP_API_KEY` environment variable, if available, or using the key specified in your user-global Steamship settings (`~/.steamship.json`).

## Automated testing

This repository is configured to auto-test upon pull-requests to the `main` and `staging` branches. Testing will also be performed as part of the automated deployment (see `DEPLOYING.md`)

* Failing tests are will block any automated deployments
* We recommend configuring your repository to block pull-request merges unless a passing test has been registered

### Automated testing setup

Unit tests will run for each pull request against `main` and every repository push.

Integration tests will run after a PR approval has been registered. The tests will run against the staging
instance of Steamship. This requires that a version matching the version in `steamship.json`
be deployed to the staging environment.

PRs should not be merged without passing unit tests, PR approvals, and passing integration tests.

### Configuring or removing automated testing

Automated tests are run from the GitHub workflow located in `.github/workflows/test.yml`
    