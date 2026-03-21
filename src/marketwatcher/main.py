from __future__ import annotations

import argparse
import signal
import sys
import time

from .config import load_config
from .logger import setup_logger, get_logger
from .marketplace import MarketplaceBrowser
from .runner import run_scan_cycle
from .state import SeenState


def _build_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="marketwatcher",
        description="Monitor Facebook Marketplace and send Telegram alerts.",
    )
    p.add_argument("--config", default="config.yaml", help="Path to config YAML file.")
    mode = p.add_mutually_exclusive_group(required=True)
    mode.add_argument("--once", action="store_true", help="Run one scan cycle and exit.")
    mode.add_argument("--loop", action="store_true", help="Run continuously.")
    mode.add_argument("--clear-watch", metavar="NAME", help="Clear seen listings for a specific watch name.")
    mode.add_argument("--list-watches", action="store_true", help="List all watches with seen listing counts.")
    p.add_argument("--debug", action="store_true", help="Enable verbose debug logging.")
    return p


def main() -> None:
    args = _build_arg_parser().parse_args()

    config = load_config(args.config)
    log = setup_logger(debug=args.debug)

    state = SeenState(config.state.seen_items_path)
    state.load()

    # ------------------------------------------------------------------
    # State management commands — no browser needed
    # ------------------------------------------------------------------

    if args.list_watches:
        counts = state.list_watches()
        if not counts:
            print("No seen listings recorded yet.")
        else:
            print("Seen listings per watch:")
            for name, count in sorted(counts.items()):
                print(f"  {name}: {count} listing(s)")
        sys.exit(0)

    if args.clear_watch:
        watch_name = args.clear_watch
        removed = state.clear_watch(watch_name)
        if removed == 0:
            print(f"No seen listings found for watch '{watch_name}'.")
            print("Use --list-watches to see available watch names.")
        else:
            state.save()
            print(f"Cleared {removed} seen listing(s) for watch '{watch_name}'.")
        sys.exit(0)

    # ------------------------------------------------------------------
    # Normal scan modes
    # ------------------------------------------------------------------

    log.info("Loaded config from %s", args.config)

    browser = MarketplaceBrowser(config.scanner)

    _stop = False

    def _handle_sigint(*_: object) -> None:
        nonlocal _stop
        log.info("Interrupt received; shutting down after current cycle.")
        _stop = True

    signal.signal(signal.SIGINT, _handle_sigint)
    signal.signal(signal.SIGTERM, _handle_sigint)

    browser.start()
    log.info("Browser started")

    try:
        if args.once:
            run_scan_cycle(config, browser, state)
        else:
            interval = config.scanner.scan_interval_seconds
            log.info("Loop mode — scan interval: %ds", interval)
            while not _stop:
                run_scan_cycle(config, browser, state)
                if _stop:
                    break
                log.info("Sleeping %ds until next cycle…", interval)
                for _ in range(interval):
                    if _stop:
                        break
                    time.sleep(1)
    finally:
        log.info("Flushing state and closing browser.")
        state.save()
        browser.close()

    log.info("MarketWatcher exited cleanly.")


if __name__ == "__main__":
    main()
