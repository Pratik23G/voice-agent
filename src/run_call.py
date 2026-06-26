"""
Entrypoint for placing outbound test calls via Vapi.

Usage:
    python -m src.run_call --scenario schedule_new
    python -m src.run_call --all
    python -m src.run_call --list
    python -m src.run_call --scenario schedule_new --dry-run
    python -m src.run_call --dry-run   (uses first scenario)
"""

import argparse
import json
import sys
import time
from datetime import datetime, timezone

from src import config, vapi_client
from src.personas import SCENARIOS, get_scenario, list_scenarios


def _timestamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")


def run_scenario(scenario_key: str, dry_run: bool = False) -> None:
    scenario = get_scenario(scenario_key)
    payload = vapi_client.build_call_payload(scenario)

    print(f"\n{'='*60}")
    print(f"Scenario : {scenario_key}")
    print(f"Goal     : {scenario['test_goal']}")
    if scenario.get("trap"):
        print(f"Trap     : {scenario['trap']}")
    print(f"{'='*60}")

    if dry_run:
        print("\n[DRY RUN] Payload that WOULD be sent to POST https://api.vapi.ai/call:\n")
        safe_payload = json.loads(json.dumps(payload))
        safe_payload["assistant"]["model"]["systemPrompt"] = (
            safe_payload["assistant"]["model"]["systemPrompt"][:120] + "..."
        )
        print(json.dumps(safe_payload, indent=2))
        print("\n[DRY RUN] No call placed.")
        return

    print(f"\nPlacing call to {config.TARGET_PHONE_NUMBER}...")
    call_id = vapi_client.create_call(scenario)
    print(f"Call ID  : {call_id}")
    print("Polling for completion...")

    try:
        call = vapi_client.poll_until_complete(call_id)
    except TimeoutError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    ts = _timestamp()
    print(f"\nCall ended. Saving artifacts...")
    paths = vapi_client.save_artifacts(call_id, scenario_key, call, ts)

    print(f"\nResults:")
    if paths["recording"]:
        print(f"  Recording  : {paths['recording']}")
    else:
        print(f"  Recording  : not available")
    print(f"  Transcript : {paths['txt']}")
    print(f"  JSON       : {paths['json']}")
    print(f"  Ended reason: {call.get('endedReason', 'unknown')}")


def run_all(dry_run: bool = False) -> None:
    keys = list(SCENARIOS.keys())
    print(f"Running {len(keys)} scenarios{'  [DRY RUN]' if dry_run else ''}...")
    for i, key in enumerate(keys, 1):
        print(f"\n[{i}/{len(keys)}] {key}")
        run_scenario(key, dry_run=dry_run)
        if not dry_run and i < len(keys):
            print("Waiting 10s before next call...")
            time.sleep(10)


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Place outbound AI patient calls via Vapi for QA testing."
    )
    group = parser.add_mutually_exclusive_group()
    group.add_argument(
        "--scenario",
        metavar="KEY",
        help="Run a single scenario by key (see --list for keys)",
    )
    group.add_argument(
        "--all",
        action="store_true",
        help="Run all scenarios sequentially",
    )
    group.add_argument(
        "--list",
        action="store_true",
        help="Print all available scenario keys and exit",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Build and print the call payload without placing any call",
    )

    args = parser.parse_args()

    if args.list:
        print("\nAvailable scenarios:\n")
        for key, desc in list_scenarios():
            print(f"  {key:<25}  {desc}")
        print()
        return

    if not args.dry_run:
        config.require_env()

    if args.all:
        run_all(dry_run=args.dry_run)
    elif args.scenario:
        run_scenario(args.scenario, dry_run=args.dry_run)
    else:
        if args.dry_run:
            first_key = next(iter(SCENARIOS))
            print(f"No scenario specified; showing dry run for '{first_key}'.")
            run_scenario(first_key, dry_run=True)
        else:
            parser.print_help()
            sys.exit(1)


if __name__ == "__main__":
    main()
