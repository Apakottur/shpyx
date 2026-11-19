# How-to guides

## Run a command

In string format:

```python
>>> shpyx.run("echo 1")
ShellCmdResult(cmd='echo 1', stdout='1\n', stderr='', all_output='1\n', return_code=0)
```

In list format:

```python
>>> shpyx.run(["echo", "1"])
ShellCmdResult(cmd='echo 1', stdout='1\n', stderr='', all_output='1\n', return_code=0)
```

!!! warning

    Never pass untrusted input to `run`, in either format. See [Security](how-it-works.md#security).

## Run a command and print live output

```python
>>> shpyx.run("echo 1", log_output=True)
1
ShellCmdResult(cmd='echo 1', stdout='1\n', stderr='', all_output='1\n', return_code=0)
```

## Run a command with shell specific logic

When the argument to `run` is a string, an actual shell is created in the subprocess and shell logic can be used.
For example, the pipe operator can be used in bash/sh:

```python
>>> shpyx.run("seq 1 5 | grep '2'")
ShellCmdResult(cmd="seq 1 5 | grep '2'", stdout='2\n', stderr='', all_output='2\n', return_code=0)
```

## Handle a failed command

By default, `run` raises [`ShpyxVerificationError`](reference/api.md#shpyx.ShpyxVerificationError) when the command
exits with a non-zero return code. The error holds the full result of the command:

```python
>>> try:
...     shpyx.run("exit 3")
... except shpyx.ShpyxVerificationError as e:
...     print(e.result.return_code)
3
```

To inspect the return code yourself instead, disable the verification:

```python
>>> shpyx.run("exit 3", verify_return_code=False).return_code
3
```

## Create a custom runner

Use a custom [`Runner`](reference/api.md#shpyx.Runner) to override the execution defaults, and not have to pass them to
every call.

For example, we can change the default value of `log_cmd`, so that all commands are logged:

```python
>>> shpyx.run("echo 1")
ShellCmdResult(cmd='echo 1', stdout='1\n', stderr='', all_output='1\n', return_code=0)

>>> shpyx.run("echo 1", log_cmd=True)
Running: echo 1
ShellCmdResult(cmd='echo 1', stdout='1\n', stderr='', all_output='1\n', return_code=0)

>>> runner = shpyx.Runner(log_cmd=True)
>>> runner.run("echo 1")
Running: echo 1
ShellCmdResult(cmd='echo 1', stdout='1\n', stderr='', all_output='1\n', return_code=0)
```

## Propagate terminal control sequences

!!! note

    This is only supported on Linux and macOS. On any other system (including Windows), `unix_raw=True` raises
    [`ShpyxOSNotSupportedError`](reference/api.md#shpyx.ShpyxOSNotSupportedError).

Some commands, like `psql`, might output special characters used for terminal management like cursor movement and
colors. For example, the `psql` command is used to start an interactive shell against a Postgres DB:

```python
shpyx.run(f"psql -h {host} -p {port} -U {user} -d {database}", log_output=True)
```

However, the above call will not work as well as running `psql` directly, due to terminal control sequences not being
properly propagated. To make it work well, we need to use the [script](https://man7.org/linux/man-pages/man1/script.1.html)
utility which will properly propagate all control sequences:

```python
# Linux:
shpyx.run(f"script -q -c 'psql -h {host} -p {port} -U {user} -d {database}'", log_output=True)
# MacOS:
shpyx.run(f"script -q /dev/null psql -h {host} -p {port} -U {user} -d {database}", log_output=True)
```

shpyx provides a keyword argument that does this wrapping automatically, `unix_raw`:

```python
shpyx.run(f"psql -h {host} -p {port} -U {user} -d {database}", log_output=True, unix_raw=True)
```

It also works with list arguments, which are shell-quoted and always run through a shell:

```python
shpyx.run(["psql", "-h", host, "-p", port, "-U", user, "-d", database], log_output=True, unix_raw=True)
```

The flag is disabled by default, and should only be used for interactive commands like `psql`.
