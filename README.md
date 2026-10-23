<p align="center">
  <img src="https://github.com/Apakottur/shpyx/blob/main/shpyx.png?raw=true" />
</p>

[![image](https://img.shields.io/pypi/v/shpyx.svg)](https://pypi.python.org/pypi/shpyx)
[![image](https://img.shields.io/pypi/l/shpyx.svg)](https://github.com/Apakottur/shpyx/blob/main/LICENSE)
[![image](https://img.shields.io/pypi/pyversions/shpyx.svg)](https://pypi.python.org/pypi/shpyx)
[![Documentation](https://readthedocs.org/projects/shpyx/badge/?version=latest)](https://shpyx.readthedocs.io/)

**shpyx** is a simple, lightweight and typed library for running shell commands in Python.

**Documentation**: [shpyx.readthedocs.io](https://shpyx.readthedocs.io/)

## Installation

Install with `uv` or `pip`:

```shell
uv add shpyx
pip install shpyx
```

## Quick start

Use `shpyx.run` to run a shell command in a subprocess:

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

Shell logic works when the command is a string, and a custom `Runner` sets defaults for every call:

```python
>>> shpyx.run("seq 1 5 | grep '2'").stdout
'2\n'
>>> runner = shpyx.Runner(log_cmd=True)
>>> runner.run("echo 1")
Running: echo 1
ShellCmdResult(cmd='echo 1', stdout='1\n', stderr='', all_output='1\n', return_code=0)
```

See the [documentation](https://shpyx.readthedocs.io/) for more guides, every option, and the full API reference.

## Contributing

Contributions are welcome!

See [CONTRIBUTING.md](CONTRIBUTING.md) for details.

## License

`shpyx` is distributed under the terms of the [MIT license](LICENSE).
