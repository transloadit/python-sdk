## HOWTO Release

This is a Howto guide on the commands to run and files to update in order to publish a new release of the Python SDK to Pypi

### Prerequisite

You need to have `twine`, `pypandoc`, and `pandoc` installed.

```bash
pip install twine
pip install pypandoc
```

To Install `pandoc` please [see](https://pandoc.org/installing.html).

Pypandoc and Pandoc are needed to convert the readme from markdown to rst for the package's documentation page on [Pypi](https://pypi.org/project/pytransloadit/).

### Release Steps

1. Update the changelog, the version file, and the test file as done in [this commit](https://github.com/transloadit/python-sdk/commit/35789c535bd02086ff8f3a07eda9583d6e676d4d) and push it to main.
2. Publish to Pypi by running the following commands.

```bash
python setup.py sdist bdist_wheel
twine check dist/*
twine upload dist/*
```

The second command above (`twine check dist/*`) is meant to check for errors in the dist build, so please abort and try to fix issues if you see any errors from running the command.

Running the third command from above will prompt you for your [Pypi](https://pypi.org/project/pytransloadit/) username and password.

3. Now that release has been published on Pypi, please head to GitHub to [draft a new tag release](https://github.com/transloadit/python-sdk/releases). Point this tag release to the latest commit pushed on step 1 above. Once you're done drafting the release, go ahead to publish it.

If all the steps above have been followed without errors, then you've successfully published a relaease. 🎉

---

Further reading for Transloadians: https://github.com/transloadit/team-internals/blob/HEAD/_howtos/2020-12-14-maintain-python-sdk.md
