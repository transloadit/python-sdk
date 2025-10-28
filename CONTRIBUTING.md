# Contributing

## HOWTO Release

This is a Howto guide on the commands to run and files to update in order to publish a new release of the Python SDK to Pypi

### Prerequisite

Poetry will handle things for us. You need to configure poetry with your pypi token for the publishing process to work.

Enable testing publishing on pypi test index.

```bash
poetry config repositories.test-pypi https://test.pypi.org/legacy/
poetry config pypi-token.test-pypi pypi-XXXXX
```

To setup your token to publish to pypi.

```bash
poetry config pypi-token.pypi pypi-XXXXX`````
```

### Release Steps

1. Update the changelog, the version file, and the test file as done in [this commit](https://github.com/transloadit/python-sdk/commit/35789c535bd02086ff8f3a07eda9583d6e676d4d) and push it to main.
2. Update the version
```bash
# e.g: 0.2.2 -> 0.2.3a0
poetry version prerelease
# or the following for, e.g.: 0.2.3
poetry version patch
```
3. Publish to Pypi

Pypi test index

```bash
poetry build
poetry publish -r test-pypi
```

To publish to pypi
```bash
poetry publish
```

4. Now that release has been published on Pypi, please head to GitHub to [draft a new tag release](https://github.com/transloadit/python-sdk/releases). Point this tag release to the latest commit pushed on step 1 above. Once you're done drafting the release, go ahead to publish it.

If all the steps above have been followed without errors, then you've successfully published a release. 🎉

---

Further reading for Transloadians: https://github.com/transloadit/team-internals/blob/HEAD/_howtos/2020-12-14-maintain-python-sdk.md
