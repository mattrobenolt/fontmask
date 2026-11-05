# Publishing

`fontmask` publishes from GitHub Actions with PyPI Trusted Publishing. No PyPI
token is stored in the repository.

## GitHub environments

Create two environments in the repository settings:

- `pypi`
- `testpypi`

Add required reviewers to `pypi` if you want a manual gate before a release.

## PyPI pending publisher

Open <https://pypi.org/manage/account/publishing/> and add a pending publisher:

- PyPI project name: `fontmask`
- Owner: `mattrobenolt`
- Repository: `fontmask`
- Workflow: `publish.yml`
- Environment: `pypi`

The first tagged release creates the project.

## TestPyPI pending publisher

Open <https://test.pypi.org/manage/account/publishing/> and add a pending
publisher:

- PyPI project name: `fontmask`
- Owner: `mattrobenolt`
- Repository: `fontmask`
- Workflow: `publish-testpypi.yml`
- Environment: `testpypi`

Run the `publish-testpypi` workflow from the Actions tab. Test the result with:

```sh
uvx --default-index https://test.pypi.org/simple/ \
  --index https://pypi.org/simple/ \
  --from fontmask fontmask --version
```

## Release

1. Set the version in `pyproject.toml`.
2. Commit and push the change.
3. Tag the commit and push the tag:

```sh
git tag -a v0.1.0 -m "fontmask 0.1.0"
git push origin v0.1.0
```

The `publish` workflow builds the sdist and wheel, runs the wheel and sdist
smoke tests, publishes to PyPI with OIDC, and creates a GitHub release with the
distributions attached.
