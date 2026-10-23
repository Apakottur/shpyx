# Contributing to shpyx

Thanks for your interest in contributing! To contribute, open a pull request with your changes, or an
issue with your bug or request.

All checks (linters, type checks, and tests) run automatically in CI through GitHub Actions.

## Development environment

Local development is done with [uv](https://docs.astral.sh/uv/getting-started/installation/).

Install all the development dependencies:

```shell
uv sync
```

## Running checks locally

Run the linters with `prek`:

```shell
prek run -a
```

Run the unit tests with `pytest`:

```shell
pytest -c tests/pytest.ini tests
```

Run the type checks with `mypy` and `ty` (both run in CI):

```shell
mypy --config-file linters/mypy.toml src tests
ty check --config-file linters/ty.toml src tests
```

## Documentation

The documentation site lives in `docs/`, is built with [Zensical](https://zensical.org/), and is hosted on
[Read the Docs](https://shpyx.readthedocs.io/). The Python API reference is generated from the docstrings.

Preview it locally with live reload:

```shell
uv run --group docs zensical serve
```

Build it the way CI does (warnings, such as broken links, fail the build):

```shell
uv run --group docs zensical build --strict
```

## Releasing

To release a new version, run the interactive script:

```shell
./scripts/release.py
```
