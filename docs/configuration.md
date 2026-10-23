# Configuration

shpyx has no configuration file — everything is passed as arguments, either to a [`Runner`](reference/api.md#shpyx.Runner)
(as defaults for all of its commands) or to a single [`run`](reference/api.md#shpyx.Runner.run) call. `shpyx.run` uses a
`Runner` with the default configuration.

## Runner defaults

The following arguments are supported by both `Runner` and `run`. Passing one to `run` overrides the `Runner` default
for that call only.

| Name                 | Description                                                                | Default |
| -------------------- | -------------------------------------------------------------------------- | ------- |
| `log_cmd`            | Log the executed command.                                                  | `False` |
| `log_output`         | Log the live output of the command (while it is being executed).           | `False` |
| `verify_return_code` | Raise an exception if the shell return code of the command is not `0`.     | `True`  |
| `verify_stderr`      | Raise an exception if anything was written to stderr during the execution. | `False` |
| `use_signal_names`   | Log the name of the signal that killed the command, if any.                | `True`  |
| `decoder_factory`    | Factory of the incremental decoder used to decode the output.              | `UTF-8` |

## Per-command options

The following arguments are supported by `run` only:

| Name       | Description                                                            | Default                  |
| ---------- | ---------------------------------------------------------------------- | ------------------------ |
| `env`      | Environment variables to set during the execution of the command.      | `Same as parent process` |
| `exec_dir` | Custom path to execute the command in (defaults to current directory). | `Same as parent process` |
| `unix_raw` | (Linux/macOS only) Use the `script` Unix utility to run the command.   | `False`                  |
