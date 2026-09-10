#!/usr/bin/env python3
"""Interactive terminal UI for DBI Translation Pipeline.

Inspired by Kefirosphere build.py interactive selection.
Provides an interactive checkbox selector for pipeline actions
with fixed canonical pipeline execution order.
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass
from pathlib import Path

# Enable VT100 / ANSI escape sequences in Windows console
if sys.platform == "win32":
    os.system("")

if sys.stdout and hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")


# ─────────────────────────────────────────────────────────────────────────────
# Pipeline Definitions
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class MenuItem:
    key: str
    name: str
    description: str
    indent: bool = False


ALL_SUB_ACTIONS = [
    "sync",
    "translate",
    "shadok",
    "align",
    "validate",
    "export",
    "build",
    "dist",
    "check",
    "test",
]

MENU_ITEMS: list[MenuItem] = [
    MenuItem("all", "all", "Complete build pipeline (all steps except deploy & clear)", indent=False),
    MenuItem("sync", "sync", "Synchronize dictionary with source CSV files", indent=True),
    MenuItem("translate", "translate", "Translate missing strings using AI (Web2API / Gemini)", indent=True),
    MenuItem("shadok", "shadok", "Localize Shadok satirical fables via AI (skips complete)", indent=True),
    MenuItem("align", "align", "Align colon positions in structured UI blocks", indent=True),
    MenuItem("validate", "validate", "Validate dictionary structure and translation rules", indent=True),
    MenuItem("export", "export", "Export CSV files and compile translation.bin files", indent=True),
    MenuItem("build", "build", "Compile translation.bin binaries (with size check & auto-regen)", indent=True),
    MenuItem("dist", "dist", "Pack NRO and translation.bin into per-language dist/ folders", indent=True),
    MenuItem("check", "check", "Check source integrity and verify binary file sizes", indent=True),
    MenuItem("test", "test", "Run parallel test suite (pytest -n auto)", indent=True),
    MenuItem("deploy", "deploy", "Deploy release to GitHub (with size verification)", indent=False),
    MenuItem("clear", "clear", "Clear translations for a specific language", indent=False),
]

CANONICAL_PIPELINE_ORDER = [
    "clear",
    "sync",
    "translate",
    "shadok",
    "align",
    "validate",
    "export",
    "build",
    "dist",
    "check",
    "test",
    "deploy",
]


def toggle_item(selected: set[str], key: str) -> None:
    """Update selected actions according to selection rules."""
    if key == "all":
        if "all" in selected:
            selected.remove("all")
            for sub in ALL_SUB_ACTIONS:
                selected.discard(sub)
        else:
            selected.add("all")
            for sub in ALL_SUB_ACTIONS:
                selected.add(sub)
    elif key in ALL_SUB_ACTIONS:
        if key in selected:
            selected.remove(key)
            selected.discard("all")
        else:
            selected.add(key)
            if all(sub in selected for sub in ALL_SUB_ACTIONS):
                selected.add("all")
    else:
        # Independent actions: dist, shadok, check, test, deploy, clear
        if key in selected:
            selected.remove(key)
        else:
            selected.add(key)


def get_execution_plan(selected: set[str]) -> list[str]:
    """Return ordered list of actions to execute in canonical order."""
    return [action for action in CANONICAL_PIPELINE_ORDER if action in selected]


# ─────────────────────────────────────────────────────────────────────────────
# Interactive UI
# ─────────────────────────────────────────────────────────────────────────────

def interactive_menu(initial_selected: set[str] | None = None) -> list[str] | None:
    """Display interactive checkbox menu and return planned actions, or None on exit."""
    try:
        import msvcrt
        has_msvcrt = True
    except ImportError:
        import tty, termios
        has_msvcrt = False

    selected: set[str] = set(initial_selected) if initial_selected is not None else set()
    idx = 0
    lines_written = 0

    def draw() -> None:
        nonlocal lines_written
        if lines_written > 0:
            sys.stdout.write(f"\033[{lines_written}A")

        sys.stdout.write("\033[J")
        print("\033[1;36m===============================================================================\033[0m")
        print("\033[1;36m                     DBI PATCHER - INTERACTIVE PIPELINE                        \033[0m")
        print("\033[1;36m===============================================================================\033[0m")
        print("Use \033[1mUP/DOWN\033[0m to navigate, \033[1mSPACE\033[0m to toggle, \033[1mENTER\033[0m to run, \033[1mQ/ESC\033[0m to exit.")
        print("-" * 79)

        out = []
        for i, item in enumerate(MENU_ITEMS):
            chk = "[x]" if item.key in selected else "[ ]"
            if item.indent:
                pointer = "    >> " if i == idx else "       "
            else:
                pointer = ">> " if i == idx else "   "

            if item.key in selected:
                color = "\033[1;32m"  # Bold green for selected
            elif i == idx:
                color = "\033[1;37m"  # Bold white for cursor
            else:
                color = "\033[2m"     # Dim for unselected
            
            out.append(f"{pointer}{color}{chk} {item.name:<10} - {item.description}\033[0m")

        print("\n".join(out))
        print("-" * 79)

        plan = get_execution_plan(selected)
        if plan:
            plan_str = " -> ".join(plan)
            print(f"\033[1;33mExecution plan:\033[0m \033[1m{plan_str}\033[0m")
        else:
            print("\033[2mNo actions selected. Use SPACE to select.\033[0m")

        # header (3 lines) + prompt (1) + divider (1) + items + divider (1) + plan (1) = len(items) + 7
        lines_written = len(MENU_ITEMS) + 7
        sys.stdout.flush()

    draw()

    while True:
        if has_msvcrt:
            c = msvcrt.getch()
            if c in (b'\x00', b'\xe0'):
                c2 = msvcrt.getch()
                if c2 == b'H':  # UP
                    idx = (idx - 1) % len(MENU_ITEMS)
                elif c2 == b'P':  # DOWN
                    idx = (idx + 1) % len(MENU_ITEMS)
            elif c == b' ':
                toggle_item(selected, MENU_ITEMS[idx].key)
            elif c in (b'\r', b'\n'):
                break
            elif c in (b'q', b'Q', b'\x1b'):
                return None
        else:
            fd = sys.stdin.fileno()
            old = termios.tcgetattr(fd)
            try:
                tty.setraw(fd)
                c = sys.stdin.read(1)
                if c == '\x1b':
                    c2 = sys.stdin.read(2)
                    if c2 == '[A':
                        idx = (idx - 1) % len(MENU_ITEMS)
                    elif c2 == '[B':
                        idx = (idx + 1) % len(MENU_ITEMS)
                    else:
                        return None
                elif c == ' ':
                    toggle_item(selected, MENU_ITEMS[idx].key)
                elif c in ('\r', '\n'):
                    break
                elif c in ('q', 'Q'):
                    return None
            finally:
                termios.tcsetattr(fd, termios.TCSADRAIN, old)

        draw()

    if lines_written > 0:
        sys.stdout.write(f"\033[{lines_written}A\033[J")
        sys.stdout.flush()

    return get_execution_plan(selected)


# ─────────────────────────────────────────────────────────────────────────────
# Execution Engine
# ─────────────────────────────────────────────────────────────────────────────

def run_pipeline() -> None:
    """Main loop for running the interactive menu and pipeline."""
    # Ensure current working directory is project root
    root = Path(__file__).resolve().parent
    os.chdir(root)

    # Import main pipeline commands
    from src.main import COMMANDS, cmd_clear, cmd_test

    selected_state: set[str] = set()

    while True:
        plan = interactive_menu(selected_state)
        if plan is None:
            print("\nExiting DBI Patcher. Goodbye!\n")
            break

        if not plan:
            print("\n\033[33m[!] No actions were selected. Press ENTER to select actions or Q to quit.\033[0m")
            input()
            continue

        print("\n\033[1;36m===============================================================================\033[0m")
        print(f"\033[1;36m  Starting Execution: {' -> '.join(plan)}\033[0m")
        print("\033[1;36m===============================================================================\033[0m\n")

        for action in plan:
            print(f"\n\033[1;32m>>> STEP: {action}\033[0m")

            if action == "clear":
                lang_code = input("  Enter language code to clear (e.g. en, fr, de, id) or press ENTER to skip: ").strip()
                if not lang_code:
                    print("  [SKIP] Clear cancelled.")
                    continue
                cmd_clear(lang_code)

            elif action == "deploy":
                confirm = input("  Are you sure you want to commit, push and deploy to GitHub? (y/N): ").strip().lower()
                if confirm != "y":
                    print("  [SKIP] Deployment cancelled.")
                    continue
                COMMANDS["deploy"]()

            elif action == "test":
                import subprocess
                print("  [TEST] Running test suite: pytest tests -n auto ...")
                res = subprocess.run([sys.executable, "-m", "pytest", "tests", "-n", "auto"])
                if res.returncode != 0:
                    print(f"  [WARN] Test suite exited with code {res.returncode}")

            elif action in COMMANDS:
                COMMANDS[action]()

            else:
                print(f"  [ERROR] Unknown command: {action}")

        print("\n\033[1;32m===============================================================================\033[0m")
        print("\033[1;32m  All selected pipeline actions completed!\033[0m")
        print("\033[1;32m===============================================================================\033[0m")

        input("\nPress ENTER to return to menu...")


if __name__ == "__main__":
    try:
        run_pipeline()
    except KeyboardInterrupt:
        print("\n\nOperation aborted by user.")
        sys.exit(0)
