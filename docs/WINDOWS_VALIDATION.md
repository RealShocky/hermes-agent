# Windows Validation

Hermes is validated on the primary Windows development host with the
repository-managed `venv311` environment. Do not use an unrelated global
Python installation for the full suite; it may omit declared core or
messaging dependencies.

## Prepare the environment

From `hermes-core-leonor-next`:

```powershell
uv pip install --python venv311\Scripts\python.exe -e ".[dev,messaging,web]"
```

The install is platform-aware. POSIX-only dependencies and tests remain
excluded on Windows, while the native Windows process, locking, path, and
encoding paths remain testable.

## Validation commands

Focused Windows compatibility gate:

```powershell
venv311\Scripts\python.exe -m pytest `
  tests\hermes_cli\test_doctor_journal_modes.py `
  tests\tools\test_bot_turn_lock.py `
  tests\tools\test_search_hidden_dirs.py `
  tests\gateway\test_telegram_rich_messages.py -q
```

The expected result is green tests plus explicit skips for POSIX-only flock
and `find` command tests. Full collection can be checked with:

```powershell
venv311\Scripts\python.exe -m pytest --collect-only -q
```

The unbounded full suite is large and can exceed a ten-minute local command
window. A timeout is not a passing result; use the focused gate and the
repository's CI runner for completion evidence.

## Portability rules

- Guard `os.geteuid`, `fcntl`, and POSIX commands at collection time.
- Use `shutil.which` rather than invoking Unix `which` from tests.
- Keep production locking on the native Windows `msvcrt`/portalocker paths;
  POSIX flock tests must be skipped on Windows, not faked.
- Test Windows error text by semantic alternatives, because Win32 and POSIX
  format missing-file errors differently.
