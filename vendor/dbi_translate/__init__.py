"""Self-contained runtime-translation patcher for DBI (Nintendo Switch homebrew).

Injects a boot loader, an exact-match table lookup, and a set of hooks into a DBI
NRO so it loads RU->EN (or any-language) translations from an SD-card table at runtime.
"""

from .patch import PatchError, patch_nro
from .table import build_from_csv, build_table, parse_table
from .versions import VERSIONS, Version

__all__ = ["patch_nro", "PatchError", "build_table", "build_from_csv", "parse_table", "Version", "VERSIONS"]
__version__ = "0.1.0"
