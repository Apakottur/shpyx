# shpyx

**shpyx** is a simple, lightweight and typed library for running shell commands in Python.

Use [`shpyx.run`](reference/api.md#shpyx.Runner.run) to run a shell command in a subprocess:

```python
>>> import shpyx
>>> shpyx.run("echo 1")
ShellCmdResult(cmd='echo 1', stdout='1\n', stderr='', all_output='1\n', return_code=0)
>>> shpyx.run("echo 1").return_code
0
>>> shpyx.run("echo 1").stdout
'1\n'
>>> shpyx.run("echo 1").stderr
''
```

shpyx supports Linux, macOS and Windows, on Python 3.11 and above.

## Installation

shpyx is available as [`shpyx`](https://pypi.org/project/shpyx/) on PyPI. Install it with `uv` (recommended) or
`pip`:

```shell
# With uv.
uv add shpyx

# With pip.
pip install shpyx
```

## Next steps

- [How-to guides](how-to.md): common tasks, like logging live output or using shell logic.
- [Configuration](configuration.md): every option of `Runner` and `run`.
- [How it works](how-it-works.md): implementation details and security considerations.
- [Python API](reference/api.md): the full API reference.
