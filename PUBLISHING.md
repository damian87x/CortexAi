# Publishing CortexAi to PyPI

This guide explains how to build, test, and publish the CortexAi package to PyPI.

## Prerequisites

Ensure you have the following tools installed:

```bash
pip install --upgrade pip
pip install build twine
```

## Building the Package

1. Build the package:

```bash
python -m build
```

This will create distribution packages in the `dist/` directory:
- A source archive (.tar.gz)
- A wheel (.whl)

## Testing Locally

Before publishing, test the package locally:

```bash
# Create a virtual environment
python -m venv test_env
source test_env/bin/activate  # On Windows: test_env\Scripts\activate

# Install from the local build
pip install dist/CortexAi-0.1.0-py3-none-any.whl  # Update version as necessary

# Test import and basic functionality
python -c "from CortexAi.agent.core.base_agent import BaseAgent; print('Import successful')"

# Deactivate virtual environment when done
deactivate
```

## Publishing to TestPyPI (Recommended)

Test your package on TestPyPI before publishing to the real PyPI:

1. Register on [TestPyPI](https://test.pypi.org/account/register/).

2. Upload to TestPyPI:

```bash
python -m twine upload --repository testpypi dist/*
```

3. Install from TestPyPI to verify:

```bash
pip install --index-url https://test.pypi.org/simple/ --extra-index-url https://pypi.org/simple/ CortexAi
```

## Publishing to PyPI

Once tested on TestPyPI, publish to the real PyPI:

1. Register on [PyPI](https://pypi.org/account/register/) if you haven't already.

2. Upload to PyPI:

```bash
python -m twine upload dist/*
```

3. Install your package:

```bash
pip install CortexAi
```

## Updating the Package

To update the package:

1. Update the version in `CortexAi/__init__.py`.
2. Make your changes to the codebase.
3. Follow the build and upload steps again.

## GitHub Releases

Consider creating a GitHub release with release notes each time you publish a new version. Tag your releases with the version number to make it easier for users to track changes.

## Automating with GitHub Actions

For a more streamlined workflow, consider setting up GitHub Actions to automatically build and publish your package when you create a new release or tag. Here's a basic workflow file to start with:

Create `.github/workflows/publish.yml`:

```yaml
name: Publish to PyPI

on:
  release:
    types: [created]

jobs:
  deploy:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v2
    - name: Set up Python
      uses: actions/setup-python@v2
      with:
        python-version: '3.8'
    - name: Install dependencies
      run: |
        python -m pip install --upgrade pip
        pip install build twine
    - name: Build and publish
      env:
        TWINE_USERNAME: ${{ secrets.PYPI_USERNAME }}
        TWINE_PASSWORD: ${{ secrets.PYPI_PASSWORD }}
      run: |
        python -m build
        twine upload dist/*
