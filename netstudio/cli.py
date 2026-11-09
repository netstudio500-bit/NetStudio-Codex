"""CLI entry point for NetStudio-Codex."""

import sys

from netstudio.main import cli as main_cli


def main() -> None:
    """Main entry point for the CLI."""
    try:
        main_cli()
    except KeyboardInterrupt:
        sys.exit(0)
    except Exception as exc:
        print(f"Error: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
