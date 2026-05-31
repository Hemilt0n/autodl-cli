from __future__ import annotations

import argparse


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="autodl",
        description="AutoDL Pro command-line tool.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version="autodl-cli 0.1.0",
    )
    return parser


def main() -> None:
    parser = build_parser()
    parser.parse_args()
