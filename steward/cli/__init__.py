"""Unified CLI entry point for steward.

Every handler raises :class:`steward.cli._errors.StewardError` on failure;
``main()`` catches it via :func:`_dispatch` and routes through
:mod:`steward.cli._output`. Argparse errors route through
``_StewardArgumentParser`` so they share the same structured output.
"""

from __future__ import annotations

import argparse
import sys

from steward import __version__
from steward.cli._errors import EXIT_USER_ERROR, StewardError
from steward.cli._output import emit_error


class _StewardArgumentParser(argparse.ArgumentParser):
    """ArgumentParser that routes errors through :func:`emit_error`."""

    def error(self, message: str) -> None:  # type: ignore[override]
        err = StewardError(
            code=EXIT_USER_ERROR,
            message=message,
            remediation=f"run '{self.prog} --help' to see valid arguments",
        )
        emit_error(err)
        raise SystemExit(err.code)


def _build_parser() -> argparse.ArgumentParser:
    # Deferred import to avoid coupling the parser module to the command modules
    # at import time (matches afi-cli's pattern; cheap insurance).
    from steward.cli._commands import show as _show_cmd
    from steward.cli._commands import verify as _verify_cmd

    parser = _StewardArgumentParser(
        prog="steward",
        description="steward — align and maintain resident agents across Culture projects",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    sub = parser.add_subparsers(dest="command", parser_class=_StewardArgumentParser)

    _show_cmd.register(sub)
    _verify_cmd.register(sub)

    return parser


def _dispatch(args: argparse.Namespace) -> int:
    try:
        rc = args.func(args)
    except StewardError as err:
        emit_error(err)
        return err.code
    except Exception as err:  # noqa: BLE001 - last-resort: wrap so no traceback leaks
        wrapped = StewardError(
            code=EXIT_USER_ERROR,
            message=f"unexpected: {err.__class__.__name__}: {err}",
            remediation="file a bug at https://github.com/agentculture/steward/issues",
        )
        emit_error(wrapped)
        return wrapped.code
    return rc if rc is not None else 0


def main(argv: list[str] | None = None) -> int:
    parser = _build_parser()
    args = parser.parse_args(argv)

    if args.command is None:
        parser.print_help()
        return 0

    return _dispatch(args)


if __name__ == "__main__":
    sys.exit(main())
