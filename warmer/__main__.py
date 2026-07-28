"""CLI entrypoint: python -m warmer <warm|status|test-notify>."""

from __future__ import annotations

import argparse
import sys

from . import __version__, core
from .config import ConfigError


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="warmer",
        description="Warm Claude / Codex CLI usage windows on a schedule.",
    )
    parser.add_argument("--version", action="version", version=f"session-warmer {__version__}")
    parser.add_argument("--config", default=None, help="path to config.json")
    sub = parser.add_subparsers(dest="command", required=True)

    warm = sub.add_parser("warm", help="ping one provider to open/refresh its window")
    warm.add_argument("--provider", required=True, help="provider name (e.g. claude, codex)")

    sub.add_parser("status", help="print current warming state")
    sub.add_parser("test-notify", help="send a test email via Resend")

    args = parser.parse_args(argv)

    try:
        if args.command == "warm":
            return core.warm(args.provider, args.config)
        if args.command == "status":
            return core.status(args.config)
        if args.command == "test-notify":
            return core.test_notify(args.config)
    except ConfigError as exc:
        print(f"[warmer] config error: {exc}", file=sys.stderr)
        return 2
    return 1


if __name__ == "__main__":
    sys.exit(main())
