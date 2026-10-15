"""Command-line entry point: `dbi-translate patch|build-table`."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .patch import PatchError, patch_nro
from .table import build_from_csv
from .versions import VERSIONS


def _patch(args) -> int:
    v = VERSIONS.get(args.version)
    if v is None:
        print(f"unknown version {args.version!r}; known: {', '.join(VERSIONS)}", file=sys.stderr)
        return 2
    try:
        out, report = patch_nro(v, Path(args.nro).read_bytes())
    except PatchError as e:
        print(f"error: {e}", file=sys.stderr)
        return 1
    Path(args.output).write_bytes(out)
    for line in report:
        print(line)
    print(f"wrote {args.output} ({len(out)} bytes)")
    print("copy a DBITRNS table to sdmc:/switch/DBI/translation.bin")
    return 0


def _build_table(args) -> int:
    data = build_from_csv(Path(args.csv))
    Path(args.output).write_bytes(data)
    print(f"wrote {args.output} ({len(data)} bytes)")
    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(prog="dbi-translate", description="DBI translation patcher")
    sub = p.add_subparsers(dest="cmd", required=True)

    pp = sub.add_parser("patch", help="inject the translation runtime into a DBI NRO")
    pp.add_argument("--nro", required=True, help="input DBI NRO (bring your own)")
    pp.add_argument("-o", "--output", required=True, help="output patched NRO")
    pp.add_argument("--version", default="905", help="DBI version (default: 905)")
    pp.set_defaults(func=_patch)

    bt = sub.add_parser("build-table", help="build translation.bin from an original,translation CSV")
    bt.add_argument("csv", help="CSV with 'original,translation' columns (UTF-8)")
    bt.add_argument("-o", "--output", default="translation.bin", help="output table (default: translation.bin)")
    bt.set_defaults(func=_build_table)

    args = p.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
