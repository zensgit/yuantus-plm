from __future__ import annotations

import argparse
from typing import Any


class RedactingArgumentParser(argparse.ArgumentParser):
    """ArgumentParser variant that does not echo rejected argument values."""

    def error(self, message: str) -> None:
        self.print_usage()
        self.exit(2, "error: CLI parse failed\nargument value hidden: true\n")


def build_redacting_parser(*args: Any, **kwargs: Any) -> RedactingArgumentParser:
    return RedactingArgumentParser(*args, **kwargs)
