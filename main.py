#!/usr/bin/env python3
"""
ClawBot AI — Entry Point
Run via cron every 5 minutes: */5 * * * * python main.py

Usage:
  python main.py              # Normal mode
  python main.py --dry-run    # Dry run (no real orders)
  python main.py --cycle N    # Override cycle number
"""
import asyncio
import sys
import os
import json
from pathlib import Path

# Ensure project root is in path
sys.path.insert(0, str(Path(__file__).parent))

from src.core.engine import Engine
from src.utils.logger import log


CYCLE_STATE_FILE = "data/cycle_state.json"


def load_cycle_number() -> int:
    """Load last cycle number from state file."""
    try:
        if os.path.exists(CYCLE_STATE_FILE):
            with open(CYCLE_STATE_FILE, "r") as f:
                data = json.load(f)
                return data.get("cycle_number", 0) + 1
    except Exception:
        pass
    return 1


def save_cycle_number(cycle_number: int):
    """Save cycle number to state file."""
    try:
        os.makedirs(os.path.dirname(CYCLE_STATE_FILE), exist_ok=True)
        with open(CYCLE_STATE_FILE, "w") as f:
            json.dump({"cycle_number": cycle_number}, f)
    except Exception as e:
        log.warning(f"Failed to save cycle state: {e}")


async def main():
    """Main entry point."""
    # Parse args
    dry_run = "--dry-run" in sys.argv
    cycle_override = None
    for i, arg in enumerate(sys.argv):
        if arg == "--cycle" and i + 1 < len(sys.argv):
            cycle_override = int(sys.argv[i + 1])

    cycle_number = cycle_override or load_cycle_number()

    if dry_run:
        log.info("🧪 DRY RUN MODE — no real orders will be placed")

    engine = Engine()
    await engine.run_cycle(cycle_number=cycle_number, dry_run=dry_run)

    save_cycle_number(cycle_number)


if __name__ == "__main__":
    asyncio.run(main())
